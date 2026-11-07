"""governed workflow: steps run in a fixed order, each step's output is persisted before the next
starts, and any failed step can be retried without redoing (or losing) the steps before it."""

import threading
import traceback

from . import generate, research, storage
from .qc import factual, instructional

ORDER = ["research", "draft", "qc_factual", "qc_instructional"]
REQUIRES = {"research": [], "draft": ["research"], "qc_factual": ["draft"], "qc_instructional": ["draft"]}
LABEL = {"research": "research", "draft": "draft", "qc_factual": "qc 1 - facts", "qc_instructional": "qc 2 - teaching"}


class StepError(Exception):
    pass


def _check_ready(st: dict, step: str, pending: list[str]) -> None:
    for dep in REQUIRES[step]:
        if st["steps"][dep]["status"] not in ("done", "stale") and dep not in pending:
            raise StepError(f"{LABEL[step]} needs {LABEL[dep]} to finish first")
    if step.startswith("qc") and not st["current_version"] and "draft" not in pending:
        raise StepError("there is no lesson draft to check yet")


def _mark(lesson_id: str, step: str, **fields) -> None:
    def f(st):
        st["steps"][step].update(fields)

    storage.update_state(lesson_id, f)


def _run_step(lesson_id: str, step: str) -> bool:
    def log(msg, kind="info"):
        storage.log(lesson_id, step, msg, kind)

    st = storage.load_state(lesson_id)
    _mark(lesson_id, step, status="running", error=None, started_at=storage.now(), finished_at=None,
          attempts=st["steps"][step]["attempts"] + 1)
    try:
        if step == "research":
            res, vecs = research.run(st["title"], st["objective"], st["audience"], log)
            storage.save_research(lesson_id, res, vecs)
            _mark(lesson_id, step, status="done", finished_at=storage.now())
            return True

        res = storage.load_research(lesson_id)
        vecs = storage.load_vectors(lesson_id)
        if res is None:
            raise StepError("research results are missing; run research again")

        if step == "draft":
            doc = generate.run(st, res, vecs, log)
            n = storage.save_version(lesson_id, doc, author="ai", note="generated draft")
            log(f"saved as v{n}; earlier versions are kept in history", "ok")
            _mark(lesson_id, step, status="done", finished_at=storage.now(), version=n)
            return True

        version = storage.load_state(lesson_id)["current_version"]
        doc = storage.load_version(lesson_id, version)["doc"]
        if step == "qc_factual":
            report = factual.run(st, doc, res, vecs, log)
        else:
            report = instructional.run(st, doc, log, res["plan"].get("key_terms", []))
        report |= {"version": version, "created_at": storage.now()}
        storage.save_qc(lesson_id, step, report)
        storage.write_json(storage.ldir(lesson_id) / "history" / f"{step}.v{version}.json", report)
        _mark(lesson_id, step, status="done", finished_at=storage.now(), version=version)
        return True
    except Exception as e:  # noqa: BLE001 - every failure is shown to the instructor with a retry button
        msg = str(e) or type(e).__name__
        log(f"failed: {msg}", "error")
        storage.write_json(storage.ldir(lesson_id) / "history" / f"{step}.error.json",
                           {"error": msg, "trace": traceback.format_exc()[-4000:], "at": storage.now()})
        _mark(lesson_id, step, status="failed", error=msg, finished_at=storage.now())
        return False


_running: dict[str, threading.Thread] = {}


def is_running(lesson_id: str) -> bool:
    t = _running.get(lesson_id)
    return bool(t and t.is_alive())


def start(lesson_id: str, steps: list[str]) -> list[str]:
    steps = [s for s in ORDER if s in steps]
    if not steps:
        raise StepError("no steps to run")
    if is_running(lesson_id):
        raise StepError("this lesson is already running a step")
    st = storage.load_state(lesson_id)
    for i, s in enumerate(steps):
        _check_ready(st, s, steps[:i])
    for s in steps:
        _mark(lesson_id, s, status="queued", error=None)

    def work():
        seq = [s for s in steps if not s.startswith("qc")]
        qcs = [s for s in steps if s.startswith("qc")]
        for s in seq:
            if not _run_step(lesson_id, s):
                for rest in steps[steps.index(s) + 1:]:
                    _mark(lesson_id, rest, status="blocked", error=f"{LABEL[s]} failed")
                return
        # the two qc layers are independent: run them side by side
        threads = [threading.Thread(target=_run_step, args=(lesson_id, s), daemon=True) for s in qcs]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    t = threading.Thread(target=work, daemon=True)
    _running[lesson_id] = t
    t.start()
    return steps
