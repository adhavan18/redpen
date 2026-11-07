"""research step: plan queries, gather from six kinds of source in parallel, rank, chunk, embed.

partial failure is normal (a site blocks us, youtube has no captions). each failure is recorded
and shown to the instructor; the step only fails if nothing usable came back.
"""

from concurrent.futures import ThreadPoolExecutor

import numpy as np

from .. import llm, prompts
from ..schemas import ResearchPlan
from . import retrieval, sources, youtube
from .reliability import domain, is_blocked, tier, channel_tier

MAX_TEXT_SOURCES = 14
MAX_VIDEOS = 5
PASSAGES_PER_SOURCE = 40  # bm25 cut for very long pages (specs)
PASSAGES_PER_KEPT_SOURCE = 14
MAX_EMBEDDED_PASSAGES = 140  # the free embedding tier is slow; this keeps research under a minute


class ResearchError(Exception):
    pass


def fallback_plan(title: str, objective: str) -> ResearchPlan:
    return ResearchPlan(
        objective_parts=[objective], key_terms=[title],
        web_queries=[title, f"{title} explained", f"{title} tutorial examples"],
        primary_source_queries=[f"{title} official documentation"],
        misconception_queries=[title], book_queries=[title], video_queries=[f"{title} explained"])


def make_plan(title: str, objective: str, audience: str, log) -> tuple[ResearchPlan, bool]:
    try:
        plan = llm.generate(prompts.render("research_plan", title=title, objective=objective, audience=audience),
                            ResearchPlan, temperature=0.2, what="research plan", fast=True)
        if not plan.objective_parts or not plan.web_queries:
            raise ValueError("empty plan")
        return plan, True
    except Exception as e:  # noqa: BLE001
        log(f"query planner failed ({e}); using keyword fallback plan", "warn")
        return fallback_plan(title, objective), False


def run(title: str, objective: str, audience: str, log) -> tuple[dict, np.ndarray | None]:
    plan, planned = make_plan(title, objective, audience, log)
    log(f"objective split into {len(plan.objective_parts)} parts: " + " | ".join(plan.objective_parts))
    failures: list[dict] = []

    # ---- gather in parallel ----
    jobs = []
    for q in plan.web_queries[:5]:
        jobs.append(("web", q, lambda q=q: sources.web_search(q, 6)))
    for q in plan.primary_source_queries[:3]:
        jobs.append(("primary", q, lambda q=q: sources.web_search(q, 5)))
    for q in [title] + plan.key_terms[:1]:
        jobs.append(("wiki", q, lambda q=q: sources.wikipedia(q, 2)))
    for q in plan.book_queries[:2]:
        jobs.append(("book", q, lambda q=q: sources.books(q, 3)))
    for q in plan.misconception_queries[:3]:
        jobs.append(("stackoverflow", q, lambda q=q: sources.stackoverflow(q, 5)))
    for q in plan.video_queries[:2]:
        jobs.append(("video", q, lambda q=q: youtube.search(q, 6)))

    def run_job(job):
        kind, q, fn = job
        try:
            return kind, q, fn(), None
        except Exception as e:  # noqa: BLE001
            return kind, q, [], f"{type(e).__name__}: {str(e)[:160]}"

    with ThreadPoolExecutor(10) as ex:
        results = list(ex.map(run_job, jobs))

    hits: dict[str, list] = {"web": [], "primary": [], "wiki": [], "book": [], "stackoverflow": [], "video": []}
    for kind, q, rows, err in results:
        if err:
            failures.append({"kind": kind, "target": q, "error": err})
            log(f"{kind} search failed for '{q}': {err}", "warn")
        hits[kind].extend(rows)
    log(f"search returned {len(hits['web']) + len(hits['primary'])} web hits, {len(hits['wiki'])} wikipedia "
        f"articles, {len(hits['book'])} books, {len(hits['stackoverflow'])} stack overflow threads, "
        f"{len(hits['video'])} videos")

    # ---- fetch web pages ----
    seen, urls, url_kind = set(), [], {}
    for kind in ("primary", "web"):
        for h in hits[kind]:
            u = h["url"].split("#")[0]
            if u in seen or is_blocked(u) or "wikipedia.org" in u:
                continue
            seen.add(u)
            urls.append(u)
            url_kind[u] = kind
    urls = sorted(urls, key=lambda u: {"A": 0, "B": 1, "C": 2}[tier(u)[0]])[:22]
    log(f"fetching {len(urls)} pages")
    pages = sources.fetch_many(urls)

    raw: list[dict] = []
    for u in urls:
        p = pages[u]
        if "error" in p:
            failures.append({"kind": "fetch", "target": u, "error": p["error"]})
            continue
        t, why = tier(p["final_url"])
        title_guess = p["title"] or next((h["title"] for k in ("primary", "web") for h in hits[k] if h["url"] == u), u)
        raw.append({"kind": "spec" if url_kind[u] == "primary" and t == "A" else "web", "title": title_guess,
                    "url": p["final_url"], "domain": domain(p["final_url"]), "tier": t, "tier_reason": why,
                    "published": p["published"], "text": p["text"]})
    for w in {w["url"]: w for w in hits["wiki"]}.values():
        t, why = tier(w["url"])
        raw.append({"kind": "wiki", "title": w["title"], "url": w["url"], "domain": "wikipedia.org", "tier": t,
                    "tier_reason": why, "published": None, "text": w["text"]})
    for b in {b["title"].lower(): b for b in hits["book"]}.values():
        t, why = tier("", "book")
        raw.append({"kind": "book", "title": b["title"], "url": b["url"], "domain": domain(b["url"]), "tier": t,
                    "tier_reason": why, "published": b["published"], "text": b["text"], "authors": b["authors"],
                    "isbn": b.get("isbn")})
    log(f"{len(raw)} readable sources, {len([f for f in failures if f['kind'] == 'fetch'])} pages failed to load")
    if not raw:
        raise ResearchError("no readable sources were found. check the internet connection, then retry; "
                            "or reword the title so it is searchable.")

    # ---- chunk ----
    # long sources (a full rfc is ~600 passages) are cut down to their most relevant passages
    # with bm25 before anything is embedded, so one spec cannot eat the embedding budget.
    focus = " ".join([objective, title] + plan.objective_parts + plan.key_terms)
    chunks: list[dict] = []
    for si, s in enumerate(raw):
        parts = retrieval.chunk_text(s["text"])
        if len(parts) > PASSAGES_PER_SOURCE:
            scores = retrieval.BM25(parts).scores(focus)
            top = sorted(sorted(range(len(parts)), key=lambda i: -scores[i])[:PASSAGES_PER_SOURCE])
            parts = [parts[i] for i in top]
        chunks.extend({"src": si, "text": t} for t in parts)

    # ---- video candidates with transcripts ----
    vids = {v["video_id"]: v for v in hits["video"] if 90 <= v["duration"] <= 3600}
    ranked = sorted(vids.values(), key=lambda v: ({"A": 0, "B": 1, "C": 2}[channel_tier(v["channel"], v["views"])[0]],
                                                    -v["views"]))[:8]
    log(f"pulling transcripts for {len(ranked)} videos")
    enriched = youtube.enrich(ranked)
    log(f"{sum(bool(v['windows']) for v in enriched)} of {len(enriched)} videos have transcripts")
    windows = [(vi, w) for vi, v in enumerate(enriched) for w in v["windows"]]

    # ---- lexical pass: pick sources and passages before spending embedding quota ----
    queries = plan.objective_parts + [objective]
    lex = np.zeros(0)
    if chunks:
        bm = retrieval.BM25([c["text"] for c in chunks])
        lex = np.max(np.stack([bm.scores(q + " " + " ".join(plan.key_terms)) for q in queries]), axis=0)
    for si, s in enumerate(raw):
        idx = [i for i, c in enumerate(chunks) if c["src"] == si]
        s["relevance"] = round(float(lex[idx].max()), 3) if idx else 0.0
    bonus = {"A": 0.08, "B": 0.04, "C": 0.0}
    order = sorted(range(len(raw)), key=lambda i: -(raw[i]["relevance"] + bonus[raw[i]["tier"]]))
    # never let books crowd out text sources, but keep up to two
    books = [i for i in order if raw[i]["kind"] == "book"][:2]
    texts = [i for i in order if raw[i]["kind"] != "book"][:MAX_TEXT_SOURCES - len(books)]
    kept = set(books + texts)
    per_src: dict[int, int] = {}
    selected = []
    for i in sorted(range(len(chunks)), key=lambda i: -lex[i]):
        si = chunks[i]["src"]
        if si in kept and per_src.get(si, 0) < PASSAGES_PER_KEPT_SOURCE:
            per_src[si] = per_src.get(si, 0) + 1
            selected.append(i)
        if len(selected) >= MAX_EMBEDDED_PASSAGES:
            break
    selected.sort()
    chunks = [chunks[i] for i in selected]

    # ---- dense pass: embed only what survived ----
    vectors = qvecs = None
    try:
        log(f"embedding {len(chunks)} passages")
        vectors = llm.embed([c["text"] for c in chunks])
        qvecs = llm.embed(queries, task="RETRIEVAL_QUERY")
        dense = (vectors @ qvecs.T).max(axis=1)
        for si in kept:
            idx = [i for i, c in enumerate(chunks) if c["src"] == si]
            raw[si]["relevance"] = round(float(dense[idx].max()), 3) if idx else 0.0
    except Exception as e:  # noqa: BLE001
        vectors = None
        log(f"embeddings unavailable ({e}); falling back to keyword ranking", "warn")
        failures.append({"kind": "embedding", "target": "gemini", "error": str(e)[:200]})

    keep = sorted(kept, key=lambda i: ({"A": 0, "B": 1, "C": 2}[raw[i]["tier"]], -raw[i]["relevance"]))
    sid = {old: f"S{n + 1}" for n, old in enumerate(keep)}
    final_sources = []
    for old in keep:
        s = {k: v for k, v in raw[old].items() if k != "text"} | {"id": sid[old], "chars": len(raw[old]["text"])}
        final_sources.append(s)
    final_chunks = [{"id": f"c{n + 1}", "source_id": sid[c["src"]], "text": c["text"]} for n, c in enumerate(chunks)]
    final_vectors = vectors

    # ---- pick the best transcript segments per objective part (bm25 over 45s windows) ----
    wbm = retrieval.BM25([w["text"] for _, w in windows]) if windows else None
    wscores = (np.stack([wbm.scores(p + " " + " ".join(plan.key_terms)) for p in plan.objective_parts], axis=1)
               if wbm else None)
    videos = []
    for vi, v in enumerate(enriched):
        t, why = channel_tier(v["channel"], v["views"])
        rows = [k for k, (wvi, _) in enumerate(windows) if wvi == vi]
        segments = []
        if rows and wscores is not None:
            sims = wscores[rows]  # windows x objective parts
            for qi, part in enumerate(plan.objective_parts):
                col = sims[:, qi]
                best = int(col.argmax())
                lo = hi = best
                while lo > 0 and col[lo - 1] >= col[best] * 0.9 and (hi - lo) < 7:
                    lo -= 1
                while hi < len(col) - 1 and col[hi + 1] >= col[best] * 0.9 and (hi - lo) < 7:
                    hi += 1
                w0, w1 = windows[rows[lo]][1], windows[rows[hi]][1]
                segments.append({"objective_part": part, "start": w0["start"], "end": w1["end"],
                                 "score": round(float(col[best]), 3),
                                 "preview": " ".join(windows[rows[k]][1]["text"] for k in range(lo, hi + 1))[:700]})
            relevance = round(float(sims.max()), 3)
        else:
            relevance = 0.0
        videos.append({k: v[k] for k in ("video_id", "title", "channel", "duration", "views", "url")}
                      | {"tier": t, "tier_reason": why, "relevance": relevance, "segments": segments,
                         "has_transcript": bool(v["windows"]), "transcript_error": v["transcript_error"],
                         "chapters": v["chapters"]})
        if v["transcript_error"]:
            failures.append({"kind": "transcript", "target": v["url"], "error": v["transcript_error"]})
    videos.sort(key=lambda v: (-(v["has_transcript"]), {"A": 0, "B": 1, "C": 2}[v["tier"]], -v["relevance"]))
    videos = videos[:MAX_VIDEOS]

    misconceptions = []
    for n, q in enumerate(sorted({q["url"]: q for q in hits["stackoverflow"]}.values(), key=lambda q: -q["score"])[:8]):
        misconceptions.append(q | {"id": f"M{n + 1}"})

    log(f"kept {len(final_sources)} sources ({sum(s['tier'] == 'A' for s in final_sources)} tier A), "
        f"{len(final_chunks)} chunks, {len(videos)} videos, {len(misconceptions)} confusion signals", "ok")
    research = {
        "plan": plan.model_dump() | {"llm_planned": planned},
        "sources": final_sources,
        "chunks": final_chunks,
        "videos": videos,
        "misconceptions": misconceptions,
        "failures": failures,
        "embedded": final_vectors is not None,
    }
    return research, final_vectors
