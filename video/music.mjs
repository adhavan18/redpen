// generates a quiet, royalty-free music bed: slow sine-pad chords with a soft 8th-note pulse.
// usage: node music.mjs <seconds>  -> public/music.wav
import fs from "node:fs";

const SR = 44100, secs = Number(process.argv[2] || 200), N = Math.ceil(SR * secs);
const BPM = 96, beat = 60 / BPM, bar = beat * 4, chordLen = bar * 2;
const n = (m) => 440 * Math.pow(2, (m - 69) / 12);
// a minor, f major 7, c major 7, g 6 (add9 colours), voiced low and close
const CHORDS = [[45, 57, 60, 64, 71], [41, 53, 57, 60, 64], [48, 55, 59, 64, 67], [43, 55, 59, 62, 64]];
const out = new Float32Array(N);
let lp = 0;
for (let i = 0; i < N; i++) {
  const t = i / SR;
  const ci = Math.floor(t / chordLen), local = t - ci * chordLen;
  let v = 0;
  for (const [k, idx] of [[0, ci], [1, ci - 1]]) { // current chord + release tail of the previous one
    if (idx < 0) continue;
    const ch = CHORDS[idx % CHORDS.length];
    const tt = k === 0 ? local : local + chordLen;
    const env = k === 0 ? Math.min(1, tt / 1.4) : Math.max(0, 1 - local / 1.6);
    for (const [j, m] of ch.entries()) {
      const f = n(m), det = 1 + (j % 2 ? 0.0018 : -0.0014);
      v += env * (Math.sin(2 * Math.PI * f * t) + 0.35 * Math.sin(2 * Math.PI * f * det * t) + 0.12 * Math.sin(4 * Math.PI * f * t)) / ch.length;
    }
  }
  // soft pulse on 8th notes, like a gentle sidechain
  const ph = (t % (beat / 2)) / (beat / 2);
  v *= 0.82 + 0.18 * Math.min(1, ph * 3);
  lp += 0.08 * (v - lp); // one-pole low-pass: takes the edge off
  out[i] = lp;
}
let peak = 0; for (const x of out) peak = Math.max(peak, Math.abs(x));
const fade = SR * 2.5;
const pcm = Buffer.alloc(N * 2);
for (let i = 0; i < N; i++) {
  const g = Math.min(1, i / fade, (N - i) / fade);
  pcm.writeInt16LE(Math.round((out[i] / peak) * 0.5 * g * 32767), i * 2);
}
const h = Buffer.alloc(44);
h.write("RIFF", 0); h.writeUInt32LE(36 + pcm.length, 4); h.write("WAVE", 8); h.write("fmt ", 12);
h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22); h.writeUInt32LE(SR, 24);
h.writeUInt32LE(SR * 2, 28); h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34); h.write("data", 36); h.writeUInt32LE(pcm.length, 40);
fs.writeFileSync("public/music.wav", Buffer.concat([h, pcm]));
console.log("public/music.wav", secs, "s");
