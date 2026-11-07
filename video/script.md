# redpen demo: talking-head script

## shooting setup
- landscape, 1080p or 4k, 30 or 60 fps, phone at eye level, about 1.5 arm lengths away
- face a window (light in front, never behind), quiet room, no fan
- one clip per section, 2 seconds of silence before and after, 2 takes each
- look into the lens; explain it like you would to a friend
- optional b-roll, 5-8 s each, no talking: hands typing, laptop screen close-up, walking in and sitting down
- send: google drive folder `redpen footage`, or put files in `video/raw/`
- target: footage in by ~9:30 pm (deadline 11:59 pm)

## script (~2.5 min)

**a. open** (face, punchy)
Every AI tool can write a lesson in ten seconds. The hard part is knowing if it's right. So I built one that has to prove it.

**b. who + what**
I'm Tamil Adhavan, final-year CSE at SRM. This is redpen, my submission for Kalvium's AI Research Intern task. You give it a lesson title and a learning objective. It researches, writes a 45-minute lesson, and runs two quality checks before an instructor ever sees it.

**c. research**
Research isn't one Google search. It splits the objective into parts you can actually test, then pulls from the real specification (RFC 9110 for HTTP), MDN, Wikipedia, books, YouTube transcripts, and Stack Overflow. Stack Overflow tells you what students actually get confused about. Every source gets a reliability tier, and it shows you why.

**d. the lesson**
The lesson is built for 45 minutes, and the tool checks that instead of trusting it: reading time per section, the activity, the quiz. Videos come with timestamps too, so it says "watch these three minutes", not "go watch a twenty-minute video."

**e. qc 1: facts**
QC one is facts. Most tools just ask a second AI, "is this accurate?" I didn't want that. Every claim is matched to a passage from the sources, and the checker has to quote its evidence. Then code checks that the quote actually exists in the source. If it doesn't, the verdict gets downgraded. Code examples are actually run. And for HTTP, claims get tested live: the lesson says a missing page returns 404, so it sends the request and checks.

**f. qc 2: teaching**
QC two is teaching quality. Four simulated students, from a total beginner to a strong student, take the quiz before the lesson and again after reading only the lesson. That gives real question statistics: which questions show learning, which ones everyone gets right anyway, and which wrong options nobody picks. To be honest about the limit: simulated students are an approximation, and the research says so. So this flags what a human should look at. It doesn't grade the lesson.

**g. review, fix, export**
Every finding comes with a fix. The instructor picks the ones they want, sees a before-and-after diff, and applies them. Every change is a new version; nothing is ever overwritten. And export is gated: if a serious issue is still open, you have to write down why you're exporting anyway.

**h. when things break**
If a search fails or the model runs out of quota, that step fails cleanly, everything saved stays saved, and you retry just that step.

**i. stack**
It's Python and FastAPI, Gemini for writing and reviewing, Gemini embeddings plus BM25 for search, yt-dlp for transcripts, and a plain HTML front end. Every prompt is a file in the repo, so it's versioned like code.

**j. close** (face, calm)
I built this with Claude as my coding partner, and I can walk you through every decision in it. I tested it on HTTP and on SQL joins. Thanks for watching.
