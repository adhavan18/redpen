// drives the real redpen ui in edge and records each scene as its own video, plus a cursor log
// (every move / click with a timestamp) that the remotion edit uses for cursor-following zooms.
// usage: node record.mjs <scene|all>   (server must be running on :8000)
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const BASE = "http://localhost:8000";
const OUT = path.resolve("public/rec");
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const W = 1920, H = 1080, ZOOM = 1.25; // page zoom so the ui reads well at 1080p
const L = JSON.parse(fs.readFileSync("lessons.json", "utf8")); // { http, sql } lesson ids
fs.mkdirSync(OUT, { recursive: true });

const CURSOR = `
(() => {
  const boot = () => {
    if (document.getElementById("__c")) return;
    document.documentElement.style.zoom = "${ZOOM}";
    const c = document.createElement("div"); c.id = "__c";
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2l16 9.5-7 1.6-3.6 6.6z" fill="#1d1d1f" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, { position: "fixed", left: 0, top: 0, zIndex: 2147483647, pointerEvents: "none",
      transform: "translate(-100px,-100px)", filter: "drop-shadow(0 2px 4px rgba(0,0,0,.35))" });
    document.body.appendChild(c);
    const z = ${ZOOM};
    addEventListener("mousemove", (e) => { c.style.transform = "translate(" + e.clientX + "px," + e.clientY + "px)"; }, true);
    addEventListener("mousedown", (e) => {
      const r = document.createElement("div");
      Object.assign(r.style, { position: "fixed", left: e.clientX - 18 + "px", top: e.clientY - 18 + "px", width: "36px", height: "36px",
        borderRadius: "50%", background: "rgba(239,56,55,.35)", zIndex: 2147483646, pointerEvents: "none",
        transition: "transform .45s cubic-bezier(.2,.8,.2,1), opacity .45s", transform: "scale(.3)" });
      document.body.appendChild(r); requestAnimationFrame(() => { r.style.transform = "scale(1.6)"; r.style.opacity = "0"; });
      setTimeout(() => r.remove(), 600);
    }, true);
  };
  if (document.body) boot(); else addEventListener("DOMContentLoaded", boot);
})();`;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function scene(name, fn) {
  console.log("recording", name);
  const browser = await chromium.launch({ executablePath: EDGE, headless: true });
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, recordVideo: { dir: OUT, size: { width: W, height: H } },
                                         acceptDownloads: true });
  await ctx.addInitScript(CURSOR);
  const page = await ctx.newPage();
  const t0 = Date.now();
  const events = [];
  let mx = W / 2, my = H / 2;
  const log = (type, x, y, extra = {}) => events.push({ t: (Date.now() - t0) / 1000, type, x: Math.round(x), y: Math.round(y), ...extra });

  const h = {
    page, sleep, log,
    async go(url) { await page.goto(BASE + url); await page.waitForLoadState("networkidle").catch(() => {}); await sleep(900); },
    async move(x, y, ms = 650) {
      const steps = Math.max(8, Math.round(ms / 16));
      for (let i = 1; i <= steps; i++) {
        const k = i / steps, e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; // ease in-out cubic
        await page.mouse.move(mx + (x - mx) * e, my + (y - my) * e);
        await sleep(ms / steps);
      }
      mx = x; my = y; log("move", x, y);
    },
    async box(sel) {
      const loc = typeof sel === "string" ? page.locator(sel).first() : sel;
      await loc.scrollIntoViewIfNeeded({ timeout: 4000 }).catch(() => {});
      await sleep(250);
      return loc.boundingBox({ timeout: 4000 }).catch(() => null);
    },
    async click(sel, { zoom = 1.8, hold = 1.2, ms = 650 } = {}) {
      const b = await h.box(sel);
      if (!b) throw new Error("not found: " + sel);
      const x = b.x + b.width / 2, y = b.y + b.height / 2;
      await h.move(x, y, ms);
      log("click", x, y, { zoom, hold });
      await page.mouse.down(); await sleep(70); await page.mouse.up();
      await sleep(350);
    },
    async type(sel, text, delay = 32) { await h.click(sel, { zoom: 1.6 }); await page.keyboard.type(text, { delay }); log("typed", mx, my); },
    async focus(sel, { zoom = 1.6, hold = 2.2 } = {}) { // zoom on an element without clicking it
      const b = await h.box(sel); if (!b) return;
      const x = b.x + b.width / 2, y = b.y + Math.min(b.height / 2, 260);
      await h.move(x, y, 700); log("focus", x, y, { zoom, hold }); await sleep(hold * 1000);
    },
    async scroll(dy, ms = 1400) {
      const steps = Math.round(ms / 16);
      for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, dy / steps); await sleep(16); }
      log("scroll", mx, my, { dy }); await sleep(300);
    },
  };
  try { await fn(h); } catch (e) { console.error(name, "failed:", e.message); }
  await sleep(800);
  const video = page.video();
  await ctx.close(); await browser.close();
  const file = path.join(OUT, `${name}.webm`);
  if (fs.existsSync(file)) fs.unlinkSync(file);
  fs.renameSync(await video.path(), file);
  fs.writeFileSync(path.join(OUT, `${name}.json`), JSON.stringify({ duration: (Date.now() - t0) / 1000, zoom: ZOOM, events }, null, 1));
  console.log(" ->", file);
}

const SCENES = {
  // official sample input typed in, then the live research log streaming
  async create(h) {
    await h.go("/");
    await h.sleep(800);
    await h.click("button[type=submit]", { zoom: 1.5 });  // empty submit: shows validation
    await h.focus("#f-err", { zoom: 2.0, hold: 1.6 });
    await h.type("#f-title", "HTTP Requests and Responses");
    await h.type("#f-obj", "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories.", 22);
    await h.click("button[type=submit]", { zoom: 1.6 });
    await h.page.waitForURL(/#\/l\//);
    fs.writeFileSync("live-lesson.txt", h.page.url().split("/l/")[1].split("/")[0]);
    await h.sleep(1500);
    await h.focus(".steps", { zoom: 1.35, hold: 3 });
    await h.focus("#log", { zoom: 1.7, hold: 6 });
    // let research run (the edit speeds this up); stop once the draft starts
    const deadline = Date.now() + 4 * 60 * 1000;
    while (Date.now() < deadline) {
      const st = await h.page.evaluate(() => S.data && S.data.state.steps);
      if (st && ["done", "failed"].includes(st.research.status)) break;
      await h.sleep(2000);
    }
    await h.sleep(5000);
    await h.focus(".steps", { zoom: 1.4, hold: 2.5 });
  },

  // a real failure (free-tier rate limit) and its retry
  async retry(h) {
    await h.go(`/#/l/${L.http}/qc_factual`);
    await h.focus(".step.failed", { zoom: 2.2, hold: 3.2 });
    await h.click('.step.failed [data-run]', { zoom: 2.2, hold: 1.2 });
    await h.sleep(1500);
    await h.focus("#log", { zoom: 1.6, hold: 4 });
    const deadline = Date.now() + 7 * 60 * 1000;
    while (Date.now() < deadline) {
      const st = await h.page.evaluate(() => S.data && S.data.state.steps.qc_factual.status);
      if (st === "done" || st === "failed") break;
      await h.sleep(3000);
    }
    await h.sleep(2500);
    await h.focus(".steps", { zoom: 1.5, hold: 2.5 });
    await h.focus(".stats", { zoom: 1.4, hold: 2.5 });
  },

  async lesson(h) {
    await h.go(`/#/l/${L.http}/lesson`);
    await h.focus(".lhead .clock", { zoom: 2.2, hold: 1.6 });
    await h.focus(".timeline", { zoom: 1.7, hold: 2.4 });
    await h.scroll(500);
    // click a claim that sits on one line (the centre of a wrapped inline box can fall between lines)
    await h.page.evaluate(() => {
      const m = [...document.querySelectorAll("mark.claim.supported")].find((x) => x.getClientRects().length === 1 &&
        x.getBoundingClientRect().top > 200 && x.textContent.length > 30);
      if (m) m.setAttribute("data-pick", "1");
    });
    await h.click("mark[data-pick]", { zoom: 1.9, hold: 2.8 });
    await h.focus("#pop", { zoom: 1.9, hold: 3.2 });
    await h.page.mouse.click(30, 300); await h.sleep(300);
    await h.click(h.page.locator("a.cite.A").first(), { zoom: 2.0, hold: 2.4 });
    await h.sleep(1600);
    await h.page.mouse.click(30, 300);
    await h.click("#heat", { zoom: 2.2, hold: 1 }); await h.sleep(900);
    await h.click("#heat", { zoom: 2.2, hold: 1 }); await h.sleep(600);
    const badge = h.page.locator(".runbadge").first();
    if (await badge.count()) { await h.focus(badge, { zoom: 1.7, hold: 3 }); }
    const vid = h.page.locator(".vid").first();
    if (await vid.count()) { await h.focus(vid, { zoom: 1.6, hold: 2.6 }); }
    await h.focus(".quizq", { zoom: 1.5, hold: 2 });
  },

  async research(h) {
    await h.go(`/#/l/${L.http}/research`);
    await h.focus(".stats", { zoom: 1.5, hold: 2.6 });
    await h.scroll(420);
    await h.focus("table.t", { zoom: 1.45, hold: 3 });
    await h.focus(".thumbs", { zoom: 1.4, hold: 1.5 });
    await h.focus(".seg-row .pill", { zoom: 2.2, hold: 2.4 });
    await h.scroll(700);
    await h.sleep(1500);
  },

  async qc1(h) {
    await h.go(`/#/l/${L.http}/qc_factual`);
    await h.focus(".stats", { zoom: 1.35, hold: 3.4 });
    await h.focus(".stat.hero-red", { zoom: 2.3, hold: 1.8 });
    const claims = h.page.locator("h2", { hasText: "Every claim" });
    await h.focus(claims, { zoom: 1.4, hold: 0.6 });
    await h.scroll(380);
    await h.focus(h.page.locator(".ok-tick").first(), { zoom: 2.1, hold: 2.6 });
    const code = h.page.locator("h2", { hasText: "Code examples" });
    if (await code.count()) { await h.scroll(0); await h.focus(code, { zoom: 1.3, hold: 0.4 }); await h.scroll(250); await h.focus(code, { zoom: 1.45, hold: 3.2 }); }
    const probes = h.page.locator("h2", { hasText: "Live HTTP" });
    if (await probes.count()) { await h.focus(probes, { zoom: 1.3, hold: 0.4 }); await h.scroll(200); await h.focus(probes, { zoom: 1.55, hold: 3.6 }); }
  },

  async qc2(h) {
    await h.go(`/#/l/${L.http}/qc_instructional`);
    await h.focus(".stats", { zoom: 1.35, hold: 2.6 });
    await h.focus(".stat.hero-red", { zoom: 2.3, hold: 2.2 });
    const cls = h.page.locator("h2", { hasText: "Simulated classroom" });
    await h.focus(cls, { zoom: 1.2, hold: 0.4 });
    await h.scroll(300);
    await h.focus(".class", { zoom: 1.45, hold: 4.2 });
    const rub = h.page.locator("h2", { hasText: "Rubric" });
    if (await rub.count()) { await h.focus(rub, { zoom: 1.2, hold: 0.3 }); await h.scroll(200); await h.focus(rub, { zoom: 1.4, hold: 2.6 }); }
    const al = h.page.locator("h2", { hasText: "Objective alignment" });
    if (await al.count()) { await h.focus(al, { zoom: 1.4, hold: 2.4 }); }
  },

  // apply qc recommendations on the sql lesson
  async fix(h) {
    await h.go(`/#/l/${L.sql}/qc_instructional`);
    await h.sleep(600);
    const boxes = h.page.locator('.issue input[type=checkbox]:not([disabled]):not([title^="whole"])');
    const n = Math.min(await boxes.count(), 2);
    for (let i = 0; i < n; i++) await h.click(boxes.nth(i), { zoom: 1.8, hold: 1 });
    await h.focus("#ibar", { zoom: 1.6, hold: 1.2 });
    await h.click("#i-fix", { zoom: 1.8 });
    await h.page.waitForSelector("#accept", { timeout: 240000 });
    await h.sleep(800);
    await h.focus(".diff", { zoom: 1.4, hold: 3.5 });
    await h.page.mouse.move(960, 700); await h.page.mouse.wheel(0, 400); await h.sleep(1500);
    await h.click("#accept", { zoom: 1.8 });
    await h.sleep(2500);
    await h.focus(".steps", { zoom: 1.4, hold: 2.4 });
  },

  async edit(h) {
    await h.go(`/#/l/${L.sql}/lesson`);
    await h.click('[data-m="edit"]', { zoom: 1.8 });
    await h.sleep(600);
    const ta = h.page.locator(".ed textarea").first();
    await h.click(ta, { zoom: 1.6 });
    await h.page.keyboard.press("Control+End");
    await h.page.keyboard.type("\n\nQuick check: before reading on, write down which rows you think a LEFT JOIN keeps.", { delay: 28 });
    h.log("typed", 960, 400);
    await h.focus(".savebar", { zoom: 1.7, hold: 1.4 });
    await h.click("#save", { zoom: 1.9 });
    await h.sleep(1800);
    await h.click('.seg button[data-tab="history"]', { zoom: 1.6 });
    await h.focus("table.t", { zoom: 1.5, hold: 3 });
  },

  async export(h) {
    await h.go(`/#/l/${L.http}/export`);
    await h.focus(".card", { zoom: 1.5, hold: 2.4 });
    const ovr = h.page.locator("#ovr");
    if (await ovr.count()) await h.type("#ovr", "Reviewed the remaining findings by hand; publishing for the pilot class.", 18);
    const dl = h.page.waitForEvent("download").catch(() => null);
    await h.click("#dl", { zoom: 1.8 });
    const d = await dl; if (d) await d.saveAs(path.join(OUT, "export.zip"));
    await h.sleep(2200);
  },
};

const want = process.argv[2] || "all";
for (const [name, fn] of Object.entries(SCENES)) {
  if (want === "all" || want.split(",").includes(name)) await scene(name, fn);
}
