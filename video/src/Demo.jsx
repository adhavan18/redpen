import React from "react";
import { AbsoluteFill, Audio, Easing, interpolate, OffthreadVideo, Sequence, spring, staticFile, useCurrentFrame,
         useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import data from "./data.json";

const { fontFamily } = loadFont("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin"] });
const { fontFamily: mono } = loadMono("normal", { weights: ["400", "500"], subsets: ["latin"] });

export const FPS = 30;
const RED = "#ef3837", INK = "#1d1d1f", INK2 = "#6e6e73", BG = "#f5f5f7";
const H = data.http, Q = data.sql;

/* ---------------------------------------------------------------- timeline
   one entry per script section (a-j). when the talk clip exists (public/talk/<k>.mp4) the section
   lasts as long as the clip and the clip's audio runs under everything; visuals are split between
   full-frame face and screen footage (face shown as a bubble). without footage, each section is
   timed from its word count and the script is shown as subtitles. */
const SECTIONS = [
  { k: "a", text: "Every AI tool can write a lesson in ten seconds. The hard part is knowing if it's right. So I built one that has to prove it.",
    parts: [{ type: "title", share: 1, lines: [["Every", "AI", "tool", "can", "write", "a", "lesson."], ["Who", "checks", "*it?"]] }] },
  { k: "b", text: "I'm Tamil Adhavan, final-year CSE at SRM. This is redpen, my submission for Kalvium's AI Research Intern task. You give it a lesson title and a learning objective. It researches, writes a 45-minute lesson, and runs two quality checks before an instructor ever sees it.",
    parts: [{ type: "face", share: 0.3, fallback: "logo" }, { type: "screen", rec: "create", from: 0, to: 26, share: 0.7,
      chips: ["title + learning objective", "→ research → 45-min lesson → 2 QC layers"] }] },
  { k: "c", text: "Research isn't one Google search. It splits the objective into parts you can actually test, then pulls from the real specification (RFC 9110 for HTTP), MDN, Wikipedia, books, YouTube transcripts, and Stack Overflow. Stack Overflow tells you what students actually get confused about. Every source gets a reliability tier, and it shows you why.",
    parts: [{ type: "screen", rec: "create", from: 26, to: "draft", share: 0.45, badge: "live · sped up",
              chips: ["RFC 9110 · MDN · Wikipedia · books · YouTube · Stack Overflow"] },
            { type: "screen", rec: "research", share: 0.55,
              chips: [`${H.sources} sources · ${H.tierA} primary (tier A)`, `${H.transcripts}/${H.videos} videos with transcripts`, `${H.confusions} real learner confusions`] }] },
  { k: "d", text: "The lesson is built for 45 minutes, and the tool checks that instead of trusting it: reading time per section, the activity, the quiz. Videos come with timestamps too, so it says watch these three minutes, not go watch a twenty-minute video.",
    parts: [{ type: "screen", rec: "lesson", from: 0, to: 9, share: 0.5, chips: [`${H.minutes} of 45 minutes, computed not trusted`] },
            { type: "screen", rec: "lesson", from: "badge", to: null, share: 0.5, chips: ["videos cut to the minutes that teach the objective"] }] },
  { k: "e", text: "QC one is facts. Most tools just ask a second AI, is this accurate? I didn't want that. Every claim is matched to a passage from the sources, and the checker has to quote its evidence. Then code checks that the quote actually exists in the source. If it doesn't, the verdict gets downgraded. Code examples are actually run. And for HTTP, claims get tested live: the lesson says a missing page returns 404, so it sends the request and checks.",
    parts: [{ type: "face", share: 0.12, fallback: "qc1title" },
            { type: "screen", rec: "lesson", from: 9, to: "badge", share: 0.33, chips: ["every claim → a quote from its source", "quote checked by code, not by the model"] },
            { type: "stat", share: 0.15, big: `${H.quotes}/${H.claims}`, label: "evidence quotes found word-for-word in the sources" },
            { type: "screen", rec: "qc1", share: 0.4, chips: [`code examples: ${H.code[0]}/${H.code[1]} ran and matched`, `${H.probes[0]}/${H.probes[1]} claims confirmed by live HTTP requests`] }] },
  { k: "f", text: "QC two is teaching quality. Four simulated students, from a total beginner to a strong student, take the quiz before the lesson and again after reading only the lesson. That gives real question statistics: which questions show learning, which ones everyone gets right anyway, and which wrong options nobody picks. To be honest about the limit: simulated students are an approximation, and the research says so. So this flags what a human should look at. It doesn't grade the lesson.",
    parts: [{ type: "stat", share: 0.18, big: `${H.pre}% → ${H.post}%`, label: "simulated class, before → after reading the lesson" },
            { type: "screen", rec: "qc2", share: 0.62, chips: ["4 students · before and after", "learning gain · discrimination · dead distractors"] },
            { type: "note", share: 0.2, text: "Simulated students approximate difficulty, not real misconceptions (QG-SMS, arXiv 2503.05888). redpen uses them to flag questions for a human." }] },
  { k: "g", text: "Every finding comes with a fix. The instructor picks the ones they want, sees a before-and-after diff, and applies them. Every change is a new version; nothing is ever overwritten. And export is gated: if a serious issue is still open, you have to write down why you're exporting anyway.",
    parts: [{ type: "screen", rec: "fix", share: 0.45, chips: ["pick findings → see the diff → apply", "caught a wrong answer key in the SQL quiz"] },
            { type: "screen", rec: "edit", share: 0.3, chips: ["every edit is a new version"] },
            { type: "screen", rec: "export", share: 0.25, chips: ["lesson · references · both QC reports"] }] },
  { k: "h", text: "If a search fails or the model runs out of quota, that step fails cleanly, everything saved stays saved, and you retry just that step.",
    parts: [{ type: "screen", rec: "create", from: 0, to: 6, share: 0.45, chips: ["empty input → blocked"] },
            { type: "fail", share: 0.55 }] },
  { k: "i", text: "It's Python and FastAPI, Gemini for writing and reviewing, Gemini embeddings plus BM25 for search, yt-dlp for transcripts, and a plain HTML front end. Every prompt is a file in the repo, so it's versioned like code.",
    parts: [{ type: "stack", share: 1 }] },
  { k: "j", text: "I built this with Claude as my coding partner, and I can walk you through every decision in it. I tested it on HTTP and on SQL joins. Thanks for watching.",
    parts: [{ type: "face", share: 0.55, fallback: "two" }, { type: "end", share: 0.45 }] },
];

const words = (t) => t.split(/\s+/).length;
const secLen = (s, subtitles) => {
  const clip = data.talk[s.k];
  if (clip && !subtitles) return Math.round(clip * FPS);
  return Math.round((words(s.text) / 2.7 + 0.8) * FPS);
};
export const totalFrames = (subtitles) => SECTIONS.reduce((a, s) => a + secLen(s, subtitles), 0);

/* resolve a recording time: number, null (= end), or a named moment from the cursor log */
function recTime(rec, v, fallback) {
  const r = data.rec[rec];
  if (!r) return 0;
  if (v === null || v === undefined) return fallback === "end" ? r.duration - 0.8 : 0;
  if (typeof v === "number") return Math.min(v, r.duration - 0.5);
  if (v === "badge") { const e = r.events.filter((e) => e.type === "focus")[2]; return e ? e.t - 0.6 : r.duration * 0.5; }
  if (v === "draft") return Math.max(30, r.duration - 25);
  return 0;
}

/* ---------------------------------------------------------------- camera
   cursor-following zoom: every click / focus event becomes "ease in to (x, y) at zoom, hold,
   ease back out", merged into one keyframe track so consecutive targets pan instead of popping. */
function cameraTrack(events) {
  const keys = [{ t: 0, s: 1, x: 960, y: 540 }];
  const zs = events.filter((e) => e.type === "click" || e.type === "focus");
  zs.forEach((e, i) => {
    const prev = keys[keys.length - 1];
    const tin = Math.max(e.t - 0.55, prev.t + 0.05);
    keys.push({ ...prev, t: tin });
    keys.push({ t: Math.max(e.t + 0.1, tin + 0.2), s: e.zoom || 1.6, x: e.x, y: e.y });
    const holdEnd = e.t + 0.1 + (e.hold ?? 1.2);
    const next = zs[i + 1];
    if (!next || next.t - 0.55 > holdEnd + 0.8) {
      keys.push({ t: holdEnd, s: e.zoom || 1.6, x: e.x, y: e.y });
      keys.push({ t: holdEnd + 0.75, s: 1, x: 960, y: 540 });
    } else {
      keys.push({ t: Math.max(holdEnd, keys[keys.length - 1].t + 0.05) > next.t - 0.6 ? keys[keys.length - 1].t + 0.05 : holdEnd,
                  s: e.zoom || 1.6, x: e.x, y: e.y });
    }
  });
  return keys;
}
const ease = Easing.bezier(0.45, 0, 0.2, 1);
function camAt(keys, t) {
  let i = keys.length - 1;
  while (i > 0 && keys[i].t > t) i--;
  const a = keys[i], b = keys[Math.min(i + 1, keys.length - 1)];
  if (b === a || b.t <= a.t) return a;
  const k = ease(Math.min(1, Math.max(0, (t - a.t) / (b.t - a.t))));
  return { s: a.s + (b.s - a.s) * k, x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k };
}

/* ---------------------------------------------------------------- pieces */
export const Bg = ({ children }) => (
  <AbsoluteFill style={{ background: `radial-gradient(1200px 700px at 80% -10%, rgba(239,56,55,.10), transparent 60%), radial-gradient(900px 600px at 0% 110%, rgba(0,0,0,.06), transparent 60%), ${BG}`, fontFamily }}>
    {children}
  </AbsoluteFill>
);

export function Screen({ rec, from, to, frames, badge }) {
  const frame = useCurrentFrame();
  const r = data.rec[rec];
  if (!r) return <Missing name={rec} />;
  const a = recTime(rec, from), b = recTime(rec, to, "end");
  const rate = Math.max(0.25, (b - a) / (frames / FPS));
  const t = a + (frame / FPS) * rate;
  const keys = React.useMemo(() => cameraTrack(r.events), [rec]);
  const cam = camAt(keys, t);
  const s = cam.s;
  const tx = Math.min(0, Math.max(1920 - 1920 * s, 960 - cam.x * s));
  const ty = Math.min(0, Math.max(1080 - 1080 * s, 540 - cam.y * s));
  const win = interpolate(s, [1, 1.5], [0.86, 0.97], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const enter = spring({ frame, fps: FPS, config: { damping: 200 }, durationInFrames: 12 });
  return (
    <Bg>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: 1920, height: 1080, transform: `scale(${win * (0.94 + 0.06 * enter)})`, borderRadius: 26, overflow: "hidden",
                      boxShadow: "0 40px 120px rgba(0,0,0,.22), 0 0 0 1px rgba(0,0,0,.06)", background: "#fff", opacity: enter }}>
          <div style={{ width: 1920, height: 1080, transformOrigin: "0 0", transform: `translate(${tx}px, ${ty}px) scale(${s})` }}>
            <OffthreadVideo src={staticFile(`rec/${rec}.webm`)} startFrom={Math.round(a * FPS)} playbackRate={rate} muted
                            style={{ width: 1920, height: 1080 }} />
          </div>
        </div>
      </AbsoluteFill>
      {badge && rate > 1.6 && <div style={{ position: "absolute", top: 54, right: 150, padding: "10px 20px", borderRadius: 999, background: INK,
                                            color: "#fff", font: `600 26px ${fontFamily}` }}>{badge} ×{Math.round(rate)}</div>}
    </Bg>
  );
}

const Missing = ({ name }) => <Bg><AbsoluteFill style={{ alignItems: "center", justifyContent: "center", font: `600 40px ${fontFamily}`, color: INK2 }}>missing recording: {name}</AbsoluteFill></Bg>;

export function Chips({ items, frames }) {
  const frame = useCurrentFrame();
  if (!items?.length) return null;
  const per = frames / items.length;
  const i = Math.min(items.length - 1, Math.floor(frame / per));
  const local = frame - i * per;
  const inn = spring({ frame: local, fps: FPS, config: { damping: 16, stiffness: 180 } });
  const out = interpolate(local, [per - 8, per], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 64, display: "flex", justifyContent: "center" }}>
      <div style={{ padding: "18px 34px", borderRadius: 999, background: "rgba(29,29,31,.92)", color: "#fff",
                    font: `600 38px ${fontFamily}`, letterSpacing: "-0.02em", transform: `translateY(${(1 - inn) * 40}px) scale(${0.9 + 0.1 * inn})`,
                    opacity: Math.min(inn, out), boxShadow: "0 20px 60px rgba(0,0,0,.25)" }}>
        <span style={{ display: "inline-block", width: 14, height: 14, borderRadius: 7, background: RED, marginRight: 16, verticalAlign: 6 }} />
        {items[i]}
      </div>
    </div>
  );
}

export function Title({ lines, frames }) {
  const frame = useCurrentFrame();
  let n = 0;
  return (
    <Bg>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 10 }}>
        {lines.map((ln, li) => (
          <div key={li} style={{ display: "flex", gap: 26, font: `800 ${li === 0 ? 104 : 150}px ${fontFamily}`, letterSpacing: "-0.05em",
                                 color: INK }}>
            {ln.map((w) => {
              const d = (n++) * 3 + (li ? 14 : 0);
              const p = spring({ frame: frame - d, fps: FPS, config: { damping: 14, stiffness: 160 } });
              const red = w.startsWith("*");
              return <span key={w + d} style={{ display: "inline-block", transform: `translateY(${(1 - p) * 60}px)`, opacity: p,
                                               color: red ? RED : INK }}>{red ? w.slice(1) : w}</span>;
            })}
          </div>
        ))}
      </AbsoluteFill>
    </Bg>
  );
}

export function Logo({ frames, sub }) {
  const frame = useCurrentFrame();
  const p = spring({ frame, fps: FPS, config: { damping: 13 } });
  const dot = spring({ frame: frame - 6, fps: FPS, config: { damping: 8, stiffness: 120 } });
  return (
    <Bg>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 28, transform: `scale(${0.8 + 0.2 * p})`, opacity: p }}>
          <div style={{ width: 64, height: 64, borderRadius: 32, background: RED, transform: `scale(${dot})` }} />
          <div style={{ font: `800 190px ${fontFamily}`, letterSpacing: "-0.06em", color: INK }}>redpen</div>
        </div>
        <div style={{ font: `500 44px ${fontFamily}`, color: INK2, marginTop: 10, opacity: interpolate(frame, [12, 24], [0, 1], { extrapolateRight: "clamp" }) }}>
          {sub || "lessons that show their receipts."}
        </div>
      </AbsoluteFill>
    </Bg>
  );
}

export function Stat({ big, label }) {
  const frame = useCurrentFrame();
  const p = spring({ frame, fps: FPS, config: { damping: 15, stiffness: 140 } });
  // count up any numbers in the headline
  const k = interpolate(frame, [0, 22], [0, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const shown = big.replace(/\d+/g, (m) => String(Math.round(+m * k)));
  return (
    <Bg>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
        <div style={{ font: `800 230px ${fontFamily}`, letterSpacing: "-0.06em", color: RED, transform: `scale(${0.85 + 0.15 * p})`, fontVariantNumeric: "tabular-nums" }}>{shown}</div>
        <div style={{ font: `600 50px ${fontFamily}`, color: INK, letterSpacing: "-0.02em", opacity: p, maxWidth: 1400, textAlign: "center" }}>{label}</div>
      </AbsoluteFill>
    </Bg>
  );
}

export function Note({ text }) {
  const frame = useCurrentFrame();
  const p = spring({ frame, fps: FPS, config: { damping: 200 } });
  return (
    <Bg>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: 200 }}>
        <div style={{ font: `600 30px ${fontFamily}`, color: RED, letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 24, opacity: p }}>being honest</div>
        <div style={{ font: `600 64px ${fontFamily}`, color: INK, letterSpacing: "-0.03em", lineHeight: 1.18, textAlign: "center", opacity: p,
                      transform: `translateY(${(1 - p) * 30}px)` }}>{text}</div>
      </AbsoluteFill>
    </Bg>
  );
}

function Fail() {
  const frame = useCurrentFrame();
  const steps = [["research", "done"], ["draft", "done"], ["qc 1 · facts", frame < 40 ? "failed: model quota" : frame < 70 ? "retrying…" : "done"], ["qc 2 · teaching", "done"]];
  return (
    <Bg>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 40 }}>
        <div style={{ display: "flex", gap: 22 }}>
          {steps.map(([t, s], i) => {
            const failed = s.startsWith("failed"), retry = s.startsWith("retry");
            const p = spring({ frame: frame - i * 4, fps: FPS, config: { damping: 15 } });
            return <div key={t} style={{ width: 330, padding: "26px 28px", borderRadius: 22, background: "#fff", transform: `translateY(${(1 - p) * 40}px)`, opacity: p,
                                          boxShadow: failed ? `inset 0 0 0 3px ${RED}` : "0 10px 30px rgba(0,0,0,.06)" }}>
              <div style={{ font: `600 22px ${fontFamily}`, color: "#a1a1a6" }}>0{i + 1}</div>
              <div style={{ font: `700 36px ${fontFamily}`, color: INK, letterSpacing: "-0.02em" }}>{t}</div>
              <div style={{ font: `600 26px ${fontFamily}`, color: failed ? RED : retry ? "#a35a00" : "#1f8a4c", marginTop: 6 }}>{s}</div>
            </div>;
          })}
        </div>
        <div style={{ font: `600 44px ${fontFamily}`, color: INK2, letterSpacing: "-0.02em" }}>saved work stays saved · retry only the step that failed</div>
        <div style={{ font: `500 24px ${fontFamily}`, color: "#a1a1a6" }}>illustration of the retry flow</div>
      </AbsoluteFill>
    </Bg>
  );
}

export function Stack({ active = -1, beatFrames = 0 }) {
  const frame = useCurrentFrame();
  const push = beatFrames ? interpolate(frame, [0, beatFrames], [1, 1.07], { extrapolateRight: "clamp" }) : 1;
  const items = [["Python + FastAPI", "pipeline, api"], ["Gemini 3.5 Flash", "writing + review, structured JSON"], ["Gemini embeddings + BM25", "retrieval"],
                 ["yt-dlp + transcripts", "video segments"], ["trafilatura", "page text"], ["DuckDuckGo · Wikipedia · Google Books · Stack Exchange", "sources"],
                 ["plain HTML / CSS / JS", "no build step"], ["prompts/*.md", "versioned with the code"], ["pytest", "21 tests, no API key needed"]];
  return (
    <Bg>
      <AbsoluteFill style={{ padding: "70px 150px 0 150px", transform: `scale(${push})`, transformOrigin: "50% 30%" }}>
        <div style={{ font: `800 80px ${fontFamily}`, letterSpacing: "-0.05em", color: INK, marginBottom: 32 }}>The stack<span style={{ color: RED }}>.</span></div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 22 }}>
          {items.map(([t, s], i) => {
            const p = spring({ frame: frame - i * 4, fps: FPS, config: { damping: 15 } });
            const on = i === active, dim = active >= 0 && !on;
            return <div key={t} style={{ background: "#fff", borderRadius: 22, padding: "26px 30px",
                                          transform: `translateY(${(1 - p) * 50}px) scale(${(0.95 + 0.05 * p) * (on ? 1.05 : 1)})`,
                                          opacity: p * (dim ? 0.5 : 1), transition: "none",
                                          boxShadow: on ? `0 0 0 4px ${RED}, 0 24px 60px rgba(239,56,55,.25)` : "0 10px 30px rgba(0,0,0,.05)" }}>
              <div style={{ font: `700 34px ${fontFamily}`, color: on ? RED : INK, letterSpacing: "-0.02em" }}>{t}</div>
              <div style={{ font: `500 25px ${fontFamily}`, color: INK2, marginTop: 6 }}>{s}</div>
            </div>;
          })}
        </div>
      </AbsoluteFill>
    </Bg>
  );
}

export function End() {
  const frame = useCurrentFrame();
  const p = spring({ frame, fps: FPS, config: { damping: 15 } });
  return (
    <Bg>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 18 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 22, opacity: p, transform: `scale(${0.9 + 0.1 * p})` }}>
          <div style={{ width: 48, height: 48, borderRadius: 24, background: RED }} />
          <div style={{ font: `800 140px ${fontFamily}`, letterSpacing: "-0.06em", color: INK }}>redpen</div>
        </div>
        <div style={{ font: `500 44px ${mono}`, color: INK, opacity: p }}>github.com/adhavan18/redpen</div>
        <div style={{ font: `500 34px ${fontFamily}`, color: INK2, marginTop: 20, opacity: interpolate(frame, [10, 22], [0, 1], { extrapolateRight: "clamp" }) }}>
          Tamil Adhavan S K · SRM IST · Kalvium AI Research Intern task
        </div>
        <div style={{ font: `500 26px ${fontFamily}`, color: "#a1a1a6", marginTop: 8, opacity: interpolate(frame, [16, 28], [0, 1], { extrapolateRight: "clamp" }) }}>
          tested on: HTTP Requests and Responses · SQL Joins
        </div>
      </AbsoluteFill>
    </Bg>
  );
}

function Face({ k, offset, frames, fallback }) {
  if (!data.talk[k]) {
    if (fallback === "logo") return <Logo frames={frames} />;
    if (fallback === "qc1title") return <Title frames={frames} lines={[["QC", "1"], ["*Facts."]]} />;
    if (fallback === "two") return <Title frames={frames} lines={[["Built", "with", "Claude."], ["*Explained", "by", "me."]]} />;
    return <Logo frames={frames} />;
  }
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <OffthreadVideo src={staticFile(`talk/${k}.mp4`)} startFrom={offset} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    </AbsoluteFill>
  );
}

function Bubble({ k, offset }) {
  const frame = useCurrentFrame();
  if (!data.talk[k]) return null;
  const p = spring({ frame, fps: FPS, config: { damping: 14 } });
  return (
    <div style={{ position: "absolute", left: 60, bottom: 60, width: 300, height: 300, borderRadius: 150, overflow: "hidden",
                  border: "6px solid #fff", boxShadow: "0 20px 60px rgba(0,0,0,.3)", transform: `scale(${p})` }}>
      <OffthreadVideo src={staticFile(`talk/${k}.mp4`)} startFrom={offset} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    </div>
  );
}

function Subtitle({ text, frames }) {
  const frame = useCurrentFrame();
  // chunk the script into ~9-word lines, evenly over the section
  const w = text.split(/\s+/), chunks = [];
  for (let i = 0; i < w.length; i += 9) chunks.push(w.slice(i, i + 9).join(" "));
  const i = Math.min(chunks.length - 1, Math.floor((frame / frames) * chunks.length));
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 40, display: "flex", justifyContent: "center" }}>
      <div style={{ maxWidth: 1500, padding: "12px 26px", borderRadius: 14, background: "rgba(255,255,255,.92)", color: INK,
                    font: `600 34px ${fontFamily}`, textAlign: "center", boxShadow: "0 8px 30px rgba(0,0,0,.08)" }}>{chunks[i]}</div>
    </div>
  );
}

/* a hard cut with a quick punch-in, the "recordly" feel */
export function Punch({ children }) {
  const frame = useCurrentFrame();
  const s = interpolate(frame, [0, 7], [1.05, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const o = interpolate(frame, [0, 3], [0.4, 1], { extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ transform: `scale(${s})`, opacity: o }}>{children}</AbsoluteFill>;
}

function Part({ sec, part, frames, offset }) {
  const hasTalk = !!data.talk[sec.k];
  switch (part.type) {
    case "title": return <Title lines={part.lines} frames={frames} />;
    case "face": return <Face k={sec.k} offset={offset} frames={frames} fallback={part.fallback} />;
    case "screen": return <><Screen rec={part.rec} from={part.from} to={part.to} frames={frames} badge={part.badge} />
                            <Chips items={part.chips} frames={frames} />{hasTalk && <Bubble k={sec.k} offset={offset} />}</>;
    case "stat": return <><Stat big={part.big} label={part.label} />{hasTalk && <Bubble k={sec.k} offset={offset} />}</>;
    case "note": return <><Note text={part.text} />{hasTalk && <Bubble k={sec.k} offset={offset} />}</>;
    case "fail": return <><Fail />{hasTalk && <Bubble k={sec.k} offset={offset} />}</>;
    case "stack": return <><Stack />{hasTalk && <Bubble k={sec.k} offset={offset} />}</>;
    case "end": return <End />;
    default: return null;
  }
}

export const Demo = ({ subtitles }) => {
  let at = 0;
  return (
    <AbsoluteFill style={{ background: BG, fontFamily }}>
      {SECTIONS.map((sec) => {
        const len = secLen(sec, subtitles);
        const start = at; at += len;
        let p = 0;
        const total = sec.parts.reduce((a, x) => a + x.share, 0);
        return (
          <Sequence key={sec.k} from={start} durationInFrames={len} name={`section ${sec.k}`}>
            {data.talk[sec.k] && !subtitles && <Audio src={staticFile(`talk/${sec.k}.mp4`)} />}
            {sec.parts.map((part, i) => {
              const plen = i === sec.parts.length - 1 ? len - p : Math.round((part.share / total) * len);
              const pstart = p; p += plen;
              return (
                <Sequence key={i} from={pstart} durationInFrames={plen} name={`${sec.k}.${i} ${part.type}`}>
                  <Punch><Part sec={sec} part={part} frames={plen} offset={pstart} /></Punch>
                </Sequence>
              );
            })}
            {(subtitles || !data.talk[sec.k]) && <Subtitle text={sec.text} frames={len} />}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
