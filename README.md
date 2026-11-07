# redpen

a lesson creation tool that shows its receipts.

give it a lesson title and a learning objective. it researches the topic (web, specs, wikipedia, books, stack overflow, youtube transcripts), writes a 45-minute lesson, and then checks it with two independent qc layers that produce evidence, not just scores.

built for the kalvium ai research intern task.

## what makes it different

most lesson generators ask a second llm "is this accurate? 1-10". redpen tries to check things the way a careful reviewer would:

**qc 1: research and facts**
- every factual sentence is extracted and checked against the research passages it came from
- the verifier has to quote its evidence, and code checks that the quote actually exists in the source. if it does not, the verdict is downgraded
- python and javascript examples in the lesson are executed and their real output is compared with what the lesson says they print
- claims about http behaviour are tested live against public test servers (jsonplaceholder, httpbin), never against `/status/{code}` which proves nothing
- second opinion on doubtful claims from gemini with google search grounding
- source tiers (primary spec / reputable / unknown) with the reason shown, citation coverage per section, copied-text detection (12+ word overlap)

**qc 2: instructional quality**
- a simulated classroom: four student profiles take the quiz before reading and again after reading only the lesson. per question you get difficulty, learning gain, discrimination (do stronger students do better?) and distractors nobody picks
- the 45-minute budget is computed, not trusted: section minutes vs reading time at 180 wpm, plus in-lesson video clips
- objective alignment matrix (taught / practised / assessed per objective part) and an 8-criterion rubric
- every objective part must have a quiz question; missing ones are flagged

**research**
- the objective is split into assessable parts, each part drives retrieval
- long specs like rfc 9110 are kept whole, then cut to their most relevant passages with bm25 before embedding
- youtube transcripts are embedded so the lesson can say "watch 2:14-5:40", not "watch this 20 minute video"
- real learner confusion is pulled from stack overflow and used for the misconceptions section and quiz distractors

**workflow**
- steps run in order (research → draft → qc 1 + qc 2 in parallel → review → export), each step's output is saved before the next starts
- any failed step can be retried on its own; partial research failures are recorded, not fatal
- every save, generation and applied fix is a new version; nothing is overwritten, old versions can be restored
- unsaved edits survive a page refresh; two tabs editing the same lesson get a conflict, not a silent overwrite
- qc findings can be applied as proposed fixes (shown as a diff, accepted per section) or dismissed with a reason
- export is gated: both qc layers must have checked the current version with no open high-severity finding, or you write an override reason into the manifest

## run it

needs python 3.11+ and a free gemini api key from https://aistudio.google.com/apikey

```bash
python -m venv .venv
.venv\Scripts\activate          # mac/linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # mac/linux: cp .env.example .env
```

put your key in `.env`, then:

```bash
python -m uvicorn redpen.main:app --port 8000
```

open http://localhost:8000

tests (no api key needed):

```bash
python -m pytest -q
```

## stack

- python, fastapi, plain html/css/js (no build step)
- gemini 3.5 flash for generation and review (structured json output), gemini embeddings for retrieval, google search grounding for the second opinion. falls back to other gemini models on quota errors
- duckduckgo search (tavily optional), wikipedia api, google books + open library, stack exchange api, yt-dlp + youtube-transcript-api, trafilatura for page text
- bm25 + dense retrieval, numpy
- files on disk for storage (`data/lessons/<id>/`), atomic writes

## layout

```
redpen/
  research/     search, fetch, reliability tiers, chunking, retrieval, youtube
  qc/           factual.py (qc 1), instructional.py (qc 2), execute.py, probes.py
  generate.py   evidence pack -> lesson
  fixes.py      qc findings -> proposed edits
  pipeline.py   step ordering, retries, background runs
  storage.py    versions, state, atomic json
  export.py     zip: lesson md/html/json, references, both qc reports, manifest
prompts/        every prompt as a markdown file, versioned with the code
static/         the ui
tests/
samples/        exported packages from the two test lessons
```

## limits, honestly

- simulated students are llms role-playing. research (qg-sms, arxiv 2503.05888; koff et al., ceur-ws vol-4287) shows this approximates item difficulty but misses how real students go wrong. redpen uses it to rank questions worth a human look, not to grade the lesson
- a claim marked "unsupported" may still be true; it means the research did not back it. the google-grounded check helps tell those apart
- code execution is a guard (temp dir, timeout, isolated interpreter, deny-list), not a sandbox. run it on your own machine for your own lessons
- book sources are metadata and descriptions only; full book text is not available
- youtube transcripts are not always available; videos without one can only be linked whole

## acknowledgements

built with help from claude (anthropic) for research, code and debugging. all design decisions are explained in the code comments and i can walk through any of it. external libraries and apis are listed above; no code was copied from other projects.
