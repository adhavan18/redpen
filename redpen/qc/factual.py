"""qc layer 1: research and factual accuracy.

deterministic checks (no llm):   citation coverage, unknown citations, source tiers, copied text,
                                 executed code output, live http probes, verifier-quote check
llm checks (separate prompts):   claim extraction, claim-vs-evidence verdicts, google-grounded
                                 second opinion, inconsistency / misleading / gap review
"""

import re
from collections import Counter

from .. import generate, llm, prompts
from ..research import retrieval
from ..schemas import ClaimList, IssueList, VerdictList
from . import execute, probes
from .common import Issues, contains, lesson_text, section_ref, sentences

FACT_KINDS = {"concept", "example", "misconceptions"}
MAX_CLAIMS = 28


def citation_audit(doc: dict, research: dict, issues: Issues) -> list[dict]:
    src = {s["id"]: s for s in research["sources"]}
    rows = []
    for s in doc["sections"]:
        sents = sentences(s["body_md"])
        cited = [x for x in sents if generate.CITE.search(x)]
        ids = Counter(generate.CITE.findall(s["body_md"]))
        unknown = sorted(i for i in ids if i not in src)
        tiers = Counter(src[i]["tier"] for i in ids if i in src)
        coverage = len(cited) / len(sents) if sents else 1.0
        rows.append({"section_id": s["id"], "title": s["title"], "kind": s["kind"], "sentences": len(sents),
                     "cited_sentences": len(cited), "coverage": round(coverage, 2), "sources": dict(ids),
                     "tiers": dict(tiers), "unknown": unknown})
        for u in unknown:
            issues.add("high", "unknown citation", s["id"], f"cites [{u}], which is not one of the research sources",
                       suggestion=f"replace [{u}] with a real source id or remove the claim")
        if s["kind"] in FACT_KINDS and sents and coverage < 0.25:
            issues.add("medium", "uncited section", s["id"],
                       f"only {len(cited)} of {len(sents)} sentences carry a citation in a {s['kind']} section",
                       suggestion="add source ids to the factual sentences, or move unsupported material out")
        if ids and set(tiers) == {"C"}:
            issues.add("medium", "weak sources", s["id"], "every citation in this section is a tier C source",
                       evidence=", ".join(f"{i}: {src[i]['domain']}" for i in ids if i in src),
                       suggestion="back the key claims with a tier A or B source")
    return rows


def source_audit(doc: dict, research: dict, issues: Issues) -> list[dict]:
    used = Counter()
    for s in doc["sections"]:
        used.update(generate.CITE.findall(s["body_md"]))
    rows = []
    for s in research["sources"]:
        rows.append({"id": s["id"], "title": s["title"], "url": s["url"], "kind": s["kind"], "tier": s["tier"],
                     "tier_reason": s["tier_reason"], "relevance": s["relevance"], "cited": used.get(s["id"], 0),
                     "published": s.get("published")})
    tiers = Counter(s["tier"] for s in research["sources"] if used.get(s["id"]))
    if used and not tiers.get("A"):
        issues.add("medium", "no primary source", None, "the lesson does not cite a single tier A (primary) source",
                   suggestion="cite the specification or official documentation for the core definitions")
    for v in doc.get("videos", []):
        if v.get("tier") == "C":
            issues.add("low", "video source", v["after_section"],
                       f"video \"{v['title']}\" is from an unrecognised channel ({v['channel']})",
                       suggestion="watch it before publishing or replace it with a known educational channel")
    return rows


def originality(doc: dict, research: dict, issues: Issues) -> list[dict]:
    idx = retrieval.ngram_index([c["text"] for c in research["chunks"]], n=12)
    rows = []
    for s in doc["sections"]:
        for span in retrieval.ngram_overlap(re.sub(r"```.*?```", " ", s["body_md"], flags=re.S),
                                            idx, n=12):
            rows.append({"section_id": s["id"], "span": span, "words": len(span.split())})
    if rows:
        by_sec = Counter(r["section_id"] for r in rows)
        for sid, n in by_sec.items():
            spans = [r["span"] for r in rows if r["section_id"] == sid]
            issues.add("medium", "copied text", sid, f"{n} passage(s) of 12+ words match a source word for word",
                       evidence=" / ".join(f'"{x}"' for x in spans[:3]),
                       suggestion="paraphrase these passages and keep the citation")
    return rows


def extract_claims(doc: dict) -> list[dict]:
    res = llm.generate(prompts.render("qc_extract_claims", lesson=lesson_text(doc, with_quiz=False),
                                      max_claims=MAX_CLAIMS),
                       ClaimList, temperature=0.0, what="claim extraction", fast=True)
    out = []
    for c in res.claims[:MAX_CLAIMS]:
        sid = section_ref(doc, c.section_index)
        if sid is None or sid == "quiz":
            continue
        body = next(s["body_md"] for s in doc["sections"] if s["id"] == sid)
        out.append({"section_id": sid, "sentence": c.sentence, "claim": c.claim, "cited": c.cited,
                    "testable": c.testable, "located": contains(body, c.sentence)})
    return out


def verify_claims(claims: list[dict], index: retrieval.Index, chunk_by_id: dict, log) -> None:
    qv = index.query_vectors([c["claim"] for c in claims])
    for c, v in zip(claims, qv):
        found = index.search(c["claim"], k=3, per_source=1, qvec=v)
        if c["cited"]:
            found += index.search(c["claim"], k=2, per_source=2, source_ids=set(c["cited"]), qvec=v)
        seen, ev = set(), []
        for ch, score in sorted(found, key=lambda x: -x[1]):
            if ch["id"] not in seen:
                seen.add(ch["id"])
                ev.append(ch)
        c["evidence_ids"] = [ch["id"] for ch in ev[:4]]

    for start in range(0, len(claims), 8):
        batch = claims[start:start + 8]
        blocks = []
        for i, c in enumerate(batch):
            ev = "\n".join(f"  ({chunk_by_id[e]['id']}, source {chunk_by_id[e]['source_id']}) "
                           f"{chunk_by_id[e]['text'][:1100]}" for e in c["evidence_ids"])
            blocks.append(f"CLAIM {i}: {c['claim']}\n  lesson sentence: {c['sentence']}\n  evidence:\n{ev or '  (none)'}")
        res = llm.generate(prompts.render("qc_verify_claims", claims="\n\n".join(blocks)), VerdictList, thinking="low",
                           temperature=0.0, what="claim verification")
        for v in res.verdicts:
            if not 0 <= v.claim_index < len(batch):
                continue
            c = batch[v.claim_index]
            chunk = chunk_by_id.get(v.evidence_id)
            quote_ok = bool(chunk and v.quote and contains(chunk["text"], v.quote))
            verdict = v.verdict
            note = None
            if verdict in ("supported", "contradicted") and not quote_ok:
                # the verifier's own quote is not in the source: do not trust its verdict
                note = f"verifier said {verdict} but its quote was not found in the source; downgraded"
                verdict = "partial" if verdict == "supported" else "unsupported"
            c.update({"verdict": verdict, "evidence_id": v.evidence_id if chunk else "",
                      "source_id": chunk["source_id"] if chunk else None, "quote": v.quote,
                      "quote_verified": quote_ok, "reasoning": v.reasoning, "fix": v.fix, "downgrade_note": note})
        log(f"verified claims {start + 1}-{start + len(batch)}")
    for c in claims:
        c.setdefault("verdict", "unsupported")
        c.setdefault("reasoning", "verifier returned no verdict for this claim")
        c.setdefault("quote_verified", False)


def external_check(claims: list[dict], log) -> str | None:
    targets = [c for c in claims if c["verdict"] in ("unsupported", "contradicted", "partial")][:10]
    if not targets:
        return None
    listing = "\n".join(f"{i}: {c['claim']}" for i, c in enumerate(targets))
    try:
        text, pages = llm.grounded(prompts.render("qc_external_check", claims=listing), what="google-grounded check")
        rows = llm.parse_json_loose(text)
        for r in rows if isinstance(rows, list) else []:
            i = r.get("i")
            if isinstance(i, int) and 0 <= i < len(targets):
                targets[i]["external"] = {"verdict": r.get("verdict", "unclear"), "note": r.get("note", ""),
                                          "pages": pages[:5]}
        log(f"google-grounded second opinion on {len(targets)} claims")
        return None
    except Exception as e:  # noqa: BLE001
        log(f"grounded check unavailable: {e}", "warn")
        return str(e)[:200]


def claim_issues(claims: list[dict], issues: Issues) -> None:
    for c in claims:
        ext = c.get("external") or {}
        ext_note = f" Google-grounded check: {ext['verdict']} - {ext['note']}" if ext else ""
        if c["verdict"] == "contradicted" or ext.get("verdict") == "false":
            issues.add("high", "contradicted claim", c["section_id"], f"\"{c['claim']}\" is contradicted by the evidence."
                       + ext_note, evidence=c.get("quote", ""), suggestion=c.get("fix", ""), origin="llm",
                       sentence=c["sentence"])
        elif c["verdict"] == "unsupported":
            sev = "low" if ext.get("verdict") == "true" else "high" if ext.get("verdict") == "misleading" else "medium"
            issues.add(sev, "unsupported claim", c["section_id"],
                       f"\"{c['claim']}\" is not backed by any research source." + ext_note,
                       evidence=c.get("reasoning", ""),
                       suggestion=c.get("fix") or "add a source for this claim or remove it", origin="llm",
                       sentence=c["sentence"])
        elif c["verdict"] == "partial":
            issues.add("medium" if ext.get("verdict") in ("misleading", "false") else "low", "partially supported",
                       c["section_id"], f"\"{c['claim']}\" goes beyond what the source says." + ext_note,
                       evidence=c.get("quote", ""), suggestion=c.get("fix", ""), origin="llm", sentence=c["sentence"])


def code_issues(results: list[dict], issues: Issues) -> None:
    for r in results:
        if r["status"] == "mismatch":
            issues.add("high", "wrong code output", r["section_id"],
                       "a code example does not print what the lesson says it prints",
                       evidence="expected but not produced: " + " | ".join(r.get("missing", [])[:3])
                       + "\nactual output:\n" + (r["actual"] or "")[:400],
                       suggestion="replace the output block with the real output, or fix the code", origin="executed")
        elif r["status"] in ("error", "timeout"):
            issues.add("high", "broken code", r["section_id"], f"a {r['language']} example fails when run: {r['note']}",
                       evidence=(r.get("stderr") or "")[-400:], suggestion="fix the example so it runs as written",
                       origin="executed")


def run(state: dict, doc: dict, research: dict, vectors, log) -> dict:
    issues = Issues("F", "factual")
    errors: list[str] = []
    chunk_by_id = {c["id"]: c for c in research["chunks"]}
    index = retrieval.Index(research["chunks"], vectors)

    log("auditing citations and sources")
    cites = citation_audit(doc, research, issues)
    srcs = source_audit(doc, research, issues)
    copied = originality(doc, research, issues)

    log("running code examples")
    code = execute.run_all(doc["sections"])
    code_issues(code, issues)
    if code:
        log(f"code: {sum(r['status'] == 'pass' for r in code)}/{len(code)} examples print what the lesson claims",
            "ok" if all(r["status"] in ("pass", "ran", "skipped") for r in code) else "warn")

    log("extracting claims")
    claims = extract_claims(doc)
    log(f"{len(claims)} claims extracted; checking each against the research")
    verify_claims(claims, index, chunk_by_id, log)
    if err := external_check(claims, log):
        errors.append(f"google-grounded check skipped: {err}")

    probe_rows: list[dict] = []
    try:
        planned = probes.plan(claims)
        if planned:
            log(f"sending {len(planned)} live http probes")
        for p in planned:
            r = probes.execute(p)
            probe_rows.append(r)
            c = claims[r["claim_index"]]
            c.setdefault("probes", []).append(r)
            if r["passed"] is False:
                issues.add("high", "failed live test", c["section_id"],
                           f"\"{c['claim']}\" was tested live and did not hold: {r['method']} {r['url']} returned "
                           f"{r['status_code']}, expected {r['expect_status_min']}-{r['expect_status_max']}",
                           evidence=r["rationale"], suggestion="correct the claim to match observed behaviour",
                           origin="executed", sentence=c["sentence"])
    except Exception as e:  # noqa: BLE001
        errors.append(f"live probes skipped: {e}")
        log(f"live probes skipped: {e}", "warn")

    claim_issues(claims, issues)

    log("reviewing for inconsistencies, misleading simplifications and gaps")
    try:
        from ..generate import evidence_pack

        ev, _ = evidence_pack(research, vectors, research["plan"]["objective_parts"], doc["objective"], per_part=4, cap=16)
        summary = "\n".join(f"- [{c['verdict']}] {c['claim']}" for c in claims)
        review = llm.generate(prompts.render("qc_factual_review", objective=doc["objective"], lesson=lesson_text(doc),
                                             evidence=ev, claim_summary=summary),
                              IssueList, temperature=0.1, what="factual review")
        for it in review.issues:
            issues.add(it.severity, it.category, section_ref(doc, it.section_index), it.description,
                       evidence=it.evidence, suggestion=it.suggestion, origin="llm")
    except Exception as e:  # noqa: BLE001
        errors.append(f"gap/inconsistency review failed: {e}")
        log(f"gap review failed: {e}", "warn")

    verdicts = Counter(c["verdict"] for c in claims)
    n = max(1, len(claims))
    summary = {
        "claims": len(claims), **{k: verdicts.get(k, 0) for k in ("supported", "partial", "unsupported", "contradicted")},
        "accuracy": round((verdicts.get("supported", 0) + 0.5 * verdicts.get("partial", 0)) / n * 100),
        "quotes_verified": sum(c.get("quote_verified", False) for c in claims),
        "code_total": len(code), "code_pass": sum(r["status"] == "pass" for r in code),
        "probes_total": len(probe_rows), "probes_pass": sum(r["passed"] is True for r in probe_rows),
        "copied_spans": len(copied),
        "cited_sources": sum(1 for s in srcs if s["cited"]),
        "tier_a_cited": sum(1 for s in srcs if s["cited"] and s["tier"] == "A"),
        "issues": Counter(i["severity"] for i in issues.items),
    }
    log(f"factual qc: {summary['accuracy']}% claim accuracy, {len(issues.items)} issues", "ok")
    return {"layer": "qc_factual", "summary": summary, "claims": claims, "code": code, "probes": probe_rows,
            "citations": cites, "sources": srcs, "copied": copied, "issues": issues.sorted(), "errors": errors}
