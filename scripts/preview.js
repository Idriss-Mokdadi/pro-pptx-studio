// preview.js — show the user a deck's cover (and one content slide) in several styles before building it. MIT License.
//
//   node preview.js brief.json [outdir]
//   brief = { title, subtitle?, kicker?, meta?: [..], topic?: "5g security ai", lang?: "fr",
//             styles?: ["nebula", ...],   // omit to auto-pick by topic and taste
//             count?: 6, sample?: "agenda" | "cards" | "stats" | "bento", items?: [..], logos?: [paths] }
// Writes <outdir>/styles-sheet.jpg (one row per style: cover + sample) and <outdir>/choices.json, prints both paths.
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");
const { Deck } = require("./deckkit.js");
const sharp = require("sharp");

const ROOT = require("./dataroot.js").dataRoot();
function allStyles() { return fs.readdirSync(path.join(ROOT, "styles")).filter((f) => f.endsWith(".json")).map((f) => JSON.parse(fs.readFileSync(path.join(ROOT, "styles", f), "utf8"))); }

function pick(brief) {
  const all = allStyles();
  if (brief.styles && brief.styles.length) return brief.styles.map((id) => all.find((s) => s.id === id) || (() => { throw new Error(`unknown style ${id}`); })());
  const words = `${brief.topic || ""} ${brief.title || ""} ${brief.kind || ""}`.toLowerCase();
  const scored = all.filter((s) => s.group === "house").map((s) => {
    const hits = (s.tags || []).filter((t) => words.includes(t)).length;
    return { s, score: hits * 40 + (s.weight || 0) * 0.6 };
  }).sort((a, b) => b.score - a.score);
  const n = brief.count || 6, out = [], seenBg = new Set();
  for (const { s } of scored) { const key = s.background.recipe; if (seenBg.has(key) && out.length < n - 1) continue; out.push(s); seenBg.add(key); if (out.length >= n) break; }
  if (!out.some((s) => s.mode === "light")) { const light = scored.find(({ s }) => s.mode === "light"); if (light) out[out.length - 1] = light.s; }
  return out;
}

function render(pptx, outdir) {
  return new Promise((res, rej) => {
    const p = spawn("python3", [path.join(__dirname, "render.py"), pptx, outdir, "--dpi", "60", "--cols", "2"], { stdio: ["ignore", "pipe", "pipe"] });
    let o = ""; p.stdout.on("data", (d) => (o += d)); p.on("close", (code) => (code === 0 ? res(o.trim().split("\n").filter((l) => /slide-\d+\.jpg$/.test(l))) : rej(new Error("render failed"))));
  });
}

async function main() {
  const brief = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const outdir = path.resolve(process.argv[3] || "style-preview"); fs.mkdirSync(outdir, { recursive: true });
  const styles = pick(brief);
  const letters = [..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"].concat([..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"].map((x) => "A" + x), [..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"].map((x) => "B" + x));
  const limit = async (fns, n) => { const out = []; let i = 0; await Promise.all([...Array(Math.min(n, fns.length))].map(async () => { while (i < fns.length) { const k = i++; out[k] = await fns[k](); } })); return out; };
  const jobs = styles.map((st, i) => async () => {
    const d = new Deck({ style: st.id, motion: "none", embedFonts: false, title: brief.title, topic: brief.topic, lang: brief.lang, footer: brief.footer || brief.title, logos: brief.logos, hero: brief.hero });
    d.cover({ kicker: brief.kicker, title: brief.title, subtitle: brief.subtitle, meta: brief.meta });
    const items = brief.items || ["Context", "Problem", "Solution", "Results", "Next steps"];
    const kind = brief.sample || "agenda";
    if (kind === "cards") d.cards({ title: brief.sampleTitle || "Three ideas, one per card", items: items.slice(0, 3).map((t, k) => ({ icon: ["target", "bolt", "chart"][k], head: typeof t === "string" ? t : t.head, text: typeof t === "string" ? "Short supporting sentence for the layout preview." : t.text })) });
    else if (kind === "stats") d.stats({ title: brief.sampleTitle || "Key numbers", items: (brief.stats || [{ value: "[value]", label: "Metric" }, { value: "[value]", label: "Metric" }, { value: "[value]", label: "Metric" }]) });
    else if (kind === "bento") d.bento({ title: brief.sampleTitle || brief.title, items: [{ type: "hero", title: brief.title }, { type: "stat", value: "[value]", label: "key metric" }, { type: "feature", icon: "bolt", head: items[0] }, { type: "feature", icon: "shield", head: items[1] }, { type: "chips", head: "Stack", items: items.slice(2, 5).map(String) }] });
    else if (kind !== "none") d.agenda({ items: items.map((t) => (typeof t === "string" ? t : t.head)) });
    const f = path.join(outdir, `${letters[i]}-${st.id}.pptx`);
    await d.save(f);
    const imgs = await render(f, path.join(outdir, `${letters[i]}-${st.id}`));
    return { letter: letters[i], id: st.id, name: st.name, mode: st.mode, source: st.source || null, imgs };
  });
  const origLog = console.log; console.log = () => {};
  const res = await limit(jobs, 6); console.log = origLog;
  const coversOnly = (brief.sample || "agenda") === "none";
  const tw = coversOnly ? 560 : 640, th = coversOnly ? 315 : 360, pad = 14, labelH = 46, cols = coversOnly ? 3 : 2;
  const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;");
  const cells = [];
  for (const r of res) {
    const ims = await Promise.all(r.imgs.slice(0, coversOnly ? 1 : 2).map((p) => sharp(p).resize(tw, th).toBuffer()));
    const lw = coversOnly ? tw : tw * 2 + pad;
    const label = Buffer.from(`<svg width="${lw}" height="${labelH}"><text x="0" y="32" font-family="Sora, Inter, sans-serif" font-size="${coversOnly ? 22 : 26}" font-weight="700" fill="#ffffff">${r.letter} · ${esc(r.name)}</text><text x="${lw}" y="32" text-anchor="end" font-family="Inter, sans-serif" font-size="${coversOnly ? 15 : 18}" fill="#c8c8d0">${esc(r.id)} · ${r.mode}</text></svg>`);
    cells.push({ label, ims });
  }
  const perRow = coversOnly ? cols : 1, cellW = coversOnly ? tw : tw * 2 + pad, cellH = th + labelH;
  const rowsN = Math.ceil(cells.length / perRow);
  const W = perRow * cellW + (perRow + 1) * pad, H = rowsN * (cellH + pad) + pad;
  const comp = []; cells.forEach((cl, i) => { const x = pad + (i % perRow) * (cellW + pad), y = pad + Math.floor(i / perRow) * (cellH + pad); comp.push({ input: cl.label, left: x, top: y }); cl.ims.forEach((im, j) => comp.push({ input: im, left: x + j * (tw + pad), top: y + labelH })); });
  const sheet = path.join(outdir, "styles-sheet.jpg");
  await sharp({ create: { width: W, height: H, channels: 3, background: "#1b1b22" } }).composite(comp).jpeg({ quality: 86 }).toFile(sheet);
  const choices = res.map(({ letter, id, name, mode, source }) => ({ letter, id, name, mode, source }));
  fs.writeFileSync(path.join(outdir, "choices.json"), JSON.stringify(choices, null, 2));
  console.log(sheet); console.log(path.join(outdir, "choices.json")); console.log(JSON.stringify(choices));
}
main().catch((e) => { console.error(e); process.exit(1); });
