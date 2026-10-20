// banner_preview.js — render one banner in several styles side by side so the user can choose. MIT License.
//   node banner_preview.js brief.json [outdir]
//   brief = Banner options (size, layout, title, …) + optional styles: [ids] (default: 4 picks by topic/taste) and topic
const fs = require("fs"), path = require("path"), sharp = require("sharp");
const { Banner } = require("./banner.js");
(async () => {
  const brief = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const out = path.resolve(process.argv[3] || "banner-preview"); fs.mkdirSync(out, { recursive: true });
  const DIR = path.join(require("./dataroot.js").dataRoot(), "styles");
  const all = fs.readdirSync(DIR).map((f) => JSON.parse(fs.readFileSync(path.join(DIR, f), "utf8")));
  const q = `${brief.topic || ""} ${brief.title || ""}`.toLowerCase();
  const ids = brief.styles || all.filter((s) => s.group !== "system").map((s) => ({ id: s.id, sc: (s.tags || []).filter((t) => q.includes(t)).length * 40 + (s.weight || 0) * 0.6, mode: s.mode })).sort((a, b) => b.sc - a.sc).slice(0, brief.count || 4).map((x) => x.id);
  const log = console.log; console.log = () => {};
  const res = [];
  for (const [i, id] of ids.entries()) { const { styles, count, topic, ...o } = brief; const r = await new Banner({ ...o, style: id }).save(path.join(out, `${String.fromCharCode(65 + i)}-${id}`)); res.push({ letter: String.fromCharCode(65 + i), id, png: r.png }); }
  console.log = log;
  const meta = await sharp(res[0].png).metadata(); const tall = meta.height > meta.width;
  const tw = tall ? 420 : 760, th = Math.round(tw * meta.height / meta.width), pad = 14, lab = 40, cols = tall ? 4 : 2;
  const comp = []; for (const [i, r] of res.entries()) { const x = pad + (i % cols) * (tw + pad), y = pad + Math.floor(i / cols) * (th + lab + pad);
    comp.push({ input: Buffer.from(`<svg width="${tw}" height="${lab}"><text x="0" y="28" font-family="Sora, Inter, sans-serif" font-size="22" font-weight="700" fill="#fff">${r.letter} · ${r.id}</text></svg>`), left: x, top: y }, { input: await sharp(r.png).resize(tw, th).toBuffer(), left: x, top: y + lab }); }
  const rows = Math.ceil(res.length / cols); const sheet = path.join(out, "banners-sheet.jpg");
  await sharp({ create: { width: cols * (tw + pad) + pad, height: rows * (th + lab + pad) + pad, channels: 3, background: "#1b1b22" } }).composite(comp).jpeg({ quality: 86 }).toFile(sheet);
  console.log(sheet); console.log(JSON.stringify(res.map(({ letter, id }) => ({ letter, id }))));
})().catch((e) => { console.error(e); process.exit(1); });
