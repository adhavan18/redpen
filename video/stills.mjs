import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import path from "node:path";
const frames = process.argv.slice(2).map(Number);
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.jsx") });
const composition = await selectComposition({ serveUrl, id: "Launch" });
for (const f of frames) {
  await renderStill({ composition, serveUrl, output: `shots/L${String(f).padStart(5, "0")}.jpg`, frame: f, imageFormat: "jpeg", jpegQuality: 70, scale: 0.5 });
  console.log("frame", f);
}
