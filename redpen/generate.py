"""draft step: evidence pack -> structured lesson -> validated lesson document."""

import random
import re

import numpy as np

from . import llm, prompts
from .research import retrieval
from .research.youtube import embed_url, fmt_ts
from .schemas import LessonDraft

CITE = re.compile(r"\[(S\d+)\]")


def evidence_pack(research: dict, vectors: np.ndarray | None, parts: list[str], objective: str,
                  per_part: int = 7, cap: int = 32) -> tuple[str, list[dict]]:
    idx = retrieval.Index(research["chunks"], vectors)
    src = {s["id"]: s for s in research["sources"]}
    queries = parts + [objective]
    qv = idx.query_vectors(queries)
    picked: dict[str, dict] = {}
    for q, v in zip(queries, qv):
        for c, _score in idx.search(q, k=per_part, per_source=2, qvec=v):
            picked.setdefault(c["id"], c)
        if len(picked) >= cap:
            break
    chunks = list(picked.values())[:cap]
    lines = []
    for c in sorted(chunks, key=lambda c: (int(c["source_id"][1:]), int(c["id"][1:]))):
        s = src[c["source_id"]]
        lines.append(f"[{c['source_id']} / {c['id']} / tier {s['tier']} / {s['domain'] or s['kind']}]\n{c['text']}\n")
    return "\n".join(lines), chunks


def sources_block(research: dict) -> str:
    out = []
    for s in research["sources"]:
        extra = f", {s.get('authors')}" if s.get("authors") else ""
        out.append(f"{s['id']}: {s['title']}{extra} ({s['kind']}, tier {s['tier']}: {s['tier_reason']}) {s['url']}")
    return "\n".join(out)


def misconceptions_block(research: dict) -> str:
    if not research["misconceptions"]:
        return "(none found; use common misconceptions you can support from the evidence)"
    return "\n".join(f"{m['id']} ({m['score']} votes): {m['title']} - {m['excerpt'][:240]}" for m in research["misconceptions"])


def videos_block(research: dict) -> str:
    if not research["videos"]:
        return "(no videos found; return an empty videos list)"
    out = []
    for v in research["videos"]:
        out.append(f"video_id={v['video_id']} \"{v['title']}\" by {v['channel']} ({fmt_ts(v['duration'])}, "
                   f"{v['views']:,} views, tier {v['tier']})")
        if not v["segments"]:
            out.append("  no transcript; only usable whole (segment_index -1)")
        for i, seg in enumerate(v["segments"]):
            out.append(f"  segment {i}: {fmt_ts(seg['start'])}-{fmt_ts(seg['end'])} for \"{seg['objective_part']}\": "
                       f"{seg['preview'][:260]}")
    return "\n".join(out)


def shuffle_options(q: dict, rng: random.Random) -> dict:
    """llms put the right answer in the same slot far too often. shuffle, keep rationale aligned."""
    n = len(q["options"])
    rat = q.get("distractor_rationale") or []
    if len(rat) != n:
        rat = (rat + [""] * n)[:n]
    order = list(range(n))
    rng.shuffle(order)
    return q | {"options": [q["options"][i] for i in order],
                "distractor_rationale": [rat[i] for i in order],
                "answer_index": order.index(q["answer_index"])}


def to_document(draft: LessonDraft, title: str, objective: str, audience: str, research: dict, log) -> dict:
    sections = []
    for i, s in enumerate(draft.sections):
        body = s.body_md.strip()
        if not body:
            continue
        sections.append({"id": f"s{len(sections) + 1}", "kind": s.kind, "title": s.title.strip(),
                         "minutes": max(1, int(s.minutes)), "body_md": body})
    if len(sections) < 4:
        raise ValueError(f"model returned only {len(sections)} usable sections")

    rng = random.Random(title + objective)
    quiz = []
    for q in draft.quiz:
        opts = [o.strip() for o in q.options if o.strip()]
        if len(opts) < 3 or not (0 <= q.answer_index < len(q.options)):
            log(f"dropped malformed quiz question: {q.question[:60]}", "warn")
            continue
        quiz.append(shuffle_options({"question": q.question.strip(), "options": opts, "answer_index": q.answer_index,
                                     "explanation": q.explanation.strip(), "objective_part": q.objective_part,
                                     "distractor_rationale": q.distractor_rationale}, rng))
    for i, q in enumerate(quiz):
        q["id"] = f"q{i + 1}"

    vids = {v["video_id"]: v for v in research["videos"]}
    videos = []
    for dv in draft.videos:
        v = vids.get(dv.video_id)
        if not v:
            log(f"model picked a video that was not in the research ({dv.video_id}); dropped", "warn")
            continue
        if 0 <= dv.segment_index < len(v["segments"]):
            seg = v["segments"][dv.segment_index]
            start, end = seg["start"], seg["end"]
        else:
            start, end = 0.0, float(v["duration"])
        sec_i = min(max(dv.after_section, 0), len(sections) - 1)
        videos.append({"video_id": v["video_id"], "title": v["title"], "channel": v["channel"],
                       "url": embed_url(v["video_id"], start), "start": start, "end": end,
                       "watch_minutes": round((end - start) / 60, 1), "in_lesson": bool(dv.in_lesson),
                       "why": dv.why, "after_section": sections[sec_i]["id"], "tier": v["tier"]})
    # at most one in-lesson clip, and only if it is short
    seen_in = False
    for v in videos:
        if v["in_lesson"] and (seen_in or v["watch_minutes"] > 7):
            v["in_lesson"] = False
        seen_in = seen_in or v["in_lesson"]

    return {"title": title, "objective": objective, "audience": audience,
            "objective_parts": draft.objective_parts or [objective], "sections": sections, "quiz": quiz,
            "quiz_minutes": max(1, int(draft.quiz_minutes)), "videos": videos,
            "evidence_gaps": draft.evidence_gaps}


def run(state: dict, research: dict, vectors, log) -> dict:
    parts = research["plan"]["objective_parts"]
    evidence, chunks = evidence_pack(research, vectors, parts, state["objective"])
    log(f"evidence pack: {len(chunks)} passages from {len({c['source_id'] for c in chunks})} sources")
    prompt = prompts.render(
        "generate_lesson", title=state["title"], objective=state["objective"], audience=state["audience"],
        objective_parts="\n".join(f"- {p}" for p in parts), evidence=evidence, sources=sources_block(research),
        misconceptions=misconceptions_block(research), videos=videos_block(research))
    log("writing the lesson")
    draft = llm.generate(prompt, LessonDraft, temperature=0.5, what="lesson generation")
    doc = to_document(draft, state["title"], state["objective"], state["audience"], research, log)
    log(f"draft: {len(doc['sections'])} sections, {len(doc['quiz'])} questions, {len(doc['videos'])} videos, "
        f"{lesson_minutes(doc)} min", "ok")
    return doc


def lesson_minutes(doc: dict) -> int:
    return (sum(s["minutes"] for s in doc["sections"]) + doc.get("quiz_minutes", 0)
            + round(sum(v["watch_minutes"] for v in doc.get("videos", []) if v["in_lesson"])))


def cited_ids(doc: dict) -> set[str]:
    ids = set()
    for s in doc["sections"]:
        ids.update(CITE.findall(s["body_md"]))
    return ids
