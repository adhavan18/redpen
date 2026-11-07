"""turn qc findings into proposed edits. nothing is written until the instructor accepts a proposal."""

import copy
from concurrent.futures import ThreadPoolExecutor

from . import llm, prompts, storage
from .research import retrieval
from .schemas import QuizRewrite, SectionRewrite

LAYERS = ("qc_factual", "qc_instructional")


def find_issues(lesson_id: str, ids: list[str]) -> list[dict]:
    out = []
    for layer in LAYERS:
        rep = storage.load_qc(lesson_id, layer) or {}
        out += [i for i in rep.get("issues", []) if i["id"] in ids]
    return out


def issue_text(issues: list[dict]) -> str:
    rows = []
    for i in issues:
        rows.append(f"- [{i['id']}, {i['severity']}, {i['category']}] {i['description']}"
                    + (f"\n  sentence: {i['sentence']}" if i.get("sentence") else "")
                    + (f"\n  evidence: {i['evidence'][:600]}" if i.get("evidence") else "")
                    + (f"\n  suggested: {i['suggestion']}" if i.get("suggestion") else ""))
    return "\n".join(rows)


def _quiz_text(quiz: list[dict]) -> str:
    out = []
    for qi, q in enumerate(quiz):
        out.append(f"Q{qi} ({q['id']}, part: {q.get('objective_part', '')}). {q['question']}")
        out += [f"   {oi}) {o}{' (correct)' if oi == q['answer_index'] else ''}" for oi, o in enumerate(q["options"])]
    return "\n".join(out)


def preview(lesson_id: str, ids: list[str]) -> dict:
    ver = storage.load_version(lesson_id)
    if not ver:
        raise ValueError("there is no lesson to fix yet")
    doc = ver["doc"]
    issues = find_issues(lesson_id, ids)
    if not issues:
        raise ValueError("none of those findings exist in the current reports")
    research = storage.load_research(lesson_id) or {"chunks": [], "sources": []}
    index = retrieval.Index(research["chunks"], storage.load_vectors(lesson_id))
    groups: dict[str, list] = {}
    manual = []
    for i in issues:
        if i["section_id"] is None:
            manual.append(i["id"])
        else:
            groups.setdefault(i["section_id"], []).append(i)

    def one(item):
        target, its = item
        try:
            if target == "quiz":
                from .qc.common import lesson_text

                r = llm.generate(prompts.render("apply_fix_quiz", title=doc["title"],
                                                parts="\n".join(f"- {p}" for p in doc["objective_parts"]),
                                                lesson=lesson_text(doc, with_quiz=False), quiz=_quiz_text(doc["quiz"]),
                                                issues=issue_text(its)),
                                 QuizRewrite, temperature=0.3, what="quiz fix")
                after = []
                for n, q in enumerate(r.quiz):
                    if len(q.options) >= 3 and 0 <= q.answer_index < len(q.options):
                        after.append(q.model_dump() | {"id": f"q{n + 1}"})
                return {"target": "quiz", "title": "knowledge check", "before": doc["quiz"], "after": after,
                        "change_summary": r.change_summary, "issue_ids": [i["id"] for i in its]}
            sec = next(s for s in doc["sections"] if s["id"] == target)
            query = " ".join(i["description"] + " " + i.get("suggestion", "") for i in its)
            ev = index.search(query, k=5, per_source=2) if research["chunks"] else []
            evidence = "\n".join(f"[{c['source_id']}] {c['text'][:900]}" for c, _ in ev) or "(no research available)"
            r = llm.generate(prompts.render("apply_fix", title=doc["title"], objective=doc["objective"],
                                            section_title=sec["title"], section_kind=sec["kind"], minutes=sec["minutes"],
                                            body=sec["body_md"], issues=issue_text(its), evidence=evidence),
                             SectionRewrite, temperature=0.3, what="section fix")
            return {"target": target, "title": sec["title"], "before": sec["body_md"], "after": r.body_md.strip(),
                    "change_summary": r.change_summary, "issue_ids": [i["id"] for i in its]}
        except Exception as e:  # noqa: BLE001 - one failed proposal must not sink the others
            return {"target": target, "error": str(e)[:300], "issue_ids": [i["id"] for i in its]}

    with ThreadPoolExecutor(3) as ex:
        proposals = list(ex.map(one, groups.items()))
    return {"base_version": ver["version"], "proposals": proposals, "manual": manual}


def accept(lesson_id: str, base_version: int, proposals: list[dict]) -> int:
    ver = storage.load_version(lesson_id, base_version)
    if not ver:
        raise ValueError("base version not found")
    doc = copy.deepcopy(ver["doc"])
    applied = []
    for p in proposals:
        if p.get("error"):
            continue
        if p["target"] == "quiz":
            doc["quiz"] = p["after"]
        else:
            for s in doc["sections"]:
                if s["id"] == p["target"]:
                    s["body_md"] = p["after"]
        applied += p["issue_ids"]
    if not applied:
        raise ValueError("nothing to apply")
    n = storage.save_version(lesson_id, doc, author="instructor", note="applied qc fixes " + ", ".join(applied),
                             base_version=base_version)
    set_status(lesson_id, applied, "applied", f"applied in v{n}")
    return n


def set_status(lesson_id: str, ids: list[str], status: str, note: str | None) -> None:
    with storage.lock(lesson_id):
        for layer in LAYERS:
            rep = storage.load_qc(lesson_id, layer)
            if not rep:
                continue
            changed = False
            for i in rep["issues"]:
                if i["id"] in ids:
                    i["status"], i["note"], changed = status, note, True
            if changed:
                storage.save_qc(lesson_id, layer, rep)
