"""export: lesson (md + standalone html + json), references, both qc reports, run sheet, manifest."""

import io
import json
import re
import zipfile
from datetime import datetime

import markdown as md_lib

from . import generate, storage
from .research.youtube import fmt_ts

CSS = """body{font:17px/1.6 Georgia,serif;max-width:760px;margin:40px auto;padding:0 20px;color:#1d1b16;background:#fbfaf6}
h1{font:700 2rem/1.2 system-ui,sans-serif}h2{font:700 1.35rem system-ui,sans-serif;margin-top:2.2em;border-top:1px solid #ddd8cc;padding-top:1em}
h3{font:600 1.05rem system-ui,sans-serif}code,pre{font:14px ui-monospace,Consolas,monospace;background:#f0ede4}pre{padding:12px;overflow:auto;border-radius:6px}
table{border-collapse:collapse}td,th{border:1px solid #ddd8cc;padding:6px 10px}.meta{color:#6b665a;font:14px system-ui,sans-serif}
sup a{text-decoration:none;font:600 11px system-ui,sans-serif}"""


def gate(lesson_id: str) -> dict:
    st = storage.load_state(lesson_id)
    v = st["current_version"]
    reasons = []
    if not v:
        reasons.append("there is no lesson yet")
    open_high = 0
    for layer, label in (("qc_factual", "qc 1 (facts)"), ("qc_instructional", "qc 2 (teaching)")):
        rep = storage.load_qc(lesson_id, layer)
        if not rep:
            reasons.append(f"{label} has not been run")
        elif rep["version"] != v:
            reasons.append(f"{label} checked v{rep['version']} but the lesson is now v{v}; re-run it")
        else:
            open_high += sum(1 for i in rep["issues"] if i["severity"] == "high" and i["status"] == "open")
    if open_high:
        reasons.append(f"{open_high} high-severity finding(s) are still open (apply or dismiss them)")
    return {"ok": not reasons, "reasons": reasons, "version": v}


def references(doc: dict, research: dict) -> tuple[list[dict], list[dict], list[dict]]:
    cited = generate.cited_ids(doc)
    srcs = [s for s in research["sources"] if s["id"] in cited]
    srcs.sort(key=lambda s: int(s["id"][1:]))
    books = [s for s in research["sources"] if s["kind"] == "book" and s["id"] not in cited]
    m_ids = set(re.findall(r"\[(M\d+)\]", " ".join(s["body_md"] for s in doc["sections"])))
    threads = [m for m in research.get("misconceptions", []) if m["id"] in m_ids]
    return srcs, books, threads


def lesson_markdown(doc: dict, research: dict) -> str:
    out = [f"# {doc['title']}", "", f"**Learning objective:** {doc['objective']}", "",
           f"*Time: {generate.lesson_minutes(doc)} minutes. Audience: {doc.get('audience', '')}*", ""]
    vids_after: dict[str, list] = {}
    for v in doc.get("videos", []):
        vids_after.setdefault(v["after_section"], []).append(v)
    for s in doc["sections"]:
        out += [f"## {s['title']}", f"*{s['minutes']} min*", "", s["body_md"], ""]
        for v in vids_after.get(s["id"], []):
            tag = "Watch now" if v["in_lesson"] else "Optional video"
            out += [f"> **{tag}:** [{v['title']}]({v['url']}) by {v['channel']}, "
                    f"{fmt_ts(v['start'])}-{fmt_ts(v['end'])} ({v['watch_minutes']} min). {v['why']}", ""]
    if doc.get("quiz"):
        out += [f"## Knowledge check", f"*{doc['quiz_minutes']} min*", ""]
        for i, q in enumerate(doc["quiz"]):
            out.append(f"**{i + 1}. {q['question']}**\n")
            out += [f"- {chr(65 + oi)}) {o}" for oi, o in enumerate(q["options"])]
            out.append("")
        out += ["### Answers", ""]
        for i, q in enumerate(doc["quiz"]):
            out.append(f"{i + 1}. **{chr(65 + q['answer_index'])}**: {q['explanation']}")
        out.append("")
    srcs, books, threads = references(doc, research)
    out += ["## References", ""]
    out += [f"- **[{s['id']}]** {s['title']}{', ' + s['authors'] if s.get('authors') else ''}. <{s['url']}> "
            f"(tier {s['tier']}: {s['tier_reason']})" for s in srcs]
    if threads:
        out += ["", "**Learner questions referenced**", ""]
        out += [f"- **[{m['id']}]** {m['title']} <{m['url']}>" for m in threads]
    if doc.get("videos"):
        out += ["", "**Videos**", ""]
        out += [f"- {v['title']} by {v['channel']} <{v['url']}> ({fmt_ts(v['start'])}-{fmt_ts(v['end'])})"
                for v in doc["videos"]]
    if books:
        out += ["", "**Further reading**", ""]
        out += [f"- {b['title']}, {b.get('authors') or 'unknown author'} ({b.get('published') or 'n.d.'}) <{b['url']}>"
                for b in books]
    return "\n".join(out) + "\n"


def to_html(markdown_text: str, title: str) -> str:
    body = md_lib.markdown(markdown_text, extensions=["fenced_code", "tables"])
    body = re.sub(r"\[(S\d+)\]", r'<sup><a href="#ref-\1">\1</a></sup>', body)
    return (f"<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width'>"
            f"<title>{title}</title><style>{CSS}</style><body>{body}</body></html>")


def qc_markdown(report: dict, title: str) -> str:
    s = report["summary"]
    layer = report["layer"]
    out = [f"# {'QC 1: research and factual accuracy' if layer == 'qc_factual' else 'QC 2: instructional quality'}",
           f"Lesson: {title} (v{report['version']}), generated {datetime.fromtimestamp(report['created_at']):%Y-%m-%d %H:%M}", ""]
    if layer == "qc_factual":
        out += [f"- claims checked: {s['claims']} (supported {s['supported']}, partial {s['partial']}, unsupported "
                f"{s['unsupported']}, contradicted {s['contradicted']}); accuracy {s['accuracy']}%",
                f"- verifier quotes found verbatim in sources: {s['quotes_verified']}/{s['claims']}",
                f"- code examples run: {s['code_pass']}/{s['code_total']} print what the lesson claims",
                f"- live http probes: {s['probes_pass']}/{s['probes_total']} confirmed",
                f"- copied passages (12+ words): {s['copied_spans']}",
                f"- sources cited: {s['cited_sources']} ({s['tier_a_cited']} tier A)", "", "## Claims", "",
                "| verdict | claim | evidence |", "|---|---|---|"]
        for c in report["claims"]:
            ev = f"{c.get('source_id') or ''}: \"{(c.get('quote') or '')[:140]}\"" + ("" if c.get("quote_verified") else " (quote not verified)")
            out.append(f"| {c['verdict']} | {c['claim'].replace('|', '/')} | {ev.replace('|', '/')} |")
        if report["code"]:
            out += ["", "## Code execution", ""]
            out += [f"- {r['section_id']} ({r['language']}): **{r['status']}** - {r['note']}" for r in report["code"]]
        if report["probes"]:
            out += ["", "## Live probes", ""]
            out += [f"- {p['method']} {p['url']} -> {p['status_code']} (expected {p['expect_status_min']}-"
                    f"{p['expect_status_max']}): {'confirmed' if p['passed'] else 'FAILED' if p['passed'] is False else 'error'}"
                    for p in report["probes"]]
        out += ["", "## Sources", "", "| id | tier | cited | source |", "|---|---|---|---|"]
        out += [f"| {r['id']} | {r['tier']} | {r['cited']} | [{r['title'][:70]}]({r['url']}) |" for r in report["sources"]]
    else:
        out += [f"- planned time: {s['total_minutes']} minutes", f"- rubric average: {s['rubric_avg']}/5",
                f"- simulated classroom: {s['pre_accuracy']}% correct before the lesson, {s['post_accuracy']}% after "
                f"(gain {s['learning_gain']} points)", ""]
        if report.get("review"):
            out += ["## Objective alignment", "", "| objective part | taught | practised | assessed | coverage |",
                    "|---|---|---|---|---|"]
            out += [f"| {r['objective_part']} | {r['taught_in']} | {r['practised_in']} | {r['assessed_by']} | {r['coverage']} |"
                    for r in report["review"]["alignment"]]
            out += ["", "## Rubric", ""]
            out += [f"- {r['criterion']}: {r['score']}/5 - {r['justification']}" for r in report["review"]["rubric"]]
        out += ["", "## Item analysis (simulated classroom)", "",
                "| q | correct before | correct after | discrimination | picks per option |", "|---|---|---|---|---|"]
        out += [f"| Q{i['question_index'] + 1} | {i['p_pre']} | {i['p_post']} | {i['discrimination']} | {i['option_picks']} |"
                for i in report["classroom"]["items"]]
        out += ["", "## Run sheet", ""]
        out += [f"- {r['start']:>2}-{r['end']:>2} min: {r['what']}" for r in report["measurements"]["run_sheet"]]
    out += ["", "## Findings", ""]
    for i in report["issues"]:
        out += [f"### {i['id']} [{i['severity']}] {i['category']} ({i['status']})",
                f"where: {i['section_id'] or 'whole lesson'}; found by: {i['origin']}", "", i["description"], ""]
        if i.get("evidence"):
            out += [f"evidence: {i['evidence']}", ""]
        if i.get("suggestion"):
            out += [f"suggested fix: {i['suggestion']}", ""]
        if i.get("note"):
            out += [f"resolution: {i['note']}", ""]
    if report.get("errors"):
        out += ["## Checks that could not run", ""] + [f"- {e}" for e in report["errors"]]
    return "\n".join(out) + "\n"


def build(lesson_id: str, override: str | None) -> tuple[bytes, str]:
    st = storage.load_state(lesson_id)
    g = gate(lesson_id)
    if not g["ok"] and not (override and len(override.strip()) >= 10):
        raise PermissionError("; ".join(g["reasons"]))
    ver = storage.load_version(lesson_id)
    doc, research = generate.normalize_doc(ver["doc"]), storage.load_research(lesson_id)
    lesson_md = lesson_markdown(doc, research)
    srcs, books, threads = references(doc, research)
    refs_md = lesson_md[lesson_md.index("## References"):]
    qf, qi = storage.load_qc(lesson_id, "qc_factual"), storage.load_qc(lesson_id, "qc_instructional")
    manifest = {"lesson": st["title"], "objective": st["objective"], "version": ver["version"],
                "exported_at": datetime.now().isoformat(timespec="seconds"), "gate": g,
                "override_reason": None if g["ok"] else override.strip(),
                "qc_versions": {"factual": qf and qf["version"], "instructional": qi and qi["version"]},
                "minutes": generate.lesson_minutes(doc)}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("lesson.md", lesson_md)
        html = to_html(lesson_md, doc["title"])
        for s in srcs:
            html = html.replace(f"<strong>[{s['id']}]</strong>", f"<strong id=\"ref-{s['id']}\">[{s['id']}]</strong>", 1)
        z.writestr("lesson.html", html)
        z.writestr("lesson.json", json.dumps(doc, indent=2, ensure_ascii=False))
        z.writestr("references.md", f"# References: {doc['title']}\n\n" + refs_md.split("\n", 1)[1])
        if qf:
            z.writestr("qc-1-factual.md", qc_markdown(qf, doc["title"]))
            z.writestr("qc-1-factual.json", json.dumps(qf, indent=2, ensure_ascii=False, default=str))
        if qi:
            z.writestr("qc-2-instructional.md", qc_markdown(qi, doc["title"]))
            z.writestr("qc-2-instructional.json", json.dumps(qi, indent=2, ensure_ascii=False, default=str))
        z.writestr("manifest.json", json.dumps(manifest, indent=2))

    def rec(s):
        s["exports"].append({"at": storage.now(), "version": ver["version"], "override": manifest["override_reason"]})

    storage.update_state(lesson_id, rec)
    name = re.sub(r"[^a-z0-9]+", "-", doc["title"].lower()).strip("-") + f"-v{ver['version']}.zip"
    return buf.getvalue(), name
