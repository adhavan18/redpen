"""qc layer 2: instructional quality.

deterministic:  structure, 45-minute budget, per-section pacing (words vs minutes), objective
                coverage of the quiz, sentence length, run sheet
simulated classroom: four fixed student profiles take the quiz closed-book, then again after
                reading only the lesson. classic item analysis on their answers: difficulty,
                learning gain, discrimination, distractor use. llm-simulated students are an
                approximation (see readme), so this ranks questions to look at, it does not grade them.
llm review:     objective alignment matrix, 8-criterion rubric, issues with concrete fixes
"""

import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from .. import config, generate, llm, prompts
from ..schemas import InstructionalReview, StudentRun
from .common import Issues, contains, lesson_text, section_ref, sentences

WPM = 180

COHORT = [
    {"name": "Asha", "level": "novice",
     "background": "first-year student, has written a little Python in school",
     "habits": "reads every word, takes analogies literally, gets lost when two terms are introduced at once"},
    {"name": "Ravi", "level": "struggling",
     "background": "second-year student who passed programming courses by memorising, weak English reading speed",
     "habits": "skims, reads headings and bold text, mixes up similar-looking terms and numbers"},
    {"name": "Meera", "level": "average",
     "background": "builds small projects from tutorials, has used libraries without knowing what happens underneath",
     "habits": "reads explanations, skips long paragraphs, tries the examples"},
    {"name": "Karthik", "level": "strong",
     "background": "has shipped real projects and is comfortable reading documentation",
     "habits": "reads quickly, notices imprecise wording, answers from understanding not memory"},
]
TOP = {"average", "strong"}


def knowledge_state(level: str, terms: list[str]) -> str:
    """an llm playing a student knows everything unless told exactly what the student does not
    know (the qg-sms approach: give each simulated student an explicit level of understanding).
    without this every 'novice' aces the pre-test and the learning-gain signal is meaningless."""
    terms = [t for t in terms if t][:8] or ["the topic of this lesson"]
    half = max(1, len(terms) // 2)
    listing = ", ".join(terms)
    return {
        "novice": f"Before this lesson you have never studied any of these and do not know what they mean: {listing}.",
        "struggling": f"You have heard these terms once in a lecture but remember them vaguely and often mix them up: "
                      f"{listing}.",
        "average": f"You have used {', '.join(terms[:half])} in tutorials without understanding the details. "
                   f"You have not learned {', '.join(terms[half:]) or 'the finer points'}.",
        "strong": f"You have worked with these in real projects: {listing}.",
    }[level]


def quiz_block(doc: dict) -> str:
    out = []
    for qi, q in enumerate(doc["quiz"]):
        out.append(f"Q{qi}. {q['question']}")
        out += [f"   {oi}) {o}" for oi, o in enumerate(q["options"])]
    return "\n".join(out)


def reading_minutes(md: str) -> float:
    code_lines = sum(len(b.splitlines()) for b in re.findall(r"```.*?```", md, re.S))
    words = len(re.sub(r"```.*?```", " ", md, flags=re.S).split())
    return words / WPM + code_lines * 0.15


def part_of(question_part: str, parts: list[str]) -> str | None:
    """match the model's objective_part label to the real objective parts by word overlap."""
    qa = set(re.findall(r"\w+", question_part.lower()))
    best, score = None, 0.0
    for p in parts:
        pa = set(re.findall(r"\w+", p.lower()))
        s = len(qa & pa) / max(1, len(qa | pa))
        if s > score:
            best, score = p, s
    return best if score >= 0.2 else None


def measurements(doc: dict, issues: Issues) -> dict:
    kinds = Counter(s["kind"] for s in doc["sections"])
    for k, label in (("hook", "an opening hook"), ("concept", "a concept explanation"), ("example", "a worked example"),
                     ("activity", "a hands-on activity"), ("recap", "a recap")):
        if not kinds.get(k):
            issues.add("high" if k in ("concept", "example", "activity") else "medium", "missing component", None,
                       f"the lesson has no {label} section",
                       suggestion=f"add {label}; the 45-minute lesson needs explanation, example, practice and a check")
    if len(doc.get("quiz", [])) < 4:
        issues.add("high", "thin assessment", "quiz", f"the knowledge check has only {len(doc.get('quiz', []))} questions",
                   suggestion="use 5-6 questions, at least one per objective part")

    total = generate.lesson_minutes(doc)
    if total > config.LESSON_MINUTES:
        issues.add("high", "over time", None, f"planned time is {total} minutes, over the {config.LESSON_MINUTES}-minute limit",
                   suggestion="cut or shorten the lowest-value section; do not cut the activity or the check")
    elif total < config.MIN_LESSON_MINUTES:
        issues.add("medium", "under time", None, f"planned time is only {total} of {config.LESSON_MINUTES} minutes",
                   suggestion="use the spare time for a second worked example or a longer activity")

    pacing = []
    for s in doc["sections"]:
        rm = reading_minutes(s["body_md"])
        row = {"section_id": s["id"], "title": s["title"], "kind": s["kind"], "planned": s["minutes"],
               "reading": round(rm, 1), "words": len(s["body_md"].split())}
        pacing.append(row)
        if s["kind"] != "activity" and rm > s["minutes"] * 1.35 + 0.5:
            issues.add("medium", "pacing", s["id"],
                       f"\"{s['title']}\" takes about {rm:.1f} min to read but is planned for {s['minutes']} min",
                       suggestion="trim it or give it more minutes from elsewhere")
        if s["kind"] == "concept" and rm < s["minutes"] * 0.3:
            issues.add("low", "pacing", s["id"],
                       f"\"{s['title']}\" is about {rm:.1f} min of reading for a {s['minutes']}-minute slot",
                       suggestion="add an example or a check-your-understanding prompt")

    parts = doc.get("objective_parts") or [doc["objective"]]
    q_by_part = Counter()
    for q in doc.get("quiz", []):
        p = part_of(q.get("objective_part", ""), parts)
        q["matched_part"] = p
        if p:
            q_by_part[p] += 1
    for p in parts:
        if not q_by_part.get(p):
            issues.add("high", "unassessed objective", "quiz", f"no quiz question assesses \"{p}\"",
                       suggestion=f"add a question where the learner has to {p[0].lower() + p[1:]}")

    long_sents = []
    for s in doc["sections"]:
        for x in sentences(s["body_md"]):
            n = len(x.split())
            if n > 38:
                long_sents.append({"section_id": s["id"], "words": n, "sentence": x})
    by_sec = Counter(x["section_id"] for x in long_sents)
    for sid, n in by_sec.items():
        if n >= 2:
            ex = next(x for x in long_sents if x["section_id"] == sid)
            issues.add("low", "readability", sid, f"{n} sentences over 38 words",
                       evidence=ex["sentence"][:300], suggestion="split long sentences; one idea per sentence")
    answer_slots = Counter(q["answer_index"] for q in doc.get("quiz", []))

    # minute-by-minute run sheet for an instructor
    t, sheet = 0.0, []
    vids_after = {}
    for v in doc.get("videos", []):
        if v["in_lesson"]:
            vids_after.setdefault(v["after_section"], []).append(v)
    for s in doc["sections"]:
        sheet.append({"start": round(t), "end": round(t + s["minutes"]), "what": s["title"], "kind": s["kind"]})
        t += s["minutes"]
        for v in vids_after.get(s["id"], []):
            sheet.append({"start": round(t), "end": round(t + v["watch_minutes"]), "what": f"video: {v['title']}",
                          "kind": "video"})
            t += v["watch_minutes"]
    if doc.get("quiz"):
        sheet.append({"start": round(t), "end": round(t + doc["quiz_minutes"]), "what": "knowledge check", "kind": "quiz"})

    return {"total_minutes": total, "pacing": pacing, "quiz_per_part": {p: q_by_part.get(p, 0) for p in parts},
            "long_sentences": long_sents[:12], "answer_slots": dict(answer_slots), "run_sheet": sheet,
            "section_kinds": dict(kinds)}


def simulate(doc: dict, log, terms: list[str] | None = None) -> dict:
    quiz = quiz_block(doc)
    lesson = lesson_text(doc, with_quiz=False)

    def run(args):
        student, condition = args
        name = "qc_student_pre" if condition == "pre" else "qc_student_post"
        try:
            res = llm.generate(prompts.render(name, quiz=quiz, lesson=lesson, knowledge=knowledge_state(student["level"], terms or []), **student), StudentRun,
                               temperature=0.7, what=f"simulated student {student['name']} ({condition})", fast=True, thinking="low")
            return student, condition, res, None
        except Exception as e:  # noqa: BLE001
            return student, condition, None, str(e)[:200]

    jobs = [(s, c) for c in ("pre", "post") for s in COHORT]
    with ThreadPoolExecutor(3) as ex:
        results = list(ex.map(run, jobs))

    responses = {"pre": {}, "post": {}}
    confusions, failures = [], []
    for student, cond, res, err in results:
        if err:
            failures.append(f"{student['name']} ({cond}): {err}")
            continue
        answers = {}
        for a in res.answers:
            if 0 <= a.question_index < len(doc["quiz"]):
                grounded = bool(a.lesson_quote) and contains(lesson, a.lesson_quote)
                answers[a.question_index] = {"chosen": a.chosen_index, "confidence": a.confidence,
                                             "quote": a.lesson_quote, "grounded": grounded}
        responses[cond][student["name"]] = answers
        if cond == "post":
            for c in res.confusions:
                sid = section_ref(doc, c.section_index)
                if sid and sid != "quiz":
                    confusions.append({"student": student["name"], "level": student["level"], "section_id": sid,
                                       "quote": c.quote, "why": c.why})
    log(f"classroom: {len(responses['pre'])} pre-tests and {len(responses['post'])} post-tests completed")

    levels = {s["name"]: s["level"] for s in COHORT}
    items = []
    for qi, q in enumerate(doc["quiz"]):
        row = {"question_index": qi, "id": q["id"], "question": q["question"], "answer_index": q["answer_index"],
               "options": q["options"]}
        for cond in ("pre", "post"):
            got = {n: r[qi] for n, r in responses[cond].items() if qi in r}
            correct = [n for n, a in got.items() if a["chosen"] == q["answer_index"]]
            row[f"p_{cond}"] = round(len(correct) / len(got), 2) if got else None
            row[f"{cond}_answers"] = {n: a["chosen"] for n, a in got.items()}
            if cond == "post":
                top = [n for n in got if levels[n] in TOP]
                bottom = [n for n in got if levels[n] not in TOP]
                if top and bottom:
                    row["discrimination"] = round(sum(n in correct for n in top) / len(top)
                                                  - sum(n in correct for n in bottom) / len(bottom), 2)
                else:
                    row["discrimination"] = None
                row["grounded"] = sum(a["grounded"] for a in got.values())
                row["quotes"] = {n: a["quote"] for n, a in got.items() if a["quote"]}
        picks = Counter()
        for cond in ("pre", "post"):
            picks.update(row[f"{cond}_answers"].values())
        row["option_picks"] = [picks.get(i, 0) for i in range(len(q["options"]))]
        row["dead_distractors"] = [i for i in range(len(q["options"])) if i != q["answer_index"] and not picks.get(i)]
        row["gain"] = (round(row["p_post"] - row["p_pre"], 2)
                       if row["p_post"] is not None and row["p_pre"] is not None else None)
        items.append(row)
    return {"cohort": COHORT, "responses": responses, "items": items, "confusions": confusions, "failures": failures}


def classroom_issues(doc: dict, cls: dict, issues: Issues) -> None:
    for it in cls["items"]:
        q = doc["quiz"][it["question_index"]]
        label = f"Q{it['question_index'] + 1}"
        if it["p_post"] is not None and it["p_post"] < 0.5:
            wrong = Counter(v for v in it["post_answers"].values() if v != it["answer_index"])
            common = wrong.most_common(1)[0][0] if wrong else None
            picked = f" Most picked option {common}: \"{q['options'][common]}\"." if common is not None else ""
            issues.add("high", "students still miss it", "quiz",
                       f"{label}: only {int(it['p_post'] * 100)}% of simulated students answer correctly after "
                       f"reading the lesson.{picked} Either the explanation does not cover it or the answer key is wrong.",
                       evidence=q["question"], suggestion="check the answer key, then strengthen the section that "
                       "teaches this", origin="simulated", question_id=q["id"])
        if it["discrimination"] is not None and it["discrimination"] < 0:
            issues.add("medium", "ambiguous question", "quiz",
                       f"{label}: weaker simulated students do better than stronger ones (discrimination "
                       f"{it['discrimination']}); stronger readers may be spotting an ambiguity",
                       evidence=q["question"], suggestion="tighten the wording so only one option is defensible",
                       origin="simulated", question_id=q["id"])
        if it["p_pre"] == 1.0 and it["p_post"] == 1.0:
            issues.add("low", "no learning signal", "quiz",
                       f"{label}: every simulated student answers correctly before reading the lesson",
                       evidence=q["question"], suggestion="make it an application question with a new scenario, so it "
                       "measures what the lesson taught", origin="simulated", question_id=q["id"])
        if len(it["dead_distractors"]) >= 2:
            dead = ", ".join(f"\"{q['options'][i]}\"" for i in it["dead_distractors"])
            issues.add("low", "dead distractors", "quiz",
                       f"{label}: nobody in the simulated classroom picked {dead}",
                       suggestion="replace them with options built on a real misconception", origin="simulated",
                       question_id=q["id"])
    by_sec: dict[str, list] = {}
    for c in cls["confusions"]:
        by_sec.setdefault(c["section_id"], []).append(c)
    for sid, cs in by_sec.items():
        sev = "medium" if len({c["student"] for c in cs}) >= 2 else "low"
        issues.add(sev, "confusing passage", sid,
                   f"{len({c['student'] for c in cs})} simulated student(s) got stuck here",
                   evidence=" / ".join(f"{c['student']} ({c['level']}): \"{c['quote'][:120]}\" - {c['why']}" for c in cs[:3]),
                   suggestion="define the term or add the missing step where they got stuck", origin="simulated")


def classroom_summary(doc: dict, cls: dict) -> str:
    lines = []
    for it in cls["items"]:
        lines.append(f"Q{it['question_index']}: correct before {it['p_pre']}, after {it['p_post']}, "
                     f"discrimination {it['discrimination']}, picks per option {it['option_picks']} "
                     f"(answer {it['answer_index']})")
    for c in cls["confusions"][:12]:
        lines.append(f"confusion in section {c['section_id']} ({c['student']}, {c['level']}): \"{c['quote'][:100]}\" - {c['why']}")
    return "\n".join(lines) or "(classroom simulation unavailable)"


def run(state: dict, doc: dict, log, terms: list[str] | None = None) -> dict:
    issues = Issues("I", "instructional")
    errors: list[str] = []
    log("measuring structure, timing and coverage")
    meas = measurements(doc, issues)
    log(f"planned time {meas['total_minutes']} min across {len(doc['sections'])} sections + quiz")

    cls = {"items": [], "confusions": [], "failures": [], "cohort": COHORT, "responses": {}}
    if doc.get("quiz"):
        log("running the simulated classroom (4 students, before and after the lesson)")
        cls = simulate(doc, log, terms)
        errors += [f"student run failed: {f}" for f in cls["failures"]]
        classroom_issues(doc, cls, issues)

    log("reviewing objective alignment and instructional quality")
    review = None
    try:
        mtext = (f"total minutes {meas['total_minutes']} (limit {config.LESSON_MINUTES}); pacing "
                 + "; ".join(f"section {i} planned {p['planned']} min, ~{p['reading']} min reading"
                             for i, p in enumerate(meas["pacing"]))
                 + f"; quiz questions per objective part {meas['quiz_per_part']}")
        r = llm.generate(prompts.render("qc_instructional_review", objective=doc["objective"],
                                        parts="\n".join(f"- {p}" for p in doc.get("objective_parts", [])),
                                        lesson=lesson_text(doc), measurements=mtext,
                                        classroom=classroom_summary(doc, cls)),
                         InstructionalReview, temperature=0.2, what="instructional review")
        review = r.model_dump()
        for it in r.issues:
            issues.add(it.severity, it.category, section_ref(doc, it.section_index), it.description,
                       evidence=it.evidence, suggestion=it.suggestion, origin="llm")
        for row in r.alignment:
            if row.coverage == "missing":
                issues.add("high", "objective not covered", None, f"\"{row.objective_part}\" is not taught, practised "
                           f"and assessed: {row.note}", suggestion="add teaching and a question for this part",
                           origin="llm")
    except Exception as e:  # noqa: BLE001
        errors.append(f"instructional review failed: {e}")
        log(f"instructional review failed: {e}", "warn")

    items = cls["items"]
    post = [i["p_post"] for i in items if i["p_post"] is not None]
    pre = [i["p_pre"] for i in items if i["p_pre"] is not None]
    rubric = review["rubric"] if review else []
    summary = {
        "total_minutes": meas["total_minutes"],
        "rubric_avg": round(sum(r["score"] for r in rubric) / len(rubric), 1) if rubric else None,
        "post_accuracy": round(sum(post) / len(post) * 100) if post else None,
        "pre_accuracy": round(sum(pre) / len(pre) * 100) if pre else None,
        "learning_gain": round((sum(post) / len(post) - sum(pre) / len(pre)) * 100) if post and pre else None,
        "coverage": Counter(r["coverage"] for r in review["alignment"]) if review else {},
        "confusions": len(cls["confusions"]),
        "issues": Counter(i["severity"] for i in issues.items),
    }
    log(f"instructional qc: rubric {summary['rubric_avg']}/5, post-lesson accuracy {summary['post_accuracy']}%, "
        f"{len(issues.items)} issues", "ok")
    return {"layer": "qc_instructional", "summary": summary, "measurements": meas, "classroom": cls,
            "review": review, "issues": issues.sorted(), "errors": errors}
