import { chromium } from "playwright-core";
const b = await chromium.launch({ executablePath: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", headless: true });
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
const L = { http: "http-requests-and-responses-4b5ba5", sql: "sql-joins-3db3c1" };
for (const [k, id] of Object.entries(L)) for (const tab of ["lesson", "research", "qc_factual", "qc_instructional", "export", "history"]) {
  await p.goto(`http://localhost:8000/#/l/${id}/${tab}`); await p.evaluate(() => document.documentElement.style.zoom = "1.25");
  await p.waitForTimeout(1500);
  await p.screenshot({ path: `shots/${k}-${tab}.png`, fullPage: true });
}
await b.close();
