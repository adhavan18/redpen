/* redpen ui. no framework: one state object, render functions, a poller while steps run. */

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const S = { id: null, tab: "lesson", data: null, log: [], lastT: 0, sig: "", poll: null, heat: true, mode: "preview",
            edit: null, dirty: false, selected: new Set(), health: null };

const STEPS = [
  ["research", "01", "research", "books, web, specs, videos"],
  ["draft", "02", "draft", "45-minute lesson"],
  ["qc_factual", "03", "qc 1 · facts", "claims, code, live tests"],
  ["qc_instructional", "04", "qc 2 · teaching", "simulated classroom"],
];
const TABS = [["lesson", "Lesson"], ["research", "Research"], ["qc_factual", "QC 1 · Facts"],
              ["qc_instructional", "QC 2 · Teaching"], ["export", "Export"], ["history", "History"]];
const SAMPLES = [
  ["HTTP Requests and Responses", "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."],
  ["SQL Joins", "Write INNER and LEFT JOIN queries and predict which rows each returns when matching rows are missing."],
  ["Git Branching", "Create and merge branches in Git and explain the difference between a fast-forward and a three-way merge."],
];

// ---------- api ----------
async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts,
                                body: opts.body ? JSON.stringify(opts.body) : undefined });
  if (!r.ok) {
    let msg = r.statusText;
    try { const j = await r.json(); msg = Array.isArray(j.detail) ? j.detail.map((d) => d.msg.replace(/^Value error, /, "")).join("; ") : j.detail || msg; } catch {}
    throw new Error(msg);
  }
  return r.headers.get("content-type")?.includes("json") ? r.json() : r;
}
function toast(msg, bad = false) {
  const t = $("#toast"); t.textContent = msg; t.className = "toast on" + (bad ? " bad" : "");
  clearTimeout(toast.h); toast.h = setTimeout(() => (t.className = "toast"), bad ? 5200 : 2600);
}
const store = {
  get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
  del(k) { try { localStorage.removeItem(k); } catch {} },
};

// ---------- routing ----------
window.addEventListener("hashchange", route);
async function route() {
  const m = location.hash.match(/^#\/l\/([a-z0-9-]+)(?:\/(\w+))?/);
  stopPoll(); closePop();
  if (!m) { S.id = null; return home(); }
  if (S.id !== m[1]) { S.id = m[1]; S.data = null; S.log = []; S.lastT = 0; S.sig = ""; S.edit = null; S.dirty = false; S.selected.clear(); S.mode = "preview"; }
  S.tab = m[2] || "lesson";
  await refresh(true);
}
function go(tab) { location.hash = `#/l/${S.id}/${tab}`; }

async function health() {
  try {
    S.health = await api("/api/health");
    $("#health").innerHTML = S.health.llm_key
      ? `<span class="led"></span>${esc(S.health.model)} · ${esc(S.health.search)}`
      : `<span class="led off"></span>no GEMINI_API_KEY in .env`;
  } catch { $("#health").innerHTML = `<span class="led off"></span>server offline`; }
}

// ---------- home ----------
async function home() {
  $("#crumbs").textContent = "";
  let lessons = [];
  try { lessons = await api("/api/lessons"); } catch (e) { toast(e.message, true); }
  $("#app").innerHTML = `
    <section class="hero">
      <h1>Lessons that show<br>their <em>receipts</em>.</h1>
      <p>Researches the topic, writes a 45-minute lesson, then proves it: every claim matched to a source quote, every code example run, every quiz taken by a simulated classroom.</p>
    </section>
    <form class="composer" id="new" autocomplete="off">
      <label for="f-title">Lesson title</label>
      <input id="f-title" name="title" placeholder="HTTP Requests and Responses" maxlength="160">
      <label for="f-obj">Learning objective</label>
      <textarea id="f-obj" name="objective" rows="2" placeholder="What should the learner be able to do after 45 minutes?" maxlength="600"></textarea>
      <div class="err" id="f-err" hidden></div>
      <div class="row">
        <input name="audience" placeholder="Audience: first-year computer science undergraduates" maxlength="200">
        <button class="btn primary" type="submit">Research &amp; write</button>
      </div>
    </form>
    <div class="chips">${SAMPLES.map((s, i) => `<button class="chip" data-i="${i}">${esc(s[0])}</button>`).join("")}</div>
    ${lessons.length ? `<section class="recent"><h3>Lessons</h3>${lessons.map((l) => `
      <div class="lrow" data-id="${l.id}"><b>${esc(l.title)}</b>
        <div class="minis">${Object.values(l.steps).map((s) => `<i class="mini ${s}"></i>`).join("")}</div>
        <span>v${l.current_version} · ${ago(l.updated_at)}</span></div>`).join("")}</section>` : ""}`;
  $$(".chip").forEach((c) => (c.onclick = () => { const s = SAMPLES[c.dataset.i]; $("#f-title").value = s[0]; $("#f-obj").value = s[1]; }));
  $$(".lrow").forEach((r) => (r.onclick = () => (location.hash = `#/l/${r.dataset.id}/lesson`)));
  $("#new").onsubmit = async (e) => {
    e.preventDefault();
    const f = new FormData(e.target), err = $("#f-err");
    const body = { title: f.get("title").trim(), objective: f.get("objective").trim(), audience: f.get("audience").trim() };
    const problems = [];
    if (!body.title) problems.push("Add a lesson title.");
    if (!body.objective) problems.push("Add a learning objective.");
    if (problems.length) { err.hidden = false; err.textContent = problems.join(" "); return; }
    const btn = e.target.querySelector("button[type=submit]"); btn.disabled = true; btn.textContent = "Starting…";
    try { const st = await api("/api/lessons", { method: "POST", body }); location.hash = `#/l/${st.id}/lesson`; }
    catch (ex) { err.hidden = false; err.textContent = ex.message; btn.disabled = false; btn.textContent = "Research & write"; }
  };
}

// ---------- lesson shell ----------
function signature(d) {
  return JSON.stringify([d.state.current_version, Object.values(d.state.steps).map((s) => s.status + s.attempts),
    d.qc_factual?.created_at, d.qc_instructional?.created_at, d.qc_factual?.issues?.map((i) => i.status).join(""),
    d.qc_instructional?.issues?.map((i) => i.status).join(""), d.state.exports.length]);
}
function busy(d) { return d.state.running || Object.values(d.state.steps).some((s) => ["running", "queued"].includes(s.status)); }

async function refresh(full = false) {
  if (!S.id) return;
  let d;
  try { d = await api(`/api/lessons/${S.id}?since=${S.lastT}`); }
  catch (e) { if (full) { $("#app").innerHTML = `<div class="empty"><b>Lesson not found</b><a href="#/">Back to lessons</a></div>`; } return; }
  if (d.state.log.length) { S.log.push(...d.state.log); S.lastT = d.state.log.at(-1).t; S.log = S.log.slice(-300); }
  const sig = signature(d);
  const changed = sig !== S.sig;
  S.data = d; S.sig = sig;
  if (full || changed) render(); else renderLog();
  if (busy(d)) startPoll(); else stopPoll();
}
function startPoll() { if (!S.poll) S.poll = setInterval(() => refresh(), 1400); }
function stopPoll() { clearInterval(S.poll); S.poll = null; }

function render() {
  const d = S.data, st = d.state;
  $("#crumbs").textContent = st.title;
  const counts = (r) => r && r.version === st.current_version ? r.issues.filter((i) => i.status === "open" && i.severity !== "low").length : 0;
  const mins = d.minutes;
  const scrollY = window.scrollY;
  $("#app").innerHTML = `
    <div class="lhead">
      <div><h1>${esc(st.title)}</h1><div class="obj">${esc(st.objective)}</div></div>
      <div class="clock">${mins != null ? `<div class="num">${mins}<small> / 45 min</small></div>${ring(mins)}` : ""}</div>
    </div>
    <div class="steps">${STEPS.map(([k, n, t, sub]) => stepCard(k, n, t, sub)).join("")}${exportCard()}</div>
    ${!S.health?.llm_key ? `<div class="banner"><b>No Gemini key.</b> Add GEMINI_API_KEY to the .env file in the project folder, restart the server, then press run.</div>` : ""}
    <div class="seg" role="tablist">${TABS.map(([k, label]) => {
      const n = k === "qc_factual" ? counts(d.qc_factual) : k === "qc_instructional" ? counts(d.qc_instructional) : 0;
      return `<button class="${S.tab === k ? "on" : ""}" data-tab="${k}">${label}${n ? `<span class="n">${n}</span>` : ""}</button>`;
    }).join("")}</div>
    <div class="${busy(d) || S.showLog ? "grid2" : ""}"><div id="pane"></div>${busy(d) || S.showLog ? `<aside class="log" id="log"></aside>` : ""}</div>
    ${busy(d) ? "" : `<button class="btn sm logbtn" id="logbtn">${S.showLog ? "hide log" : "show log"}</button>`}`;
  $("#logbtn")?.addEventListener("click", () => { S.showLog = !S.showLog; render(); });
  $$(".seg button").forEach((b) => (b.onclick = () => go(b.dataset.tab)));
  $$("[data-run]").forEach((b) => (b.onclick = () => runSteps(b.dataset.run.split(","))));
  $(".step.exp")?.addEventListener("click", () => go("export"));
  ({ lesson: paneLesson, research: paneResearch, qc_factual: paneQC1, qc_instructional: paneQC2, export: paneExport,
     history: paneHistory }[S.tab] || paneLesson)($("#pane"));
  renderLog();
  window.scrollTo(0, scrollY);
}
function ring(m) {
  const pct = Math.min(1, m / 45), over = m > 45, c = 2 * Math.PI * 16;
  return `<svg width="44" height="44" viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="16" fill="none" stroke="#e5e5ea" stroke-width="5"/>
    <circle cx="20" cy="20" r="16" fill="none" stroke="${over ? "#ef3837" : "#1d1d1f"}" stroke-width="5" stroke-linecap="round"
    stroke-dasharray="${c * pct} ${c}" transform="rotate(-90 20 20)"/></svg>`;
}
function stepCard(k, n, title, sub) {
  const s = S.data.state.steps[k], st = s.status;
  const deps = { research: [], draft: ["research"], qc_factual: ["draft"], qc_instructional: ["draft"] }[k];
  const ready = deps.every((x) => ["done", "stale"].includes(S.data.state.steps[x].status));
  const label = { idle: sub, queued: "queued", running: "running", done: "done", failed: "failed", stale: "out of date: lesson edited", blocked: "waiting: earlier step failed" }[st] || st;
  let btn = "";
  const running = busy(S.data);
  if (!running && ready) {
    const runSet = k === "research" ? "research,draft,qc_factual,qc_instructional" : k === "draft" ? "draft,qc_factual,qc_instructional" : k;
    if (st === "failed") btn = `<button class="btn sm primary" data-run="${k}">Retry</button>`;
    else if (st === "idle" || st === "blocked") btn = `<button class="btn sm dark" data-run="${runSet}">Run</button>`;
    else if (st === "stale") btn = `<button class="btn sm dark" data-run="${k}">Re-run</button>`;
    else if (st === "done") btn = `<button class="btn sm ghost" data-run="${k}" title="run again">↻</button>`;
  }
  return `<div class="step ${st}"><div class="k">${n}</div><div class="t">${title}</div>
    <div class="s">${st === "running" ? '<span class="spin"></span>' : ""}${esc(label)}</div>
    ${s.error && st === "failed" ? `<div class="small" style="color:var(--red-ink);margin-top:4px" title="${esc(s.error)}">${esc(s.error.slice(0, 90))}</div>` : ""}
    <div class="act">${btn}</div></div>`;
}
function exportCard() {
  const g = S.data.gate;
  return `<div class="step exp ${g.ok ? "done" : ""}" style="cursor:pointer"><div class="k">05</div><div class="t">review · export</div>
    <div class="s">${g.ok ? "ready to export" : `${g.reasons.length} thing${g.reasons.length > 1 ? "s" : ""} to resolve`}</div></div>`;
}
async function runSteps(steps) {
  try { await api(`/api/lessons/${S.id}/run`, { method: "POST", body: { steps } }); toast("Started"); await refresh(true); }
  catch (e) { toast(e.message, true); }
}
function renderLog() {
  const el = $("#log"); if (!el) return;
  const label = { research: "research", draft: "draft", qc_factual: "qc 1", qc_instructional: "qc 2" };
  el.innerHTML = `<h4>live log</h4>` + (S.log.length ? S.log.slice(-120).map((l) =>
    `<div class="l ${l.kind}"><span class="st">${label[l.step] || l.step}</span><span class="m">${esc(l.msg)}</span></div>`).join("")
    : `<div class="l"><span class="m" style="color:#8e8e93">nothing yet</span></div>`);
  el.scrollTop = el.scrollHeight;
}

// ---------- lesson tab ----------
function currentReport(layer) { const r = S.data[layer]; return r && r.version === S.data.state.current_version ? r : null; }

function paneLesson(el) {
  const v = S.data.version;
  if (!v) {
    const st = S.data.state.steps;
    el.innerHTML = `<div class="card empty"><b>${st.research.status === "running" || st.draft.status === "running" ? "Researching and writing…" : "No lesson yet"}</b>
      ${st.research.status === "running" ? "Searching the web, specs, Wikipedia, books, Stack Overflow and YouTube transcripts. Watch the live log." : st.draft.status === "running" ? "Writing from the evidence pack." : "Press Run on research to start."}</div>`;
    return;
  }
  const stored = store.get(`redpen:draft:${S.id}`);
  const restore = stored && !S.dirty && stored.base_version === v.version ? `<div class="banner warn"><span style="flex:1">You have unsaved edits from an earlier session.</span>
      <button class="btn sm dark" id="rs-yes">Restore</button><button class="btn sm" id="rs-no">Discard</button></div>` : "";
  el.innerHTML = `${restore}
    <div style="display:flex;gap:12px;align-items:center;margin-bottom:14px">
      <div class="seg" style="margin:0"><button class="${S.mode === "preview" ? "on" : ""}" data-m="preview">Preview</button><button class="${S.mode === "edit" ? "on" : ""}" data-m="edit">Edit</button></div>
      ${S.mode === "preview" && currentReport("qc_factual") ? `<label class="toggle"><input type="checkbox" id="heat" ${S.heat ? "checked" : ""}> trust heatmap</label>` : ""}
      <span class="muted small" style="margin-left:auto">v${v.version} · ${esc(v.author)} · ${esc(v.note)}</span>
    </div>
    <div id="lbody"></div>`;
  $$("[data-m]", el).forEach((b) => (b.onclick = () => { S.mode = b.dataset.m; if (S.mode === "edit" && !S.dirty) S.edit = structuredClone(v.doc); paneLesson(el); }));
  $("#heat")?.addEventListener("change", (e) => { S.heat = e.target.checked; $(".prose")?.classList.toggle("heat", S.heat); });
  $("#rs-yes")?.addEventListener("click", () => { S.edit = stored.doc; S.dirty = true; S.mode = "edit"; paneLesson(el); });
  $("#rs-no")?.addEventListener("click", () => { store.del(`redpen:draft:${S.id}`); paneLesson(el); });
  if (S.mode === "edit") editor($("#lbody")); else preview($("#lbody"), v.doc);
}

function mdToHtml(md) { return DOMPurify.sanitize(marked.parse(md, { gfm: true }), { ADD_ATTR: ["data-c"] }); }

function preview(el, doc) {
  const r = S.data.research, qc = currentReport("qc_factual");
  const srcs = Object.fromEntries((r?.sources || []).map((s) => [s.id, s]));
  const ms = Object.fromEntries((r?.misconceptions || []).map((m) => [m.id, m]));
  const claims = qc ? qc.claims.map((c, i) => ({ ...c, idx: i })) : [];
  const sheet = S.data.qc_instructional?.measurements?.run_sheet;
  const vidsAfter = {};
  (doc.videos || []).forEach((v) => (vidsAfter[v.after_section] ||= []).push(v));
  let html = "";
  if (sheet) html += timeline(sheet);
  const pill = (id) => id[0] === "M"
    ? (ms[id] ? `<a class="cite" href="${esc(ms[id].url)}" target="_blank" title="${esc(ms[id].title)}">${id}</a>` : id)
    : `<a class="cite ${srcs[id]?.tier === "A" ? "A" : ""} ${srcs[id] ? "" : "bad"}" data-s="${id}">${id}</a>`;
  for (const sec of doc.sections) {
    // [S6] and [S6, S9] both become pills
    let body = mdToHtml(sec.body_md).replace(/\[\s*([SM]\d+(?:\s*[,;]\s*[SM]\d+)*)\s*\]/g, (m, ids) => ids.split(/\s*[,;]\s*/).map(pill).join(""));
    html += `<section data-sec="${sec.id}"><div class="kind">${esc(sec.kind)}</div><h2 class="sec">${esc(sec.title)}<span class="min">${sec.minutes} min</span></h2>${body}</section>`;
    for (const v of vidsAfter[sec.id] || []) html += videoCard(v);
  }
  if (doc.quiz?.length) {
    html += `<div class="kind">assessment</div><h2 class="sec">Knowledge check<span class="min">${doc.quiz_minutes} min</span></h2>`;
    html += doc.quiz.map((q, i) => `<div class="quizq"><b>${i + 1}. ${esc(q.question)}</b><ol type="A">${q.options.map((o, oi) =>
      `<li class="${oi === q.answer_index ? "ans" : ""}">${esc(o)}</li>`).join("")}</ol><div class="small muted" style="margin-top:6px">${esc(q.explanation)}</div></div>`).join("");
  }
  const cited = new Set([...doc.sections.map((s) => s.body_md).join(" ").matchAll(/\[(S\d+)\]/g)].map((m) => m[1]));
  html += `<div class="kind">sources</div><h2 class="sec">References</h2><ol style="padding-left:20px">${(r?.sources || []).filter((s) => cited.has(s.id)).map((s) =>
    `<li value="${s.id.slice(1)}"><a href="${esc(s.url)}" target="_blank">${esc(s.title)}</a> <span class="pill ${s.tier}">tier ${s.tier}</span> <span class="muted small">${esc(s.tier_reason)}</span></li>`).join("")}</ol>`;
  el.innerHTML = `<div class="card"><div class="prose ${S.heat ? "heat" : ""}">${html}</div></div>`;
  for (const c of claims) {
    const secEl = el.querySelector(`section[data-sec="${c.section_id}"]`);
    if (secEl) highlight(secEl, c.sentence, c.verdict, c.idx);
  }

  // execution badges under each python / js block, in order per section
  if (qc) {
    for (const secEl of $$("section[data-sec]", el)) {
      const results = qc.code.filter((c) => c.section_id === secEl.dataset.sec);
      const blocks = $$("pre code", secEl).filter((c) => /language-(python|py|python3|javascript|js|node)\b/.test(c.className));
      blocks.forEach((b, i) => {
        const res = results[i]; if (!res) return;
        const badge = document.createElement("div");
        badge.className = "runbadge";
        badge.innerHTML = `<span class="pill ${res.status}">${{ pass: "✓ ran, output matches", mismatch: "✗ output differs", error: "✗ crashed", timeout: "✗ timed out", ran: "ran", skipped: "not run" }[res.status]}</span>
          <span>${esc(res.note)}${res.ms ? ` · ${res.ms} ms` : ""}</span>`;
        const pre = b.closest("pre"), next = pre.nextElementSibling;
        (next && next.tagName === "PRE" && /language-(output|text|console)/.test(next.querySelector("code")?.className || "") ? next : pre).after(badge);
      });
    }
  }
  $$("mark.claim", el).forEach((m) => (m.onclick = (e) => claimPop(e, claims[m.dataset.c], srcs)));
  $$("a.cite[data-s]", el).forEach((a) => (a.onclick = (e) => sourcePop(e, srcs[a.dataset.s])));
}
/* find a claim's sentence in the rendered section and tint it. matching is on letters and digits
   only, so markdown, citation pills and punctuation differences do not matter; the match can
   span bold / code / link elements, each piece gets its own <mark>. */
function highlight(container, sentence, verdict, idx) {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => n.parentElement.closest("pre, a.cite, mark, h2, .kind") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
  const nodes = []; let text = "";
  while (walker.nextNode()) { nodes.push([walker.currentNode, text.length]); text += walker.currentNode.nodeValue; }
  const keep = [], pos = [];
  for (let i = 0; i < text.length; i++) { const ch = text[i].toLowerCase(); if (/[a-z0-9]/.test(ch)) { keep.push(ch); pos.push(i); } }
  const needle = sentence.replace(/\[[^\]]*\]/g, "").replace(/^\s*([-*+]|\d+\.)\s+/, "").toLowerCase().replace(/[^a-z0-9]/g, "");
  if (needle.length < 12) return false;
  const at = keep.join("").indexOf(needle);
  if (at < 0) return false;
  const start = pos[at], end = pos[at + needle.length - 1] + 1;
  for (const [n, off] of nodes) {
    const s = Math.max(start, off), e = Math.min(end, off + n.nodeValue.length);
    if (s >= e) continue;
    const r = document.createRange(); r.setStart(n, s - off); r.setEnd(n, e - off);
    const m = document.createElement("mark"); m.className = `claim ${verdict}`; m.dataset.c = idx;
    r.surroundContents(m);
  }
  return true;
}
function timeline(sheet) {
  const total = Math.max(45, sheet.at(-1)?.end || 45);
  return `<div style="margin-bottom:28px"><div class="sec-h">45-minute run sheet</div><div class="timeline">${sheet.map((s) =>
    `<div class="k-${s.kind}" style="flex:${Math.max(s.end - s.start, 0.6)}" title="${s.start}-${s.end} min · ${esc(s.what)}">${s.end - s.start >= 4 ? esc(s.kind) : ""}</div>`).join("")}
    ${total > (sheet.at(-1)?.end || 0) ? `<div style="flex:${total - sheet.at(-1).end};background:#e5e5ea"></div>` : ""}</div>
    <div class="tl-legend"><span>0</span><span>15</span><span>30</span><span>45 min</span></div></div>`;
}
function videoCard(v) {
  const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  return `<a class="vid" href="${esc(v.url)}" target="_blank" style="text-decoration:none"><img src="https://i.ytimg.com/vi/${esc(v.video_id)}/mqdefault.jpg" alt="">
    <div><span class="pill ${v.in_lesson ? "solid" : ""}">${v.in_lesson ? "watch now" : "optional"} · ${fmt(v.start)}–${fmt(v.end)}</span>
    <b>${esc(v.title)}</b><div class="meta">${esc(v.channel)} · ${v.watch_minutes} min clip · ${esc(v.why)}</div></div></a>`;
}

// ---------- popovers ----------
function place(e, html) {
  const p = $("#pop"); p.innerHTML = html; p.hidden = false;
  const r = e.target.getBoundingClientRect();
  p.style.left = Math.min(window.scrollX + r.left, window.scrollX + document.documentElement.clientWidth - 400) + "px";
  p.style.top = window.scrollY + r.bottom + 8 + "px";
  e.stopPropagation();
}
function closePop() { $("#pop").hidden = true; }
document.addEventListener("click", (e) => { if (!e.target.closest("#pop")) closePop(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closePop(); closeModal(); } });
function claimPop(e, c, srcs) {
  const s = srcs[c.source_id];
  place(e, `<div style="display:flex;gap:6px;align-items:center;margin-bottom:6px"><span class="pill ${c.verdict}">${c.verdict}</span>
    ${c.quote ? (c.quote_verified ? `<span class="pill green">quote found in source</span>` : `<span class="pill red">quote not in source</span>`) : ""}</div>
    <div><b>${esc(c.claim)}</b></div>
    ${c.quote ? `<div class="quote">“${esc(c.quote)}”</div>` : ""}
    ${s ? `<div class="src">${esc(c.source_id)} · <a href="${esc(s.url)}" target="_blank">${esc(s.title)}</a> · tier ${s.tier}</div>` : ""}
    <div class="small muted" style="margin-top:8px">${esc(c.reasoning)}</div>
    ${c.downgrade_note ? `<div class="small" style="color:var(--amber);margin-top:6px">${esc(c.downgrade_note)}</div>` : ""}
    ${c.external ? `<div class="small" style="margin-top:8px"><b>Google-grounded:</b> ${esc(c.external.verdict)}: ${esc(c.external.note)}</div>` : ""}
    ${(c.probes || []).map((p) => `<div class="small mono" style="margin-top:8px">${p.passed ? "✓" : "✗"} ${esc(p.method)} ${esc(p.url)} → ${p.status_code ?? "error"}</div>`).join("")}
    ${c.fix ? `<div class="issue" style="display:block;padding:0;border:0"><div class="fx">${esc(c.fix)}</div></div>` : ""}`);
}
function sourcePop(e, s) {
  if (!s) return place(e, `<b>Unknown source.</b> This citation does not match any research source.`);
  place(e, `<div style="display:flex;gap:6px;margin-bottom:6px"><span class="pill ${s.tier}">tier ${s.tier}</span><span class="pill">${esc(s.kind)}</span><span class="pill">relevance ${s.relevance}</span></div>
    <b>${esc(s.title)}</b><div class="small muted">${esc(s.tier_reason)}</div><div class="src"><a href="${esc(s.url)}" target="_blank">${esc(s.url)}</a></div>`);
}

// ---------- editor ----------
function editor(el) {
  const v = S.data.version;
  if (!S.edit) S.edit = structuredClone(v.doc);
  const d = S.edit;
  el.innerHTML = `${d.sections.map((s, i) => `
    <div class="ed" data-i="${i}"><div class="eh"><span class="pill">${esc(s.kind)}</span>
      <input class="title" value="${esc(s.title)}" data-f="title"><input class="min" type="number" min="1" max="45" value="${s.minutes}" data-f="minutes"><span class="small muted">min</span></div>
      <textarea data-f="body_md" spellcheck="true">${esc(s.body_md)}</textarea></div>`).join("")}
    <div class="ed"><div class="eh"><span class="pill">quiz</span><b style="flex:1">Knowledge check</b><input class="min" type="number" min="1" max="20" value="${d.quiz_minutes}" id="qmin"><span class="small muted">min</span></div>
    ${d.quiz.map((q, qi) => `<div class="qe" data-q="${qi}"><textarea rows="2" data-qf="question">${esc(q.question)}</textarea>
      ${q.options.map((o, oi) => `<div class="opt"><input type="radio" name="ans${qi}" ${oi === q.answer_index ? "checked" : ""} data-ans="${oi}" title="correct answer"><input value="${esc(o)}" data-opt="${oi}"></div>`).join("")}
      <input value="${esc(q.explanation)}" data-qf="explanation" placeholder="explanation"></div>`).join('<hr style="border:0;border-top:1px solid var(--line);margin:0">')}</div>
    <div class="savebar"><span id="dstate">${S.dirty ? "Unsaved changes (kept in this browser until you save)" : "No changes"}</span>
      <button class="btn" id="discard" ${S.dirty ? "" : "disabled"}>Discard</button><button class="btn primary" id="save" ${S.dirty ? "" : "disabled"}>Save as v${v.version + 1}</button></div>`;
  const touch = () => {
    S.dirty = true; store.set(`redpen:draft:${S.id}`, { base_version: v.version, doc: S.edit });
    $("#dstate").textContent = "Unsaved changes (kept in this browser until you save)"; $("#save").disabled = false; $("#discard").disabled = false;
  };
  $$(".ed[data-i]", el).forEach((box) => {
    const s = d.sections[box.dataset.i];
    $$("[data-f]", box).forEach((inp) => (inp.oninput = () => { s[inp.dataset.f] = inp.dataset.f === "minutes" ? +inp.value : inp.value; box.classList.add("dirty"); touch(); }));
  });
  $("#qmin").oninput = (e) => { d.quiz_minutes = +e.target.value; touch(); };
  $$(".qe", el).forEach((box) => {
    const q = d.quiz[box.dataset.q];
    $$("[data-qf]", box).forEach((inp) => (inp.oninput = () => { q[inp.dataset.qf] = inp.value; touch(); }));
    $$("[data-opt]", box).forEach((inp) => (inp.oninput = () => { q.options[+inp.dataset.opt] = inp.value; touch(); }));
    $$("[data-ans]", box).forEach((inp) => (inp.onchange = () => { q.answer_index = +inp.dataset.ans; touch(); }));
  });
  $("#discard").onclick = () => { S.edit = structuredClone(v.doc); S.dirty = false; store.del(`redpen:draft:${S.id}`); editor(el); };
  $("#save").onclick = async () => {
    try {
      const r = await api(`/api/lessons/${S.id}/lesson`, { method: "PUT", body: { doc: S.edit, base_version: v.version, note: "instructor edit" } });
      S.dirty = false; S.edit = null; store.del(`redpen:draft:${S.id}`); toast(`Saved v${r.version}. QC is now out of date; re-run it.`);
      await refresh(true);
    } catch (e) { toast(e.message, true); }
  };
}

// ---------- research tab ----------
function paneResearch(el) {
  const r = S.data.research;
  if (!r) { el.innerHTML = `<div class="card empty"><b>No research yet</b>Run the research step.</div>`; return; }
  const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  const tiers = { A: 0, B: 0, C: 0 }; r.sources.forEach((s) => tiers[s.tier]++);
  el.innerHTML = `
    <div class="stats">
      <div class="stat"><div class="v">${r.sources.length}</div><div class="l">sources kept</div></div>
      <div class="stat"><div class="v">${tiers.A}<small> / ${tiers.B} / ${tiers.C}</small></div><div class="l">tier A / B / C</div></div>
      <div class="stat"><div class="v">${r.chunk_count}</div><div class="l">passages indexed${r.embedded ? " (embedded)" : " (keyword)"}</div></div>
      <div class="stat"><div class="v">${r.videos.filter((v) => v.has_transcript).length}<small> / ${r.videos.length}</small></div><div class="l">videos with transcripts</div></div>
      <div class="stat"><div class="v">${r.misconceptions.length}</div><div class="l">learner confusions found</div></div>
    </div>
    <div class="card"><h2>Objective, split into assessable parts</h2><ol>${r.plan.objective_parts.map((p) => `<li>${esc(p)}</li>`).join("")}</ol>
      <div class="small muted">queries: ${[...r.plan.primary_source_queries, ...r.plan.web_queries].map(esc).join(" · ")}</div></div>
    <div class="card"><h2>Sources</h2><table class="t"><tr><th>id</th><th>source</th><th>kind</th><th>tier</th><th>relevance</th></tr>
      ${r.sources.map((s) => `<tr><td class="mono">${s.id}</td><td><a href="${esc(s.url)}" target="_blank">${esc(s.title)}</a>${s.authors ? `<div class="small muted">${esc(s.authors)} ${esc(s.published || "")}</div>` : ""}<div class="small muted">${esc(s.tier_reason)}</div></td>
        <td><span class="pill">${esc(s.kind)}</span></td><td><span class="pill ${s.tier}">${s.tier}</span></td>
        <td><div class="bar-s" title="${s.relevance}"><i style="width:${Math.max(4, Math.min(100, s.relevance * 100))}%"></i></div></td></tr>`).join("")}</table></div>
    <div class="card"><h2>Videos, cut to the minutes that teach the objective</h2><div class="thumbs">${r.videos.map((v) => `
      <div class="vcard"><a href="${esc(v.url)}" target="_blank"><img src="https://i.ytimg.com/vi/${esc(v.video_id)}/mqdefault.jpg" alt=""></a>
      <div class="b"><b>${esc(v.title)}</b><div class="muted small">${esc(v.channel)} · ${fmt(v.duration)} · ${v.views.toLocaleString()} views · <span class="pill ${v.tier}">${v.tier}</span></div>
      <div class="seg-row">${v.segments.map((s) => `<a class="pill" href="https://www.youtube.com/watch?v=${esc(v.video_id)}&t=${Math.floor(s.start)}s" target="_blank" title="${esc(s.objective_part)}">${fmt(s.start)}–${fmt(s.end)}</a>`).join("") || `<span class="small muted">${esc(v.transcript_error || "no transcript")}</span>`}</div></div></div>`).join("")}</div></div>
    <div class="card"><h2>What real learners get confused about</h2><table class="t">${r.misconceptions.map((m) => `<tr><td class="mono">${m.id}</td><td><a href="${esc(m.url)}" target="_blank">${esc(m.title)}</a></td><td class="muted small">${m.score} votes</td></tr>`).join("") || "<tr><td class='muted'>none found</td></tr>"}</table></div>
    ${r.failures.length ? `<div class="card"><h2>What could not be fetched</h2><table class="t">${r.failures.map((f) => `<tr><td><span class="pill">${esc(f.kind)}</span></td><td class="small" style="word-break:break-all">${esc(f.target)}</td><td class="small muted">${esc(f.error)}</td></tr>`).join("")}</table></div>` : ""}`;
}

// ---------- issues (shared by both qc tabs) ----------
function issuesBlock(rep, layer) {
  const open = rep.issues.filter((i) => i.status === "open").length;
  return `<div class="card"><div style="display:flex;align-items:center;gap:10px"><h2 style="margin:0;flex:1">Findings</h2>
      <span class="muted small">${open} open · ${rep.issues.length} total · found by: check = code, executed = ran it, simulated = classroom, llm = reviewer model</span></div>
    ${rep.issues.map((i) => `<div class="issue ${i.status}">
      <input type="checkbox" data-iss="${i.id}" ${i.status !== "open" ? "disabled" : ""} ${S.selected.has(i.id) ? "checked" : ""} title="${i.section_id ? "select to fix" : "whole-lesson finding: fix by editing"}">
      <div><div class="h"><span class="pill ${i.severity}">${i.severity}</span><span class="pill">${esc(i.category)}</span><span class="pill">${esc(i.origin)}</span>
        <span class="muted small">${esc(i.id)} · ${esc(sectionName(i.section_id))}</span>${i.status !== "open" ? `<span class="pill solid">${i.status}</span>` : ""}</div>
        <div class="d">${esc(i.description)}</div>${i.evidence ? `<div class="ev">${esc(i.evidence)}</div>` : ""}
        ${i.suggestion ? `<div class="fx">${esc(i.suggestion)}</div>` : ""}${i.note ? `<div class="small muted" style="margin-top:4px">${esc(i.note)}</div>` : ""}</div></div>`).join("") || `<div class="muted">No findings.</div>`}
    <div class="issuebar" id="ibar" ${S.selected.size ? "" : "hidden"}><span id="icount"></span>
      <button class="btn sm" id="i-dismiss">Dismiss</button><button class="btn sm primary" id="i-fix">Preview fixes</button></div></div>`;
}
function sectionName(id) {
  if (!id) return "whole lesson"; if (id === "quiz") return "knowledge check";
  return S.data.version?.doc.sections.find((s) => s.id === id)?.title || id;
}
function wireIssues(el) {
  const upd = () => { const b = $("#ibar", el); if (!b) return; b.hidden = !S.selected.size; $("#icount", el).textContent = `${S.selected.size} selected`; };
  $$("[data-iss]", el).forEach((c) => (c.onchange = () => { c.checked ? S.selected.add(c.dataset.iss) : S.selected.delete(c.dataset.iss); upd(); }));
  upd();
  $("#i-fix", el)?.addEventListener("click", previewFixes);
  $("#i-dismiss", el)?.addEventListener("click", () => {
    openModal(`<h2>Dismiss ${S.selected.size} finding(s)</h2><p class="muted">Say why, so the next reviewer knows it was a decision, not an oversight.</p>
      <textarea id="dnote" rows="3" style="width:100%;border:1px solid var(--line);border-radius:10px;padding:10px"></textarea>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:12px"><button class="btn" onclick="closeModal()">Cancel</button><button class="btn dark" id="dgo">Dismiss</button></div>`);
    $("#dgo").onclick = async () => {
      const note = $("#dnote").value.trim(); if (note.length < 4) return toast("Add a short reason", true);
      try { await api(`/api/lessons/${S.id}/issues`, { method: "POST", body: { ids: [...S.selected], status: "dismissed", note: "dismissed: " + note } });
        S.selected.clear(); closeModal(); await refresh(true); } catch (e) { toast(e.message, true); }
    };
  });
}

// ---------- fixes ----------
async function previewFixes() {
  const ids = [...S.selected];
  openModal(`<h2>Drafting fixes</h2><p class="muted"><span class="spin" style="display:inline-block;vertical-align:-1px"></span> Rewriting only the affected sections, using the research evidence. Nothing is saved until you accept.</p>`);
  let res;
  try { res = await api(`/api/lessons/${S.id}/fixes/preview`, { method: "POST", body: { issue_ids: ids } }); }
  catch (e) { closeModal(); return toast(e.message, true); }
  const ok = res.proposals.filter((p) => !p.error);
  $("#sheet").innerHTML = `<h2>Review proposed fixes</h2><p class="muted">Based on v${res.base_version}. Untick anything you don't want. Accepting saves a new version; the old one stays in history.</p>
    ${res.manual.length ? `<div class="banner info">${res.manual.join(", ")} apply to the whole lesson. Fix those by editing.</div>` : ""}
    ${res.proposals.map((p, i) => `<div class="card" style="border:1px solid var(--line)">
      <div style="display:flex;gap:10px;align-items:center;margin-bottom:8px">${p.error ? "" : `<input type="checkbox" checked data-p="${i}" style="accent-color:var(--red);width:16px;height:16px">`}
        <b style="flex:1">${esc(p.title || p.target)}</b><span class="muted small">${p.issue_ids.join(", ")}</span></div>
      ${p.error ? `<div class="banner">Could not draft this fix: ${esc(p.error)}</div>` : `<div class="small" style="margin-bottom:8px;white-space:pre-wrap">${esc(p.change_summary)}</div>${diffHtml(asText(p.before), asText(p.after))}`}</div>`).join("")}
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:16px"><button class="btn" onclick="closeModal()">Cancel</button>
      <button class="btn primary" id="accept" ${ok.length ? "" : "disabled"}>Apply as v${S.data.state.current_version + 1}</button></div>`;
  $("#accept").onclick = async () => {
    const chosen = $$("[data-p]").filter((c) => c.checked).map((c) => res.proposals[+c.dataset.p]);
    if (!chosen.length) return toast("Nothing selected", true);
    try { const r = await api(`/api/lessons/${S.id}/fixes/accept`, { method: "POST", body: { base_version: res.base_version, proposals: chosen } });
      S.selected.clear(); closeModal(); toast(`Applied, saved as v${r.version}. Re-run QC to confirm.`); await refresh(true); }
    catch (e) { toast(e.message, true); }
  };
}
function asText(x) {
  if (typeof x === "string") return x;
  return x.map((q, i) => `Q${i + 1}. ${q.question}\n` + q.options.map((o, oi) => `  ${oi === q.answer_index ? "*" : " "} ${o}`).join("\n")).join("\n\n");
}
function diffHtml(a, b) {
  const A = a.split("\n"), B = b.split("\n"), n = A.length, m = B.length;
  const L = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = A[i] === B[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const out = []; let i = 0, j = 0;
  while (i < n && j < m) {
    if (A[i] === B[j]) { out.push(`<div>${esc(A[i]) || "&nbsp;"}</div>`); i++; j++; }
    else if (L[i + 1][j] >= L[i][j + 1]) out.push(`<div class="del">${esc(A[i++]) || "&nbsp;"}</div>`);
    else out.push(`<div class="add">${esc(B[j++]) || "&nbsp;"}</div>`);
  }
  while (i < n) out.push(`<div class="del">${esc(A[i++]) || "&nbsp;"}</div>`);
  while (j < m) out.push(`<div class="add">${esc(B[j++]) || "&nbsp;"}</div>`);
  return `<div class="diff">${out.join("")}</div>`;
}
function openModal(html) { $("#sheet").innerHTML = html; $("#modal").hidden = false; }
function closeModal() { $("#modal").hidden = true; }
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });

// ---------- qc 1 ----------
function staleBanner(rep) {
  return rep.version !== S.data.state.current_version
    ? `<div class="banner warn"><span style="flex:1">This report checked <b>v${rep.version}</b>; the lesson is now <b>v${S.data.state.current_version}</b>.</span><button class="btn sm dark" data-rerun="${rep.layer}">Re-run</button></div>` : "";
}
function qcEmpty(el, layer, what) {
  const st = S.data.state.steps[layer];
  el.innerHTML = `<div class="card empty"><b>${st.status === "running" ? "Checking…" : "Not run yet"}</b>${st.status === "running" ? "Follow the live log." : what}</div>`;
}
function paneQC1(el) {
  const rep = S.data.qc_factual;
  if (!rep) return qcEmpty(el, "qc_factual", "QC 1 runs automatically after the draft, or press Run above.");
  const s = rep.summary;
  el.innerHTML = `${staleBanner(rep)}
    <div class="stats">
      <div class="stat hero-red"><div class="v">${s.accuracy}<small>%</small></div><div class="l">claim accuracy (${s.supported} of ${s.claims} fully supported)</div></div>
      <div class="stat"><div class="v">${s.quotes_verified}<small> / ${s.claims}</small></div><div class="l">evidence quotes verified verbatim</div></div>
      <div class="stat"><div class="v">${s.code_pass}<small> / ${s.code_total}</small></div><div class="l">code examples ran and matched</div></div>
      <div class="stat"><div class="v">${s.probes_pass}<small> / ${s.probes_total}</small></div><div class="l">claims confirmed by live HTTP</div></div>
      <div class="stat"><div class="v">${s.tier_a_cited}<small> / ${s.cited_sources}</small></div><div class="l">cited sources that are primary</div></div>
      <div class="stat"><div class="v">${s.copied_spans}</div><div class="l">copied passages</div></div>
    </div>
    ${issuesBlock(rep, "qc_factual")}
    <div class="card"><h2>Every claim, checked against its evidence</h2><table class="t"><tr><th>verdict</th><th>claim</th><th>evidence</th></tr>
      ${rep.claims.map((c) => `<tr><td><span class="pill ${c.verdict}">${c.verdict}</span></td><td>${esc(c.claim)}<div class="small muted">${esc(sectionName(c.section_id))}</div></td>
        <td>${c.quote ? `<div class="quote" style="margin:0">“${esc(c.quote)}”</div><div class="small" style="margin-top:4px">${c.quote_verified ? '<span class="ok-tick">✓</span> found verbatim in' : '<span class="no-tick">✗</span> not found in'} ${esc(c.source_id || "")}</div>` : `<span class="small muted">${esc(c.reasoning)}</span>`}
        ${c.external ? `<div class="small" style="margin-top:4px">Google: <b>${esc(c.external.verdict)}</b>, ${esc(c.external.note)}</div>` : ""}</td></tr>`).join("")}</table></div>
    ${rep.code.length ? `<div class="card"><h2>Code examples, executed</h2>${rep.code.map((r) => `<div style="margin-bottom:16px">
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:6px"><span class="pill ${r.status}">${r.status}</span><b>${esc(sectionName(r.section_id))}</b><span class="muted small">${esc(r.language)} · ${esc(r.note)}</span></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px"><div><div class="sec-h">lesson says</div><pre class="diff" style="padding:10px">${esc(r.expected || "(no output shown)")}</pre></div>
      <div><div class="sec-h">actually printed</div><pre class="diff" style="padding:10px">${esc(r.actual ?? r.stderr ?? "")}</pre></div></div></div>`).join("")}</div>` : ""}
    ${rep.probes.length ? `<div class="card"><h2>Live HTTP tests</h2><table class="t"><tr><th></th><th>request</th><th>got</th><th>expected</th><th>tests the claim</th></tr>
      ${rep.probes.map((p) => `<tr><td>${p.passed ? '<span class="ok-tick">✓</span>' : '<span class="no-tick">✗</span>'}</td><td class="mono">${esc(p.method)} ${esc(p.url)}</td><td class="mono">${p.status_code ?? esc(p.error)} ${esc(p.reason || "")}</td>
        <td class="mono">${p.expect_status_min}–${p.expect_status_max}</td><td class="small">${esc(rep.claims[p.claim_index]?.claim)}</td></tr>`).join("")}</table></div>` : ""}
    <div class="card"><h2>Citation coverage by section</h2><table class="t"><tr><th>section</th><th>cited sentences</th><th>sources</th></tr>
      ${rep.citations.map((c) => `<tr><td>${esc(c.title)} <span class="pill">${esc(c.kind)}</span></td><td>${c.cited_sentences} / ${c.sentences}</td><td class="mono small">${Object.entries(c.sources).map(([k, v]) => `${k}×${v}`).join(" ") || "—"}</td></tr>`).join("")}</table></div>
    ${rep.errors.length ? `<div class="card"><h2>Checks that could not run</h2><ul>${rep.errors.map((e) => `<li class="small">${esc(e)}</li>`).join("")}</ul></div>` : ""}`;
  wireIssues(el);
  $$("[data-rerun]", el).forEach((b) => (b.onclick = () => runSteps([b.dataset.rerun])));
}

// ---------- qc 2 ----------
function paneQC2(el) {
  const rep = S.data.qc_instructional;
  if (!rep) return qcEmpty(el, "qc_instructional", "QC 2 runs automatically after the draft, or press Run above.");
  const s = rep.summary, cls = rep.classroom, doc = S.data.version?.doc;
  const names = cls.cohort.map((c) => c.name);
  el.innerHTML = `${staleBanner(rep)}
    <div class="stats">
      <div class="stat hero-red"><div class="v">${s.pre_accuracy ?? "–"}<small>%</small> → ${s.post_accuracy ?? "–"}<small>%</small></div><div class="l">simulated class, before → after the lesson</div></div>
      <div class="stat"><div class="v">${s.rubric_avg ?? "–"}<small> / 5</small></div><div class="l">rubric average</div></div>
      <div class="stat"><div class="v">${s.total_minutes}<small> min</small></div><div class="l">planned time (limit 45)</div></div>
      <div class="stat"><div class="v">${s.confusions}</div><div class="l">places students got stuck</div></div>
    </div>
    ${issuesBlock(rep, "qc_instructional")}
    <div class="card"><h2>Simulated classroom</h2><p class="muted small">Four simulated students answer every question before reading (faded dot) and after reading only this lesson (solid dot). Green = correct. This flags questions to look at; it is not a substitute for real students.</p>
      <div class="class"><div class="hd">question</div>${cls.cohort.map((c) => `<div class="hd">${esc(c.name)}<br><span style="text-transform:none;letter-spacing:0">${esc(c.level)}</span></div>`).join("")}<div class="hd">gain</div><div class="hd">discrim.</div>
      ${cls.items.map((it) => `<div>${esc(it.question)}${it.dead_distractors.length ? `<div class="small muted">unpicked options: ${it.dead_distractors.map((x) => String.fromCharCode(65 + x)).join(", ")}</div>` : ""}</div>
        ${names.map((n) => { const pre = it.pre_answers[n], post = it.post_answers[n];
          const dot = (a, cls2) => `<i class="d ${a === undefined ? "x" : a === it.answer_index ? "y" : "n"} ${cls2}" title="${a === undefined ? "no answer" : "chose " + String.fromCharCode(65 + a)}"></i>`;
          return `<div class="dots">${dot(pre, "pre")}<span class="arrow">→</span>${dot(post, "")}</div>`; }).join("")}
        <div class="mono">${it.gain == null ? "–" : (it.gain > 0 ? "+" : "") + Math.round(it.gain * 100)}</div><div class="mono">${it.discrimination ?? "–"}</div>`).join("")}</div></div>
    ${cls.confusions.length ? `<div class="card"><h2>Where simulated students got stuck</h2>${cls.confusions.map((c) => `<div style="padding:8px 0;border-bottom:1px solid var(--line)">
      <span class="pill">${esc(c.student)} · ${esc(c.level)}</span> <span class="muted small">${esc(sectionName(c.section_id))}</span><div class="quote">“${esc(c.quote)}”</div><div class="small" style="margin-top:4px">${esc(c.why)}</div></div>`).join("")}</div>` : ""}
    ${rep.review ? `<div class="card"><h2>Objective alignment</h2><table class="t"><tr><th>objective part</th><th>taught</th><th>practised</th><th>assessed</th><th>coverage</th></tr>
      ${rep.review.alignment.map((a) => `<tr><td>${esc(a.objective_part)}<div class="small muted">${esc(a.note)}</div></td><td class="mono small">${a.taught_in.map((i) => "§" + (i + 1)).join(" ") || "—"}</td>
        <td class="mono small">${a.practised_in.map((i) => "§" + (i + 1)).join(" ") || "—"}</td><td class="mono small">${a.assessed_by.map((i) => "Q" + (i + 1)).join(" ") || "—"}</td>
        <td><span class="pill ${a.coverage === "full" ? "green" : a.coverage === "partial" ? "amber" : "red"}">${a.coverage}</span></td></tr>`).join("")}</table></div>
    <div class="card"><h2>Rubric</h2>${rep.review.rubric.map((r) => `<div class="rub"><span>${esc(r.criterion.replace(/_/g, " "))}</span><div class="track" title="${esc(r.justification)}"><i class="${r.score <= 2 ? "lo" : ""}" style="width:${r.score * 20}%"></i></div><b>${r.score}</b></div>
      <div class="small muted" style="margin:-4px 0 6px 180px">${esc(r.justification)}</div>`).join("")}</div>` : ""}
    <div class="card"><h2>Pacing</h2>${timeline(rep.measurements.run_sheet)}<table class="t"><tr><th>section</th><th>planned</th><th>reading time</th><th>words</th></tr>
      ${rep.measurements.pacing.map((p) => `<tr><td>${esc(p.title)} <span class="pill">${esc(p.kind)}</span></td><td>${p.planned} min</td><td class="${p.kind !== "activity" && p.reading > p.planned * 1.35 + 0.5 ? "no-tick" : ""}">${p.reading} min</td><td class="muted">${p.words}</td></tr>`).join("")}</table></div>
    ${rep.errors.length ? `<div class="card"><h2>Checks that could not run</h2><ul>${rep.errors.map((e) => `<li class="small">${esc(e)}</li>`).join("")}</ul></div>` : ""}`;
  wireIssues(el);
  $$("[data-rerun]", el).forEach((b) => (b.onclick = () => runSteps([b.dataset.rerun])));
}

// ---------- export ----------
function paneExport(el) {
  const g = S.data.gate;
  el.innerHTML = `<div class="card"><h2>${g.ok ? "Ready to export" : "Before you export"}</h2>
    ${g.ok ? `<p class="muted">Both QC layers checked v${g.version} and no high-severity finding is open.</p>` : `<ul class="gate">${g.reasons.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>
      <p class="muted small">You can still export, but the reason is written into the package's manifest so reviewers can see it.</p>
      <textarea id="ovr" rows="2" placeholder="Reason for exporting anyway (at least 10 characters)" style="width:100%;border:1px solid var(--line);border-radius:10px;padding:10px"></textarea>`}
    <p class="muted small">The zip contains lesson.md, lesson.html, lesson.json, references.md, both QC reports (markdown + json) and manifest.json.</p>
    <button class="btn primary" id="dl" ${S.data.version ? "" : "disabled"}>Download v${S.data.state.current_version} package</button></div>
    ${S.data.state.exports.length ? `<div class="card"><h2>Previous exports</h2><table class="t">${S.data.state.exports.slice().reverse().map((x) => `<tr><td>v${x.version}</td><td class="muted">${new Date(x.at * 1000).toLocaleString()}</td><td class="small">${x.override ? "override: " + esc(x.override) : "passed gate"}</td></tr>`).join("")}</table></div>` : ""}`;
  $("#dl").onclick = async () => {
    const o = $("#ovr")?.value?.trim() || "";
    try {
      const r = await fetch(`/api/lessons/${S.id}/export${o ? "?override=" + encodeURIComponent(o) : ""}`);
      if (!r.ok) { const j = await r.json(); throw new Error(j.detail); }
      const blob = await r.blob(), name = (r.headers.get("content-disposition") || "").match(/filename="(.+)"/)?.[1] || "lesson.zip";
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; a.click(); URL.revokeObjectURL(a.href);
      toast(`Exported ${name}`); await refresh(true);
    } catch (e) { toast(e.message, true); }
  };
}

// ---------- history ----------
function paneHistory(el) {
  const vs = S.data.versions.slice().reverse();
  el.innerHTML = `<div class="card"><h2>Versions</h2><p class="muted small">Every save, generation and applied fix is a new version. Nothing is overwritten.</p>
    <table class="t">${vs.map((v) => `<tr><td class="mono">v${v.version}</td><td><span class="pill ${v.author === "ai" ? "" : "solid"}">${esc(v.author)}</span></td><td>${esc(v.note)}</td>
      <td class="muted small">${new Date(v.created_at * 1000).toLocaleString()}</td>
      <td>${v.version === S.data.state.current_version ? '<span class="pill green">current</span>' : `<button class="btn sm" data-restore="${v.version}">Restore</button>`}</td></tr>`).join("") || "<tr><td class='muted'>No versions yet.</td></tr>"}</table></div>`;
  $$("[data-restore]", el).forEach((b) => (b.onclick = async () => {
    try { const r = await api(`/api/lessons/${S.id}/versions/${b.dataset.restore}/restore`, { method: "POST" }); toast(`Restored as v${r.version}`); await refresh(true); }
    catch (e) { toast(e.message, true); }
  }));
}

function ago(t) {
  const s = Date.now() / 1000 - t;
  return s < 60 ? "just now" : s < 3600 ? `${Math.floor(s / 60)} min ago` : s < 86400 ? `${Math.floor(s / 3600)} h ago` : new Date(t * 1000).toLocaleDateString();
}
window.addEventListener("beforeunload", (e) => { if (S.dirty) { e.preventDefault(); e.returnValue = ""; } });
health().then(route);
