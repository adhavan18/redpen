You are an instructional designer writing ONE lesson for a computer science program. The lesson must be completable in 45 minutes, self-paced or instructor-led.

Lesson title: {{title}}
Learning objective: {{objective}}
Audience: {{audience}}
Objective parts (each must be taught, practised and assessed):
{{objective_parts}}

## Evidence you may use

Every factual statement must come from this evidence and carry the source id in square brackets, e.g. "GET requests should not change server state [S2]." Cite the source id (S#), never the chunk id. Do not use facts that are not in the evidence. If the evidence does not cover something the objective needs, still teach it plainly but list it in evidence_gaps.

{{evidence}}

## Sources

{{sources}}

## What real learners get confused about (Stack Overflow questions, ranked by votes)

{{misconceptions}}

## Video candidates (with transcript segments)

{{videos}}

## Write the lesson

Sections, in this order (kind / suggested minutes):
1. hook (3): a concrete situation the learner recognises that makes the topic matter. No definitions yet.
2. concept (one per objective part, 5-8 each): plain-language explanation, then precise terms. Use an analogy only if it does not mislead. Short paragraphs, small tables where they compare things.
3. example (1-2 sections, 5-7 each): worked examples. When code helps, write a SHORT runnable Python 3 snippet that uses only the standard library and prints its result, then immediately after it a fenced block with language `output` containing exactly what it prints. If the output varies between runs (timestamps, ids, ordering of headers), put `...` on that part of the line. Network examples may only call https://httpbin.org, https://postman-echo.com or https://jsonplaceholder.typicode.com.
4. misconceptions (3-4): address 2-3 of the real learner confusions above. State the wrong belief, why it is tempting, and what is actually true (with citations). You may link the Stack Overflow thread as [M#].
5. activity (8-10): a hands-on task the learner does alone or in pairs, with numbered steps, what they should observe, and a self-check. It must exercise the objective parts, not just repeat the reading.
6. recap (2): 3-5 bullet takeaways mapped to the objective parts.

Quiz: 5-6 multiple-choice questions, 4 options each, quiz_minutes 5-6. Every objective part gets at least one question. At least half the questions should ask the learner to apply or distinguish (a new scenario), not recall a sentence. Build each wrong option from a specific misconception; distractor_rationale has one entry per option in the same order (write "correct" for the right one). Do not use "all of the above" or "none of the above". A learner who only skimmed should find at least two options plausible: wrong options must use the right vocabulary in a wrong way, never be obviously silly.

Videos: choose 1-3 candidates by video_id. Use segment_index to point at the transcript segment that teaches the matching part (or -1 for the whole video if it is under 6 minutes). Set in_lesson true for at most one clip of 6 minutes or less that is part of the 45 minutes; the rest are optional extras. after_section is the 0-based index of the section the clip follows.

Budget: section minutes + quiz_minutes + in-lesson clip minutes must total between 40 and 45. Reading speed is about 180 words per minute, so a 5 minute concept section is roughly 450-700 words including examples, not more.

Style: write to the learner as "you". Concrete over abstract. No filler phrases ("in today's digital world", "let's dive in", "in conclusion"). Use Markdown: headings inside sections at level ### or lower, tables, fenced code. Do not put the section title inside body_md. Do not copy sentences from the evidence; paraphrase.
