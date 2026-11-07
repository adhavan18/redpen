from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import config, export, fixes, generate, pipeline, storage


@asynccontextmanager
async def lifespan(_app):
    storage.recover_interrupted()
    yield


app = FastAPI(title="redpen", lifespan=lifespan)


def _404(fn):
    try:
        return fn()
    except KeyError:
        raise HTTPException(404, "lesson not found")


class NewLesson(BaseModel):
    title: str = Field(max_length=160)
    objective: str = Field(max_length=600)
    audience: str = Field("first-year computer science undergraduates", max_length=200)
    run: bool = True

    @field_validator("title", "objective")
    @classmethod
    def not_blank(cls, v: str, info):
        v = " ".join(v.split())
        if not v:
            raise ValueError(f"{info.field_name} cannot be empty")
        if info.field_name == "objective" and len(v.split()) < 4:
            raise ValueError("write the objective as a full sentence: what should the learner be able to do?")
        return v

    @field_validator("audience")
    @classmethod
    def audience_default(cls, v: str):
        return " ".join(v.split()) or "first-year computer science undergraduates"


class RunSteps(BaseModel):
    steps: list[str]


class SaveLesson(BaseModel):
    doc: dict
    base_version: int
    note: str = "instructor edit"


class FixRequest(BaseModel):
    issue_ids: list[str]


class AcceptFixes(BaseModel):
    base_version: int
    proposals: list[dict]


class IssueStatus(BaseModel):
    ids: list[str]
    status: str
    note: str | None = None


@app.get("/api/health")
def health():
    return {"llm_key": bool(config.GEMINI_API_KEY), "model": config.MODEL, "fallbacks": config.FALLBACK_MODELS,
            "search": "tavily" if config.TAVILY_API_KEY else "duckduckgo"}


@app.get("/api/lessons")
def lessons():
    return storage.list_lessons()


@app.post("/api/lessons")
def create(body: NewLesson):
    st = storage.create(body.title, body.objective, body.audience)
    if body.run:
        if not config.GEMINI_API_KEY:
            storage.log(st["id"], "research", "GEMINI_API_KEY is missing: add it to .env, restart, then press run",
                        "error")
        else:
            pipeline.start(st["id"], pipeline.ORDER)
    return storage.load_state(st["id"])


@app.get("/api/lessons/{lesson_id}")
def get(lesson_id: str, since: float = 0):
    def f():
        st = storage.load_state(lesson_id)
        ver = storage.load_version(lesson_id)
        res = storage.load_research(lesson_id)
        return {
            "state": st | {"log": [x for x in st["log"] if x["t"] > since], "running": pipeline.is_running(lesson_id)},
            "version": ver,
            "minutes": generate.lesson_minutes(ver["doc"]) if ver else None,
            "research": None if not res else {k: v for k, v in res.items() if k != "chunks"}
            | {"chunk_count": len(res["chunks"])},
            "qc_factual": storage.load_qc(lesson_id, "qc_factual"),
            "qc_instructional": storage.load_qc(lesson_id, "qc_instructional"),
            "gate": export.gate(lesson_id),
            "versions": storage.list_versions(lesson_id),
        }

    return _404(f)


@app.get("/api/lessons/{lesson_id}/chunks/{chunk_id}")
def chunk(lesson_id: str, chunk_id: str):
    res = _404(lambda: storage.load_research(lesson_id)) or {"chunks": []}
    for c in res["chunks"]:
        if c["id"] == chunk_id:
            return c
    raise HTTPException(404, "chunk not found")


@app.post("/api/lessons/{lesson_id}/run")
def run(lesson_id: str, body: RunSteps):
    _404(lambda: storage.load_state(lesson_id))
    if not config.GEMINI_API_KEY:
        raise HTTPException(400, "GEMINI_API_KEY is missing: add it to .env and restart the server")
    try:
        return {"started": pipeline.start(lesson_id, body.steps)}
    except pipeline.StepError as e:
        raise HTTPException(409, str(e))


@app.put("/api/lessons/{lesson_id}/lesson")
def save(lesson_id: str, body: SaveLesson):
    _404(lambda: storage.load_state(lesson_id))
    doc = body.doc
    if not doc.get("sections") or any(not s.get("body_md", "").strip() for s in doc["sections"]):
        raise HTTPException(400, "every section needs some text; delete a section instead of emptying it")
    for s in doc["sections"]:
        try:
            s["minutes"] = max(1, int(s["minutes"]))
        except (TypeError, ValueError):
            raise HTTPException(400, f"minutes for \"{s.get('title')}\" must be a number")
    for q in doc.get("quiz", []):
        if not (0 <= int(q.get("answer_index", -1)) < len(q.get("options", []))):
            raise HTTPException(400, f"question \"{q.get('question', '')[:50]}\" has no valid answer selected")
    try:
        n = storage.save_version(lesson_id, doc, author="instructor", note=body.note[:200],
                                 base_version=body.base_version)
    except storage.ConflictError as e:
        raise HTTPException(409, str(e))
    return {"version": n}


@app.post("/api/lessons/{lesson_id}/versions/{n}/restore")
def restore(lesson_id: str, n: int):
    ver = _404(lambda: storage.load_version(lesson_id, n))
    if not ver:
        raise HTTPException(404, "version not found")
    return {"version": storage.save_version(lesson_id, ver["doc"], author="instructor", note=f"restored v{n}")}


@app.post("/api/lessons/{lesson_id}/fixes/preview")
def fix_preview(lesson_id: str, body: FixRequest):
    _404(lambda: storage.load_state(lesson_id))
    try:
        return fixes.preview(lesson_id, body.issue_ids)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/lessons/{lesson_id}/fixes/accept")
def fix_accept(lesson_id: str, body: AcceptFixes):
    _404(lambda: storage.load_state(lesson_id))
    try:
        return {"version": fixes.accept(lesson_id, body.base_version, body.proposals)}
    except storage.ConflictError as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/lessons/{lesson_id}/issues")
def issue_status(lesson_id: str, body: IssueStatus):
    if body.status not in ("open", "dismissed"):
        raise HTTPException(400, "status must be open or dismissed")
    _404(lambda: storage.load_state(lesson_id))
    fixes.set_status(lesson_id, body.ids, body.status, body.note)
    return {"ok": True}


@app.get("/api/lessons/{lesson_id}/export")
def do_export(lesson_id: str, override: str | None = None):
    _404(lambda: storage.load_state(lesson_id))
    try:
        data, name = export.build(lesson_id, override)
    except PermissionError as e:
        raise HTTPException(409, f"export blocked: {e}")
    return Response(data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(config.STATIC_DIR / "index.html")
