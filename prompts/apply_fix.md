You are revising one section of a lesson to resolve review findings. Change only what the findings require; keep everything else (structure, tone, citations, code that already works) as it is.

Lesson: {{title}}
Objective: {{objective}}
Section: "{{section_title}}" ({{section_kind}}, {{minutes}} minutes)

Current section text (Markdown):
<<<
{{body}}
>>>

Findings to resolve:
{{issues}}

Research evidence you may cite (use the S id in square brackets):
{{evidence}}

Rules:
- Every factual sentence you add or change must cite an S id from the evidence above. Do not invent sources.
- If a code example's output was wrong, fix the output block to match the real output shown in the finding, or fix the code.
- Keep roughly the same length unless a finding is about length or pacing.
- body_md is the complete new section text, not a diff, and without the section title.
- change_summary: one line per finding, saying what you changed.
