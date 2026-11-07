import React from "react";
import { AbsoluteFill, Audio, Easing, interpolate, OffthreadVideo, Sequence, spring, staticFile, useCurrentFrame } from "remotion";
import { loadFont } from "@remotion/google-fonts/Inter";
import transcript from "./transcript.json";
import data from "./data.json";
import { SECTIONS, FIX_AT, FIX_WORD } from "./edl";
import { Bg, End, Logo, Note, Screen, Stack, Stat, Title } from "./Demo";

const { fontFamily } = loadFont("normal", { weights: ["500", "600", "700", "800"], subsets: ["latin"] });
export const FPS = 30;
const RED = "#ef3837", INK = "#1d1d1f";
const PAD_IN = 0.08, PAD_OUT = 0.16, MORPH = 0.38;
// the orange-room takes came off the front camera mirrored (the poster reads backwards); flip them back
const MIRRORED = new Set(["c10", "c11", "c12", "c13", "c14", "c15", "c16", "c17", "c18", "c19", "c20", "c21", "c22"]);

/* ---------- build the timeline from the edl ---------- */
const strip = (w) => w.replace(/[^\w'%-]/g, "");

function resolveCut([clip, a, b]) {
  const words = transcript[clip].words;
  const i0 = a === null ? 0 : words.findIndex((w) => Math.abs(w.s - a) < 0.011);
  const i1 = b === null ? words.length - 1 : words.findIndex((w) => Math.abs(w.s - b) < 0.011);
  if (i0 < 0 || i1 < 0) throw new Error(`edl: no word at ${clip} ${a}/${b}`);
  const prevEnd = i0 > 0 ? words[i0 - 1].e : 0;
  const nextStart = i1 < words.length - 1 ? words[i1 + 1].s : transcript[clip].duration;
  const tin = Math.max(prevEnd + 0.02, words[i0].s - PAD_IN, 0);
  const tout = Math.min(nextStart - 0.02, words[i1].e + PAD_OUT, transcript[clip].duration);
  return { clip, tin, tout, words: words.slice(i0, i1 + 1) };
}

export const TIMELINE = (() => {
  let at = 0;
  return SECTIONS.map((sec) => {
    let t = 0;
    const segs = [], words = [];
    for (const c of sec.cuts || []) {
      const r = resolveCut(c);
      segs.push({ ...r, start: t });
      for (const w of r.words) {
        const key = `${r.clip}@${w.s}`;
        let text = key in FIX_AT ? FIX_AT[key] : (FIX_WORD[strip(w.w).toLowerCase()] ?? w.w);
        if (text === "") continue;
        if (text.startsWith("-") && words.length) { words[words.length - 1].text += text; continue; }
        words.push({ text, raw: strip(w.w), s: t + (w.s - r.tin), e: t + (w.e - r.tin) });
      }
      t += r.tout - r.tin;
    }
    const dur = sec.silent ?? t;
    const anchor = (b) => {
      if (typeof b.at === "number") return b.at;
      const hits = words.filter((w) => w.raw === strip(b.at));
      const w = hits[b.n ?? 0];
      if (!w) throw new Error(`edl: anchor "${b.at}" not spoken in ${sec.k}`);
      return Math.max(0, w.s - 0.12);
    };
    const beats = sec.beats.map((b) => ({ ...b, t: anchor(b) })).sort((x, y) => x.t - y.t);
    for (const b of beats) {
      if (!b.marks) continue;
      b.markTimes = b.marks.map(([word, idx]) => {
        const w = words.find((x) => x.s >= b.t - 0.2 && (strip(x.text) === strip(word) || x.raw === strip(word)));
        return [w ? w.s - b.t : 0, idx];
      });
    }
    beats.forEach((b, i) => (b.end = i + 1 < beats.length ? beats[i + 1].t : dur));
    const out = { ...sec, segs, words, dur, beats, start: at };
    at += dur;
    return out;
  });
})();
export const totalLaunchFrames = Math.ceil(TIMELINE.reduce((a, s) => a + s.dur, 0) * FPS);

/* ---------- face: one track per section, morphing between full card and corner bubble ---------- */
const RECTS = {
  full: { x: 160, y: 90, w: 1600, h: 900, r: 34 },
  bubble: { x: 64, y: 1080 - 64 - 290, w: 290, h: 290, r: 145 },
};
const faceMode = (type) => (type === "face" ? "full" : ["screen", "stat", "note", "stack", "proof"].includes(type) ? "bubble" : "hidden");

function FaceTrack({ sec }) {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const i = sec.beats.findIndex((b) => t >= b.t && t < b.end);
  const cur = sec.beats[Math.max(0, i)], prev = sec.beats[Math.max(0, i - 1)];
  const k = Easing.bezier(0.45, 0, 0.2, 1)(Math.min(1, Math.max(0, (t - cur.t) / MORPH)));
  const from = i > 0 ? faceMode(prev.type) : faceMode(cur.type), to = faceMode(cur.type);
  const rect = (m) => RECTS[m === "hidden" ? "bubble" : m];
  const A = rect(from), B = rect(to);
  const mix = (p) => A[p] + (B[p] - A[p]) * k;
  const opA = from === "hidden" ? 0 : 1, opB = to === "hidden" ? 0 : 1;
  const opacity = opA + (opB - opA) * k;
  if (opacity <= 0.01) return null;
  const full = to === "full" && k > 0.5;
  return (
    <div style={{ position: "absolute", left: mix("x"), top: mix("y"), width: mix("w"), height: mix("h"), borderRadius: mix("r"),
                  overflow: "hidden", opacity, background: "#000",
                  boxShadow: full ? "0 40px 120px rgba(0,0,0,.25)" : "0 18px 50px rgba(0,0,0,.35), 0 0 0 5px #fff" }}>
      {sec.segs.map((s, j) => (
        <Sequence key={j} from={Math.round(s.start * FPS)} durationInFrames={Math.round((s.tout - s.tin) * FPS) + 1} layout="none">
          {/* alternate a slight punch-in on every cut, so jump cuts read as edits, not glitches */}
          <div style={{ width: "100%", height: "100%", transform: `scale(${(MIRRORED.has(s.clip) ? -1 : 1) * (j % 2 ? 1.12 : 1.0)}, ${j % 2 ? 1.12 : 1.0})` }}>
            <OffthreadVideo src={staticFile(`clips/${s.clip}.mp4`)} startFrom={Math.round(s.tin * FPS)} muted
                            style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </div>
        </Sequence>
      ))}
    </div>
  );
}

function Voice({ sec }) {
  return sec.segs.map((s, j) => {
    const n = Math.round((s.tout - s.tin) * FPS);
    return (
      <Sequence key={j} from={Math.round(s.start * FPS)} durationInFrames={n} layout="none">
        <Audio src={staticFile(`clips/${s.clip}.mp4`)} startFrom={Math.round(s.tin * FPS)}
               volume={(f) => interpolate(f, [0, 2, n - 3, n], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      </Sequence>
    );
  });
}

/* ---------- captions: short phrases, the spoken word lights up ---------- */
function phrases(words) {
  const out = []; let cur = [];
  for (const w of words) {
    cur.push(w);
    if (cur.length >= 5 || /[.,?!]$/.test(w.text) && cur.length >= 2) { out.push(cur); cur = []; }
  }
  if (cur.length) out.push(cur);
  return out.map((p) => ({ words: p, s: p[0].s, e: p[p.length - 1].e }));
}
function Captions({ sec }) {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const ps = React.useMemo(() => phrases(sec.words), [sec.k]);
  const p = ps.find((x, i) => t >= x.s - 0.05 && t < (ps[i + 1] ? ps[i + 1].s - 0.05 : x.e + 0.5));
  if (!p) return null;
  const beat = sec.beats.find((b) => t >= b.t && t < b.end);
  const onFace = beat?.type === "face";
  const inn = interpolate(t - (p.s - 0.05), [0, 0.12], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: onFace ? 130 : 60, display: "flex", justifyContent: "center", pointerEvents: "none" }}>
      <div style={{ padding: "12px 26px", borderRadius: 18, background: onFace ? "rgba(0,0,0,.42)" : "rgba(29,29,31,.88)",
                    font: `700 46px ${fontFamily}`, letterSpacing: "-0.02em", color: "#fff", opacity: inn,
                    transform: `translateY(${(1 - inn) * 10}px)`, maxWidth: 1500, textAlign: "center" }}>
        {p.words.map((w, i) => {
          const on = t >= w.s - 0.03 && t <= w.e + 0.08;
          return <span key={i} style={{ color: on ? RED : "#fff", marginRight: 14 }}>{w.text}</span>;
        })}
      </div>
    </div>
  );
}

/* ---------- beats ---------- */
function Label({ text, big }) {
  const frame = useCurrentFrame();
  const p = spring({ frame: frame - 4, fps: FPS, config: { damping: 16, stiffness: 170 } });
  if (big) {
    return (
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 70, display: "flex", justifyContent: "center" }}>
        <div style={{ padding: "20px 38px", borderRadius: 999, background: RED, color: "#fff", font: `800 52px ${fontFamily}`,
                      letterSpacing: "-0.03em", transform: `translateY(${(1 - p) * 50}px) scale(${0.9 + 0.1 * p})`, opacity: p,
                      boxShadow: "0 24px 70px rgba(239,56,55,.35)" }}>{text}</div>
      </div>
    );
  }
  return (
    <div style={{ position: "absolute", top: 46, left: 70, padding: "10px 20px", borderRadius: 999, background: "rgba(255,255,255,.95)",
                  font: `700 26px ${fontFamily}`, color: INK, letterSpacing: "-0.01em", boxShadow: "0 10px 30px rgba(0,0,0,.12)",
                  transform: `translateX(${(1 - p) * -30}px)`, opacity: p, display: "flex", alignItems: "center", gap: 12 }}>
      <span style={{ width: 12, height: 12, borderRadius: 6, background: RED }} />{text}
    </div>
  );
}

function Proof() {
  const frame = useCurrentFrame();
  const L = [data.http, data.sql];
  return (
    <Bg>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 40, flexDirection: "row" }}>
        {L.map((l, i) => {
          const p = spring({ frame: frame - i * 6, fps: FPS, config: { damping: 15 } });
          const rows = [[`${l.accuracy}%`, "claim accuracy"], [`${l.quotes}/${l.claims}`, "quotes verified"], [`${l.code[0]}/${l.code[1]}`, "code ran + matched"],
                        [`${l.issues}`, "findings raised for review"]];
          return (
            <div key={l.title} style={{ width: 640, background: "#fff", borderRadius: 30, padding: "40px 46px", boxShadow: "0 20px 60px rgba(0,0,0,.08)",
                                         transform: `translateY(${(1 - p) * 60}px)`, opacity: p }}>
              <div style={{ font: `600 24px ${fontFamily}`, color: RED, letterSpacing: ".1em", textTransform: "uppercase" }}>tested on</div>
              <div style={{ font: `800 54px ${fontFamily}`, color: INK, letterSpacing: "-0.04em", margin: "6px 0 26px" }}>{l.title}</div>
              {rows.map(([v, k]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "12px 0", borderTop: "1px solid rgba(0,0,0,.08)" }}>
                  <span style={{ font: `500 30px ${fontFamily}`, color: "#6e6e73" }}>{k}</span>
                  <span style={{ font: `700 32px ${fontFamily}`, color: INK }}>{v}</span>
                </div>
              ))}
            </div>
          );
        })}
      </AbsoluteFill>
    </Bg>
  );
}

function StackLive({ b, frames }) {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  let active = -1;
  for (const [mt, idx] of b.markTimes || []) if (t >= mt - 0.1) active = idx;
  return <Stack active={active} beatFrames={frames} />;
}

function Beat({ b, frames }) {
  switch (b.type) {
    case "face": return <Bg />;
    case "kinetic": return <Title lines={b.lines} frames={frames} />;
    case "logo": return <Logo frames={frames} />;
    case "stat": return <Stat big={b.big} label={b.label} />;
    case "note": return <Note text={b.text} />;
    case "stack": return <StackLive b={b} frames={frames} />;
    case "proof": return <Proof />;
    case "end": return <End />;
    case "screen": {
      const r = data.rec[b.rec];
      const dur = frames / FPS;
      const rate = b.rate ?? 1;
      const from = Math.max(0, Math.min(b.from, r.duration - 0.3 - dur * rate));
      return (
        <>
          <Screen rec={b.rec} from={from} to={from + dur * rate} frames={frames} badge={b.badge ? "live · sped up" : null} />
          {(b.label || b.big) && <Label text={b.label || b.big} big={!!b.big} />}
        </>
      );
    }
    default: return null;
  }
}

/* a white flash-free "punch" on every beat change: fast scale settle, the recordly feel */
function Punch({ children }) {
  const frame = useCurrentFrame();
  const s = interpolate(frame, [0, 8], [1.045, 1], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const o = interpolate(frame, [0, 3], [0.55, 1], { extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ transform: `scale(${s})`, opacity: o }}>{children}</AbsoluteFill>;
}


/* music bed: generated (music.mjs), ducked under the voice, lifted for title cards and the silent qc 1 sequence */
const SPEECH = TIMELINE.flatMap((sec) => sec.words.map((w) => [sec.start + w.s, sec.start + w.e]));
function speakingNear(t) {
  for (const [a, b] of SPEECH) if (t >= a - 0.35 && t <= b + 0.35) return true;
  return false;
}
const DUCK = (() => { // per-frame volume, smoothed
  const out = new Float32Array(totalLaunchFrames);
  let v = 0.2;
  for (let f = 0; f < totalLaunchFrames; f++) {
    const target = speakingNear(f / FPS) ? 0.07 : 0.5;
    v += (target - v) * 0.08;
    out[f] = v;
  }
  return out;
})();
function Music() {
  return <Audio src={staticFile("music.wav")} volume={(f) => DUCK[Math.min(f, DUCK.length - 1)]} />;
}

export const Launch = () => (
  <AbsoluteFill style={{ background: "#f5f5f7", fontFamily }}>
    <Music />
    {TIMELINE.map((sec) => (
      <Sequence key={sec.k} from={Math.round(sec.start * FPS)} durationInFrames={Math.round(sec.dur * FPS)} name={sec.k}>
        {sec.beats.map((b, i) => {
          const f0 = Math.round(b.t * FPS), n = Math.max(1, Math.round((b.end - b.t) * FPS));
          return (
            <Sequence key={i} from={f0} durationInFrames={n} name={`${sec.k}:${b.type}${b.rec ? " " + b.rec : ""}`}>
              <Punch><Beat b={b} frames={n} /></Punch>
            </Sequence>
          );
        })}
        {sec.segs.length > 0 && <FaceTrack sec={sec} />}
        {sec.segs.length > 0 && <Voice sec={sec} />}
        {sec.words.length > 0 && <Captions sec={sec} />}
      </Sequence>
    ))}
  </AbsoluteFill>
);
