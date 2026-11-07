import random

import pytest

from redpen import config, export, generate, storage
from redpen.qc import execute, instructional
from redpen.qc.common import Issues, contains, sentences
from redpen.research import retrieval
from redpen.research.reliability import tier


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)


def doc(**kw):
    d = {"title": "T", "objective": "Explain things clearly to students", "audience": "x",
         "objective_parts": ["Explain GET and POST", "Distinguish 2xx, 4xx and 5xx"],
         "sections": [
             {"id": "s1", "kind": "hook", "title": "Hook", "minutes": 3, "body_md": "Why it matters."},
             {"id": "s2", "kind": "concept", "title": "GET and POST", "minutes": 8,
              "body_md": "GET retrieves a resource [S1]. POST submits data [S1]."},
             {"id": "s3", "kind": "example", "title": "Ex", "minutes": 6,
              "body_md": "```python\nprint(1 + 1)\n```\n\n```output\n2\n```"},
             {"id": "s4", "kind": "activity", "title": "Do", "minutes": 10, "body_md": "1. Try it."},
             {"id": "s5", "kind": "recap", "title": "Recap", "minutes": 2, "body_md": "- done"},
         ],
         "quiz": [{"id": "q1", "question": "?", "options": ["a", "b", "c", "d"], "answer_index": 0, "explanation": "",
                   "objective_part": "Explain GET and POST"}],
         "quiz_minutes": 5, "videos": [], "evidence_gaps": []}
    d.update(kw)
    return d


# ---------- code execution ----------

def test_code_block_runs_and_matches():
    [r] = execute.run_all(doc()["sections"])
    assert r["status"] == "pass", r


def test_code_output_mismatch_is_caught():
    secs = [{"id": "s1", "body_md": "```python\nprint(3 * 3)\n```\n```output\n10\n```"}]
    [r] = execute.run_all(secs)
    assert r["status"] == "mismatch" and r["missing"] == ["10"]


def test_ellipsis_is_a_wildcard():
    ok, _ = execute.compare("Status: 200\nDate: ...", "Status: 200\nServer: x\nDate: Sat, 07 Nov 2026")
    assert ok


def test_crash_and_denylist():
    [r] = execute.run_all([{"id": "s", "body_md": "```python\nraise SystemExit('boom')\n```"}])
    assert r["status"] == "error"
    [r] = execute.run_all([{"id": "s", "body_md": "```python\nimport subprocess\n```"}])
    assert r["status"] == "skipped"


# ---------- retrieval ----------

def test_chunking_keeps_text_and_bounds_size():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 60 for i in range(30))
    chunks = retrieval.chunk_text(text)
    assert len(chunks) > 5 and all(len(c) < 1500 for c in chunks)


def test_bm25_ranks_the_relevant_passage_first():
    docs = ["cats sleep all day", "a 404 status code means the resource was not found", "pasta recipes"]
    s = retrieval.BM25(docs).scores("what does 404 not found mean")
    assert s.argmax() == 1


def test_copied_text_detection():
    src = "the quick brown fox jumps over the lazy dog near the river bank every single morning"
    idx = retrieval.ngram_index([src], n=12)
    hits = retrieval.ngram_overlap("intro: the quick brown fox jumps over the lazy dog near the river bank every day",
                                   idx, n=12)
    assert hits and hits[0].startswith("the quick brown fox")
    assert not retrieval.ngram_overlap("a completely different sentence about http methods and codes here", idx, n=12)


# ---------- quote verification + sentences ----------

def test_contains_ignores_markdown_and_quotes():
    assert contains("A **GET** request is `safe` ’really’.", "a get request is safe 'really'")
    assert not contains("GET is safe.", "POST is safe")


def test_sentence_split_skips_code():
    s = sentences("First one. Second one!\n\n```python\nx = 1. y\n```\n- third item")
    assert s == ["First one.", "Second one!", "third item"]


# ---------- reliability ----------

def test_tiers():
    assert tier("https://www.rfc-editor.org/rfc/rfc9110")[0] == "A"
    assert tier("https://developer.mozilla.org/en-US/docs/Web/HTTP")[0] == "A"
    assert tier("https://en.wikipedia.org/wiki/HTTP")[0] == "B"
    assert tier("https://someone.medium.com/http")[0] == "C"


# ---------- generation post-processing ----------

def test_shuffle_keeps_answer_and_rationale_aligned():
    q = {"options": ["right", "w1", "w2", "w3"], "answer_index": 0,
         "distractor_rationale": ["correct", "r1", "r2", "r3"]}
    for seed in range(20):
        out = generate.shuffle_options(q, random.Random(seed))
        assert out["options"][out["answer_index"]] == "right"
        assert out["distractor_rationale"][out["answer_index"]] == "correct"


def test_lesson_minutes_counts_sections_quiz_and_inlesson_clips():
    d = doc(videos=[{"in_lesson": True, "watch_minutes": 4.0}, {"in_lesson": False, "watch_minutes": 9.0}])
    assert generate.lesson_minutes(d) == 3 + 8 + 6 + 10 + 2 + 5 + 4


# ---------- qc 2 deterministic checks ----------

def test_time_budget_and_unassessed_part_are_flagged():
    d = doc()
    d["sections"][3]["minutes"] = 30  # pushes the lesson to 54 minutes
    issues = Issues("I", "instructional")
    m = instructional.measurements(d, issues)
    cats = {i["category"] for i in issues.items}
    assert m["total_minutes"] == 54 and "over time" in cats
    assert "unassessed objective" in cats  # nothing assesses "Distinguish 2xx, 4xx and 5xx"
    assert m["run_sheet"][-1]["what"] == "knowledge check"


# ---------- storage ----------

def test_versions_are_append_only_and_conflicts_are_refused():
    st = storage.create("HTTP", "Explain GET and POST to students", "x")
    v1 = storage.save_version(st["id"], doc(), "ai", "draft")
    v2 = storage.save_version(st["id"], doc(title="edited"), "instructor", "edit", base_version=v1)
    assert (v1, v2) == (1, 2)
    assert storage.load_version(st["id"], 1)["doc"]["title"] == "T"
    with pytest.raises(storage.ConflictError):
        storage.save_version(st["id"], doc(), "instructor", "stale tab", base_version=1)


def test_edit_marks_qc_stale_and_gate_blocks_export():
    st = storage.create("HTTP", "Explain GET and POST to students", "x")
    v = storage.save_version(st["id"], doc(), "ai", "draft")
    storage.update_state(st["id"], lambda s: s["steps"]["qc_factual"].update(status="done"))
    storage.save_qc(st["id"], "qc_factual", {"version": v, "issues": [{"severity": "high", "status": "open"}]})
    g = export.gate(st["id"])
    assert not g["ok"] and any("high-severity" in r for r in g["reasons"])
    storage.save_version(st["id"], doc(), "instructor", "edit")
    assert storage.load_state(st["id"])["steps"]["qc_factual"]["status"] == "stale"
    with pytest.raises(PermissionError):
        export.build(st["id"], override=None)


def test_interrupted_steps_become_retryable():
    st = storage.create("HTTP", "Explain GET and POST to students", "x")
    storage.update_state(st["id"], lambda s: s["steps"]["research"].update(status="running"))
    storage.recover_interrupted()
    s = storage.load_state(st["id"])["steps"]["research"]
    assert s["status"] == "failed" and "restart" in s["error"]


def test_prompt_render_accepts_a_name_variable():
    from redpen import prompts

    out = prompts.render("qc_student_pre", name="Asha", level="novice", background="b", habits="h",
                         knowledge="k", quiz="Q0. ?", lesson="")
    assert "Asha" in out and "{{" not in out


def test_knowledge_state_differs_by_level():
    states = {lv: instructional.knowledge_state(lv, ["GET", "POST", "4xx"]) for lv in
              ("novice", "struggling", "average", "strong")}
    assert "never studied" in states["novice"] and len(set(states.values())) == 4


def test_quote_check_ignores_table_pipes_but_not_words():
    src = "| 1xx Informational | Indicates that the request was received and is being processed |"
    assert contains(src, "1xx Informational Indicates that the request was received")
    assert not contains(src, "1xx Informational indicates the request failed")


def test_rate_limiter_queues_past_the_budget(monkeypatch):
    from redpen import llm

    slept = []
    monkeypatch.setattr(llm.time, "sleep", lambda s: (slept.append(s), clock.__setitem__(0, clock[0] + s)))
    clock = [1000.0]
    monkeypatch.setattr(llm.time, "monotonic", lambda: clock[0])
    lim = llm._RateLimiter(rpm=3)
    for _ in range(3):
        lim.wait("m")
    assert not slept
    lim.wait("m")  # fourth call inside the same minute has to wait
    assert slept and 59 < slept[0] <= 60.1


def test_export_lists_sources_cited_in_combined_form():
    st = storage.create("HTTP", "Explain GET and POST to students", "x")
    d = doc()
    d["sections"][1]["body_md"] = "GET retrieves a resource [S1, S2]."
    storage.save_version(st["id"], d, "ai", "draft")  # stored un-normalized, like older lessons
    research = {"sources": [{"id": f"S{i}", "kind": "web", "title": f"t{i}", "url": f"https://x/{i}", "tier": "B",
                             "tier_reason": "r"} for i in (1, 2)], "misconceptions": []}
    md = export.lesson_markdown(generate.normalize_doc(storage.load_version(st["id"])["doc"]), research)
    assert "**[S2]**" in md and "[S1, S2]" not in md
