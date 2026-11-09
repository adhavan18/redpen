"""builds the read-only github pages demo in docs/.

the page is the real ui (static/) with window.REDPEN_DEMO set. every api response is a
snapshot taken through the real fastapi routes, so the demo shows exactly what the tool
produced; the export button serves the committed sample package for that lesson.

usage: python scripts/build_demo.py   (needs the lessons in data/lessons)
"""
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from redpen.main import app  # noqa: E402

DOCS = ROOT / "docs"
DEMO = DOCS / "demo"
# lesson id -> committed sample export folder
LESSONS = {
    "http-requests-and-responses-4b5ba5": "http-requests-and-responses",
    "sql-joins-3db3c1": "sql-joins",
}


def main():
    api = TestClient(app)
    if DEMO.exists():
        shutil.rmtree(DEMO)
    DEMO.mkdir(parents=True)

    def save(name, data):
        (DEMO / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    save("health", {"demo": True})
    save("lessons", [l for l in api.get("/api/lessons").json() if l["id"] in LESSONS])
    for lesson_id, sample in LESSONS.items():
        d = api.get(f"/api/lessons/{lesson_id}").raise_for_status().json()
        d["state"]["running"] = False
        save(lesson_id, d)
        with zipfile.ZipFile(DEMO / f"{lesson_id}.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted((ROOT / "samples" / sample).iterdir()):
                z.write(f, f.name)

    shutil.copy(ROOT / "static" / "style.css", DOCS / "style.css")
    shutil.copy(ROOT / "static" / "app.js", DOCS / "app.js")
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    # content hashes in the urls so the 10-minute pages cache never serves a stale ui
    v = {f: hashlib.sha1((DOCS / f).read_bytes()).hexdigest()[:8] for f in ("style.css", "app.js")}
    html = html.replace('href="/static/style.css"', f'href="style.css?v={v["style.css"]}"')
    html = html.replace('<script src="/static/app.js"></script>',
                        f'<script>window.REDPEN_DEMO = true;</script>\n<script src="app.js?v={v["app.js"]}"></script>')
    html = re.sub(r"<title>.*?</title>", "<title>redpen · demo</title>", html)
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    print("built", DOCS, sorted(p.name for p in DEMO.iterdir()))


if __name__ == "__main__":
    main()
