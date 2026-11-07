// collects everything the edit needs into src/data.json:
//  - real numbers from the final qc reports (nothing in the video is typed by hand)
//  - recording lengths + cursor logs
//  - talk clip lengths (if the footage is in public/talk/a.mp4 ... j.mp4)
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const ROOT = path.resolve("..");
const L = JSON.parse(fs.readFileSync("lessons.json", "utf8"));
const read = (p) => JSON.parse(fs.readFileSync(p, "utf8"));
const lesson = (id) => path.join(ROOT, "data", "lessons", id);

function stats(id) {
  const st = read(path.join(lesson(id), "state.json"));
  const r = read(path.join(lesson(id), "research.json"));
  const f = read(path.join(lesson(id), "qc_factual.json"));
  const i = read(path.join(lesson(id), "qc_instructional.json"));
  const v = read(path.join(lesson(id), "versions", `v${st.current_version}.json`)).doc;
  const tiers = { A: 0, B: 0, C: 0 };
  r.sources.forEach((s) => tiers[s.tier]++);
  return {
    title: st.title, versions: st.current_version,
    sources: r.sources.length, tierA: tiers.A, videos: r.videos.length,
    transcripts: r.videos.filter((x) => x.has_transcript).length, confusions: r.misconceptions.length,
    sourceKinds: [...new Set(r.sources.map((s) => s.kind))],
    claims: f.summary.claims, supported: f.summary.supported, accuracy: f.summary.accuracy,
    quotes: f.summary.quotes_verified, code: [f.summary.code_pass, f.summary.code_total],
    probes: [f.summary.probes_pass, f.summary.probes_total],
    probeRows: f.probes.map((p) => `${p.method} ${p.url.replace("https://", "")} → ${p.status_code}`),
    pre: i.summary.pre_accuracy, post: i.summary.post_accuracy, rubric: i.summary.rubric_avg,
    minutes: i.summary.total_minutes, issues: f.issues.length + i.issues.length,
    sections: v.sections.length, quiz: v.quiz.length,
  };
}

function dur(file) {
  try {
    const out = execFileSync("npx", ["remotion", "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", file],
                             { encoding: "utf8", shell: true });
    return parseFloat(out.trim());
  } catch { return null; }
}

const rec = {};
for (const f of fs.readdirSync("public/rec").filter((f) => f.endsWith(".json"))) rec[f.replace(".json", "")] = read(path.join("public/rec", f));
const talk = {};
for (const k of "abcdefghij") {
  const f = path.join("public/talk", `${k}.mp4`);
  if (fs.existsSync(f)) talk[k] = dur(f);
}
const data = { http: stats(L.http), sql: stats(L.sql), rec, talk };
fs.writeFileSync("src/data.json", JSON.stringify(data, null, 1));
console.log(JSON.stringify({ http: data.http, sql: data.sql, rec: Object.keys(rec), talk }, null, 1));
