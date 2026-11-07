"""file-based lesson store.

data/lessons/<id>/
  state.json          inputs, step statuses, live log, current version number
  research.json       sources, chunks, video candidates, misconceptions
  embeddings.npy      chunk vectors (row i = research.chunks[i])
  versions/v<n>.json  every saved lesson, never overwritten
  qc_factual.json / qc_instructional.json

all writes go through a temp file + os.replace so a crash never leaves half a json file.
"""

import json
import os
import re
import threading
import time
import uuid
from pathlib import Path

import numpy as np

from . import config

STEPS = ["research", "draft", "qc_factual", "qc_instructional"]

_locks: dict[str, threading.RLock] = {}
_locks_guard = threading.Lock()


def lock(lesson_id: str) -> threading.RLock:
    with _locks_guard:
        return _locks.setdefault(lesson_id, threading.RLock())


def now() -> float:
    return round(time.time(), 3)


def lessons_dir() -> Path:
    d = config.DATA_DIR / "lessons"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ldir(lesson_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]{4,64}", lesson_id):
        raise KeyError(lesson_id)
    return lessons_dir() / lesson_id


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{uuid.uuid4().hex[:6]}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40].strip("-")
    return f"{s or 'lesson'}-{uuid.uuid4().hex[:6]}"


def create(title: str, objective: str, audience: str) -> dict:
    lesson_id = slugify(title)
    state = {
        "id": lesson_id,
        "title": title,
        "objective": objective,
        "audience": audience,
        "created_at": now(),
        "updated_at": now(),
        "current_version": 0,
        "steps": {s: {"status": "idle", "error": None, "attempts": 0, "started_at": None,
                      "finished_at": None, "version": None} for s in STEPS},
        "log": [],
        "exports": [],
    }
    write_json(ldir(lesson_id) / "state.json", state)
    return state


def load_state(lesson_id: str) -> dict:
    st = read_json(ldir(lesson_id) / "state.json")
    if st is None:
        raise KeyError(lesson_id)
    return st


def save_state(state: dict) -> None:
    state["updated_at"] = now()
    write_json(ldir(state["id"]) / "state.json", state)


def update_state(lesson_id: str, fn) -> dict:
    with lock(lesson_id):
        st = load_state(lesson_id)
        fn(st)
        save_state(st)
        return st


def log(lesson_id: str, step: str, msg: str, kind: str = "info") -> None:
    def add(st):
        st["log"].append({"t": now(), "step": step, "msg": msg, "kind": kind})
        st["log"] = st["log"][-400:]

    update_state(lesson_id, add)


def list_lessons() -> list[dict]:
    out = []
    for p in lessons_dir().iterdir():
        st = read_json(p / "state.json")
        if st:
            out.append({k: st[k] for k in ("id", "title", "objective", "updated_at", "current_version")}
                       | {"steps": {k: v["status"] for k, v in st["steps"].items()}})
    return sorted(out, key=lambda x: -x["updated_at"])


def recover_interrupted() -> None:
    """a server restart kills background threads; mark their steps failed so they can be retried."""
    for p in lessons_dir().iterdir():
        st = read_json(p / "state.json")
        if not st:
            continue
        changed = False
        for s in st["steps"].values():
            if s["status"] == "running":
                s["status"], s["error"], changed = "failed", "interrupted by a server restart", True
        if changed:
            save_state(st)


# ---------- research ----------

def save_research(lesson_id: str, research: dict, vectors: np.ndarray | None) -> None:
    d = ldir(lesson_id)
    write_json(d / "research.json", research)
    if vectors is not None:
        tmp = d / "embeddings.tmp.npy"
        np.save(tmp, vectors)
        os.replace(tmp, d / "embeddings.npy")
    elif (d / "embeddings.npy").exists():
        (d / "embeddings.npy").unlink()


def load_research(lesson_id: str) -> dict | None:
    return read_json(ldir(lesson_id) / "research.json")


def load_vectors(lesson_id: str) -> np.ndarray | None:
    p = ldir(lesson_id) / "embeddings.npy"
    return np.load(p) if p.exists() else None


# ---------- versions ----------

def save_version(lesson_id: str, doc: dict, author: str, note: str, base_version: int | None = None) -> int:
    """append a new version. base_version guards against two tabs overwriting each other."""
    with lock(lesson_id):
        st = load_state(lesson_id)
        if base_version is not None and base_version != st["current_version"]:
            raise ConflictError(st["current_version"])
        n = st["current_version"] + 1
        write_json(ldir(lesson_id) / "versions" / f"v{n}.json",
                   {"version": n, "author": author, "note": note, "created_at": now(), "doc": doc})
        st["current_version"] = n
        for step in ("qc_factual", "qc_instructional"):
            if st["steps"][step]["status"] == "done":
                st["steps"][step]["status"] = "stale"
        save_state(st)
        return n


class ConflictError(Exception):
    def __init__(self, current: int):
        super().__init__(f"lesson changed elsewhere; current version is v{current}")
        self.current = current


def load_version(lesson_id: str, n: int | None = None) -> dict | None:
    if n is None:
        n = load_state(lesson_id)["current_version"]
    if not n:
        return None
    return read_json(ldir(lesson_id) / "versions" / f"v{n}.json")


def list_versions(lesson_id: str) -> list[dict]:
    out = []
    for p in sorted((ldir(lesson_id) / "versions").glob("v*.json"), key=lambda p: int(p.stem[1:])):
        v = read_json(p)
        out.append({k: v[k] for k in ("version", "author", "note", "created_at")})
    return out


# ---------- qc ----------

def save_qc(lesson_id: str, layer: str, report: dict) -> None:
    write_json(ldir(lesson_id) / f"{layer}.json", report)


def load_qc(lesson_id: str, layer: str) -> dict | None:
    return read_json(ldir(lesson_id) / f"{layer}.json")
