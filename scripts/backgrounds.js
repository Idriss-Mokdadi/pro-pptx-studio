// backgrounds.js — procedural backgrounds and hero art (SVG rendered with sharp). MIT License.
// One background image per deck: every slide uses the same picture, so the deck reads as one object.
//
//   const bg = require("./backgrounds.js");
//   const buf = await bg.background({ recipe: "aurora", ...params }, palette, { w: 2400, h: 1350 });   // JPEG Buffer
//   const art = await bg.hero("orbs", palette, { w: 1200, h: 1200 });                                // PNG Buffer (transparent)
//
// palette = { bg, bg2, primary, accent, accent2, text, muted } (hex without #)

const sharp = require("sharp");

function rng(seed) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
const h = (c) => "#" + String(c).replace("#", "");
function mix(a, b, t) { const p = (x) => [0, 2, 4].map((i) => parseInt(String(x).replace("#", "").slice(i, i + 2), 16)); const [x, y] = [p(a), p(b)]; return x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, "0")).join(""); }

const grain = (w, h, op = 0.05) => `<filter id="gr" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 ${op}"/></feComponentTransfer></filter><rect width="${w}" height="${h}" filter="url(#gr)"/>`;
const blur = (id, sd) => `<filter id="${id}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="${sd}"/></filter>`;
const vignette = (w, h, color, op) => `<radialGradient id="vg" cx="50%" cy="50%" r="75%"><stop offset="55%" stop-color="${h_(color)}" stop-opacity="0"/><stop offset="100%" stop-color="${h_(color)}" stop-opacity="${op}"/></radialGradient><rect width="${w}" height="${h}" fill="url(#vg)"/>`;
function h_(c) { return h(c); }

function blobs(list, w, H, sd) {
  return `<g filter="url(#bl)">${list.map((b) => `<ellipse cx="${b.x * w}" cy="${b.y * H}" rx="${b.rx * w}" ry="${(b.ry || b.rx) * w}" fill="${h(b.c)}" fill-opacity="${b.o ?? 0.6}"/>`).join("")}</g>${""}`;
}

const RECIPES = {
  // dark base, colored light from corners (aurora / nebula)
  aurora(p, w, H, o) {
    const g = o.glows || [{ x: 1.0, y: 1.05, rx: 0.45, c: p.primary, o: 0.55 }, { x: 0.82, y: 0.95, rx: 0.3, c: p.accent, o: 0.4 }, { x: -0.05, y: -0.1, rx: 0.25, c: p.accent2 || p.accent, o: 0.18 }];
    return base(p, w, H, o) + `<defs>${blur("bl", w * (o.blur || 0.09))}</defs>` + blobs(g, w, H) + `<defs>${vignettedef(p.bg, 0.55)}</defs><rect width="${w}" height="${H}" fill="url(#vg)"/>`;
  },
  // saturated blurred blobs behind translucent glass cards
  glassblobs(p, w, H, o) {
    const g = o.glows || [{ x: 0.12, y: 0.2, rx: 0.22, c: p.primary, o: 0.75 }, { x: 0.9, y: 0.82, rx: 0.26, c: p.accent, o: 0.65 }, { x: 0.62, y: 0.05, rx: 0.14, c: p.accent2 || p.primary, o: 0.45 }, { x: 0.35, y: 1.0, rx: 0.16, c: p.accent2 || p.accent, o: 0.35 }];
    return base(p, w, H, o) + `<defs>${blur("bl", w * 0.06)}</defs>` + blobs(g, w, H);
  },
  // light base with soft blurred color clouds (light competition-deck look)
  meshlight(p, w, H, o) {
    const g = o.glows || [{ x: 1.0, y: -0.02, rx: 0.22, ry: 0.2, c: p.accent, o: 0.95 }, { x: -0.02, y: 1.02, rx: 0.2, ry: 0.18, c: p.accent, o: 0.9 }, { x: 0.12, y: 0.16, rx: 0.3, ry: 0.11, c: p.primary, o: 0.6 }, { x: 0.9, y: 0.92, rx: 0.3, ry: 0.12, c: p.primary, o: 0.65 }, { x: 0.62, y: 0.42, rx: 0.16, ry: 0.06, c: p.primary, o: 0.18 }];
    return base(p, w, H, o) + `<defs>${blur("bl", w * 0.05)}</defs>` + blobs(g, w, H);
  },
  // constellation of nodes and links (telecom / network)
  network(p, w, H, o) {
    const r = rng(o.seed || 7); const pts = []; const n = o.nodes || 46;
    for (let i = 0; i < n; i++) { const t = r(); pts.push([w * (0.55 + 0.47 * Math.pow(r(), 0.8)), H * (t * 1.05 - 0.02)]); }
    for (let i = 0; i < 14; i++) pts.push([w * (r() * 0.5), H * (r() < 0.5 ? r() * 0.12 : 0.9 + r() * 0.1)]);
    let lines = "", dots = "";
    pts.forEach((a, i) => pts.forEach((b, j) => { if (j <= i) return; const d = Math.hypot(a[0] - b[0], a[1] - b[1]); if (d < w * 0.11) lines += `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke-opacity="${(0.5 * (1 - d / (w * 0.11))).toFixed(2)}"/>`; }));
    pts.forEach(([x, y], i) => { const big = r() < 0.18; dots += `<circle cx="${x}" cy="${y}" r="${big ? w * 0.0032 : w * 0.0016}" fill="${h(i % 5 ? p.primary : p.accent)}" fill-opacity="${big ? 0.95 : 0.7}"/>${big ? `<circle cx="${x}" cy="${y}" r="${w * 0.012}" fill="${h(p.primary)}" fill-opacity="0.12"/>` : ""}`; });
    return RECIPES.aurora(p, w, H, { ...o, glows: o.glows || [{ x: 0.95, y: 0.9, rx: 0.35, c: p.primary, o: 0.35 }, { x: 0.1, y: -0.1, rx: 0.2, c: p.accent, o: 0.12 }] }) + `<g stroke="${h(p.primary)}" stroke-width="${w * 0.0006}">${lines}</g>${dots}`;
  },
  // bundles of thin flowing lines (signal waves)
  waves(p, w, H, o) {
    const bundle = (y0, amp, col, n, phase, op) => { let s = ""; for (let i = 0; i < n; i++) { const t = i / n, y = y0 + t * H * 0.18; s += `<path d="M ${-w * 0.05} ${y} C ${w * 0.25} ${y - amp * (1 - t) + phase}, ${w * 0.55} ${y + amp * (0.6 + t)}, ${w * 1.05} ${y - amp * 0.4 * t}" fill="none" stroke="${h(col)}" stroke-opacity="${(op * (0.35 + 0.65 * Math.sin(Math.PI * t))).toFixed(3)}" stroke-width="${w * 0.0007}"/>`; } return s; };
    return RECIPES.aurora(p, w, H, { ...o, glows: o.glows || [{ x: 0.9, y: 0.95, rx: 0.3, c: p.accent, o: 0.3 }] }) + bundle(H * 0.68, H * 0.32, p.accent, 60, 0, 0.9) + bundle(H * 0.74, H * 0.22, p.primary, 40, H * 0.1, 0.7);
  },
  // falling data columns + center glow (holographic AI)
  binary(p, w, H, o) {
    const r = rng(o.seed || 3); let s = ""; const cw = w / 120;
    for (let c = 0; c < 120; c++) { if (r() < 0.45) continue; const x = c * cw + cw * 0.3; const len = 3 + Math.floor(r() * 18), y0 = r() * H; for (let k = 0; k < len; k++) { const y = (y0 + k * cw * 1.6) % H; const op = (0.05 + 0.25 * (k / len)) * (x > w * 0.45 ? 1 : 0.5); s += `<rect x="${x}" y="${y}" width="${cw * 0.35}" height="${cw * (r() < 0.5 ? 0.9 : 0.35)}" rx="${cw * 0.1}" fill="${h(p.primary)}" fill-opacity="${op.toFixed(3)}"/>`; } }
    return RECIPES.aurora(p, w, H, { ...o, glows: o.glows || [{ x: 0.5, y: 0.5, rx: 0.32, ry: 0.2, c: p.primary, o: 0.22 }, { x: 1.0, y: 0.0, rx: 0.25, c: p.accent, o: 0.35 }, { x: 0.0, y: 1.0, rx: 0.25, c: p.accent2 || p.accent, o: 0.3 }] }) + s;
  },
  // hexagon mesh + angled glass shards (cyber / cloud security)
  hex(p, w, H, o) {
    const R = w * 0.028, hw = Math.sqrt(3) * R; let s = "";
    for (let row = -1; row < H / (1.5 * R) + 1; row++) for (let col = -1; col < w / hw + 1; col++) {
      const cx = col * hw + (row % 2 ? hw / 2 : 0), cy = row * 1.5 * R; const fx = cx / w, fy = cy / H;
      const op = Math.max(0, 0.45 * (fx - 0.3) * (1.2 - Math.abs(fy - 0.5)));
      if (op < 0.01) continue; const pts = [...Array(6)].map((_, k) => { const a = Math.PI / 3 * k + Math.PI / 6; return `${cx + R * Math.cos(a)},${cy + R * Math.sin(a)}`; }).join(" ");
      s += `<polygon points="${pts}" fill="none" stroke="${h(p.primary)}" stroke-opacity="${op.toFixed(3)}" stroke-width="${w * 0.0006}"/>`; }
    const shard = (pts, c, op) => `<polygon points="${pts.map(([x, y]) => `${x * w},${y * H}`).join(" ")}" fill="${h(c)}" fill-opacity="${op}"/>`;
    return RECIPES.aurora(p, w, H, { ...o, glows: o.glows || [{ x: 0.95, y: 0.15, rx: 0.3, c: p.primary, o: 0.35 }, { x: 0.05, y: 1.0, rx: 0.25, c: p.accent, o: 0.2 }] }) + s +
      shard([[0.82, 0], [1, 0], [1, 0.42]], p.primary, 0.22) + shard([[0.9, 1], [1, 0.62], [1, 1]], p.accent, 0.16) + shard([[0, 0.78], [0.12, 1], [0, 1]], p.primary, 0.14);
  },
  // PCB traces in one corner (IoT / embedded)
  circuit(p, w, H, o) {
    const r = rng(o.seed || 11); let s = "";
    for (let i = 0; i < 34; i++) { let x = w * (0.6 + r() * 0.42), y = H * (r() * 1.0); let d = `M${x} ${y}`; for (let k = 0; k < 4; k++) { if (k % 2 === 0) x += (r() - 0.3) * w * 0.12; else y += (r() - 0.5) * H * 0.2; d += ` L${x} ${y}`; }
      s += `<path d="${d}" fill="none" stroke="${h(i % 4 ? p.primary : p.accent)}" stroke-opacity="0.32" stroke-width="${w * 0.0012}" stroke-linejoin="round"/><circle cx="${x}" cy="${y}" r="${w * 0.0028}" fill="none" stroke="${h(p.primary)}" stroke-opacity="0.6" stroke-width="${w * 0.001}"/>`; }
    return RECIPES.aurora(p, w, H, { ...o, glows: o.glows || [{ x: 0.95, y: 0.5, rx: 0.3, c: p.primary, o: 0.25 }] }) + s;
  },
  // perspective grid floor with horizon glow
  gridfloor(p, w, H, o) {
    const hz = H * 0.66; let s = "";
    for (let i = 0; i < 16; i++) { const t = Math.pow(i / 16, 2.2); const y = hz + (H - hz) * t; s += `<line x1="0" y1="${y}" x2="${w}" y2="${y}" stroke-opacity="${(0.08 + 0.4 * t).toFixed(2)}"/>`; }
    for (let i = -20; i <= 20; i++) s += `<line x1="${w / 2 + i * w * 0.02}" y1="${hz}" x2="${w / 2 + i * w * 0.16}" y2="${H}" stroke-opacity="0.35"/>`;
    return RECIPES.aurora(p, w, H, { ...o, glows: o.glows || [{ x: 0.5, y: 0.66, rx: 0.45, ry: 0.06, c: p.accent, o: 0.55 }, { x: 0.5, y: 0.2, rx: 0.3, c: p.primary, o: 0.12 }] }) + `<g stroke="${h(p.primary)}" stroke-width="${w * 0.0008}">${s}</g>`;
  },
  // warm dark base with a diagonal light sweep
  sweep(p, w, H, o) {
    return base(p, w, H, o) + `<defs>${blur("bl", w * 0.05)}<linearGradient id="sw" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${h(p.primary)}" stop-opacity="0"/><stop offset="0.5" stop-color="${h(p.primary)}" stop-opacity="0.75"/><stop offset="1" stop-color="${h(p.primary)}" stop-opacity="0"/></linearGradient></defs>` +
      `<g filter="url(#bl)"><path d="M ${w * 0.35} ${H * 1.1} C ${w * 0.6} ${H * 0.75}, ${w * 0.8} ${H * 0.55}, ${w * 1.1} ${H * 0.45} L ${w * 1.1} ${H * 0.62} C ${w * 0.85} ${H * 0.72}, ${w * 0.66} ${H * 0.9}, ${w * 0.5} ${H * 1.1} Z" fill="url(#sw)"/>` +
      `<ellipse cx="${w * 0.05}" cy="${H * 0.05}" rx="${w * 0.2}" ry="${H * 0.18}" fill="${h(p.accent)}" fill-opacity="0.25"/></g>`;
  },
  // light base with angular color shards in two corners (campus / geometric)
  shards(p, w, H, o) {
    const S = (pts, c, op) => `<polygon points="${pts.map(([x, y]) => `${x * w},${y * H}`).join(" ")}" fill="${h(c)}" fill-opacity="${op}"/>`;
    return base(p, w, H, o) +
      S([[0, 0], [0.13, 0], [0, 0.3]], p.primary, 0.95) + S([[0, 0.3], [0.13, 0], [0.19, 0], [0, 0.42]], p.accent, 0.9) + S([[0.06, 0], [0.24, 0], [0.16, 0.08]], p.primary, 0.35) +
      S([[1, 1], [0.86, 1], [1, 0.7]], p.primary, 0.95) + S([[1, 0.7], [0.86, 1], [0.81, 1], [1, 0.6]], p.accent, 0.9) + S([[0.95, 1], [0.76, 1], [0.84, 0.93]], p.primary, 0.35) +
      `<defs><linearGradient id="fade" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${h(p.primary)}" stop-opacity="0.05"/><stop offset="1" stop-color="${h(p.primary)}" stop-opacity="0"/></linearGradient></defs><polygon points="${w * 0.4},0 ${w * 0.75},0 ${w * 0.45},${H}  ${w * 0.1},${H}" fill="url(#fade)"/>`;
  },
  // iridescent ribbon in a corner (purple 3D look)
  ribbon(p, w, H, o) {
    const cols = [p.accent, p.primary, p.accent2 || "7DF9FF", "FFB86B"];
    let s = `<defs>${blur("bl", w * 0.004)}${blur("bl2", w * 0.03)}<linearGradient id="ir" x1="0" y1="0" x2="1" y2="0">${cols.map((c, i) => `<stop offset="${i / (cols.length - 1)}" stop-color="${h(c)}"/>`).join("")}</linearGradient></defs>`;
    let r = "";
    for (let i = 0; i < 26; i++) { const t = i / 26; r += `<path d="M ${w * (0.62 + t * 0.05)} ${-H * 0.05} C ${w * (0.95 - t * 0.1)} ${H * (0.25 + t * 0.1)}, ${w * (0.55 + t * 0.12)} ${H * (0.55 - t * 0.05)}, ${w * (1.05)} ${H * (0.95 - t * 0.2)}" fill="none" stroke="url(#ir)" stroke-width="${w * 0.0035}" stroke-opacity="${(0.3 + 0.7 * Math.sin(Math.PI * t)).toFixed(2)}"/>`; }
    return RECIPES.aurora(p, w, H, { ...o, glows: o.glows || [{ x: 0.9, y: 0.3, rx: 0.25, c: p.primary, o: 0.35 }] }) + s + `<g filter="url(#bl2)" opacity="0.7">${r}</g><g filter="url(#bl)">${r}</g>`;
  },
  // soft out-of-focus orbs (background companion to the 3D orbs hero)
  orbs(p, w, H, o) {
    return RECIPES.aurora(p, w, H, { ...o, glows: o.glows || [{ x: 0.88, y: 0.18, rx: 0.12, c: p.accent, o: 0.5 }, { x: 0.78, y: 0.85, rx: 0.08, c: p.primary, o: 0.5 }, { x: 0.05, y: 0.95, rx: 0.15, c: p.accent2 || p.primary, o: 0.25 }] });
  },
  paper(p, w, H, o) { return base(p, w, H, o) + `<defs>${blur("bl", w * 0.08)}</defs>` + blobs([{ x: 0.0, y: 0.0, rx: 0.3, c: mix(p.bg, "000000", 0.12), o: 0.35 }, { x: 1, y: 1, rx: 0.3, c: mix(p.bg, "000000", 0.12), o: 0.35 }], w, H) + grain(w, H, 0.12); },
  graph(p, w, H, o) {
    const g = w / 64; let s = "";
    for (let x = 0; x <= w; x += g) s += `<line x1="${x}" y1="0" x2="${x}" y2="${H}" stroke-opacity="${Math.round(x / g) % 4 === 0 ? 0.22 : 0.09}"/>`;
    for (let y = 0; y <= H; y += g) s += `<line x1="0" y1="${y}" x2="${w}" y2="${y}" stroke-opacity="${Math.round(y / g) % 4 === 0 ? 0.22 : 0.09}"/>`;
    return base(p, w, H, o) + `<g stroke="${h(o.line || p.primary)}" stroke-width="${w * 0.0005}">${s}</g>`;
  },
  dots(p, w, H, o) { const g = w / 48; let s = ""; for (let x = g / 2; x < w; x += g) for (let y = g / 2; y < H; y += g) s += `<circle cx="${x}" cy="${y}" r="${w * 0.0012}"/>`; return base(p, w, H, o) + `<g fill="${h(o.line || p.muted)}" fill-opacity="0.35">${s}</g>`; },
  solid(p, w, H, o) { return base(p, w, H, o); },
};

function vignettedef(c, op) { return `<radialGradient id="vg" cx="45%" cy="45%" r="80%"><stop offset="60%" stop-color="${h(c)}" stop-opacity="0"/><stop offset="100%" stop-color="${h(c)}" stop-opacity="${op}"/></radialGradient>`; }

function base(p, w, H, o) {
  const a = p.bg, b = p.bg2 || p.bg;
  return `<defs><linearGradient id="base" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${h(a)}"/><stop offset="1" stop-color="${h(b)}"/></linearGradient></defs><rect width="${w}" height="${H}" fill="url(#base)"/>`;
}

async function background(spec, palette, { w = 2400, h: H = 1350, format = "jpeg" } = {}) {
  if (spec.recipe === "image") {
    // a background image you own (e.g. exported from your own template); cropped to fill, optional dim overlay
    const file = require("path").isAbsolute(spec.path) ? spec.path : require("path").join(require("./dataroot.js").dataRoot(), spec.path);
    let img = sharp(file).resize(w, H, { fit: "cover" });
    if (spec.dim) img = sharp(await img.toBuffer()).composite([{ input: Buffer.from(`<svg width="${w}" height="${H}"><rect width="${w}" height="${H}" fill="${h(palette.bg)}" fill-opacity="${spec.dim}"/></svg>`) }]);
    return format === "png" ? img.png().toBuffer() : img.jpeg({ quality: 88 }).toBuffer();
  }
  const fn = RECIPES[spec.recipe || "solid"];
  if (!fn) throw new Error(`unknown background recipe "${spec.recipe}". Recipes: ${Object.keys(RECIPES).join(", ")}`);
  const body = fn(palette, w, H, spec) + (spec.grain === false ? "" : grain(w, H, spec.grain || 0.035));
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${H}" viewBox="0 0 ${w} ${H}">${body}</svg>`;
  const img = sharp(Buffer.from(svg));
  return format === "png" ? img.png().toBuffer() : img.jpeg({ quality: 88, chromaSubsampling: "4:4:4" }).toBuffer();
}

// ---------- hero art (transparent PNG) ----------
const HEROES = {
  orbs(p, s) {
    const sph = (cx, cy, r, c1, c2, c3) => `<radialGradient id="g${cx}${cy}" cx="34%" cy="30%" r="75%"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".18" stop-color="${h(c1)}"/><stop offset=".62" stop-color="${h(c2)}"/><stop offset="1" stop-color="${h(c3)}"/></radialGradient><circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#g${cx}${cy})"/>`;
    const dark = mix(p.bg, "000000", 0.3);
    return `<defs>${blur("gl", s * 0.05)}<linearGradient id="tor" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${h(p.accent)}"/><stop offset=".5" stop-color="${h(p.primary)}"/><stop offset="1" stop-color="${h(p.accent2 || p.accent)}"/></linearGradient></defs>` +
      `<circle cx="${s * 0.55}" cy="${s * 0.45}" r="${s * 0.3}" fill="${h(p.primary)}" fill-opacity=".45" filter="url(#gl)"/>` +
      sph(s * 0.55, s * 0.45, s * 0.28, mix(p.primary, "ffffff", 0.35), p.primary, dark) +
      `<ellipse cx="${s * 0.52}" cy="${s * 0.62}" rx="${s * 0.4}" ry="${s * 0.1}" fill="none" stroke="url(#tor)" stroke-width="${s * 0.035}" transform="rotate(-14 ${s * 0.52} ${s * 0.62})"/>` +
      sph(s * 0.2, s * 0.78, s * 0.09, mix(p.accent, "ffffff", 0.4), p.accent, dark) + sph(s * 0.86, s * 0.18, s * 0.06, mix(p.accent2 || p.accent, "ffffff", 0.4), p.accent2 || p.accent, dark);
  },
  iso(p, s) {
    const cube = (x, y, a, top, l, r, hgt = 1) => `<polygon points="${x},${y} ${x + a},${y - a / 2} ${x + 2 * a},${y} ${x + a},${y + a / 2}" fill="${h(top)}"/><polygon points="${x},${y} ${x + a},${y + a / 2} ${x + a},${y + a / 2 + a * hgt} ${x},${y + a * hgt}" fill="${h(l)}"/><polygon points="${x + a},${y + a / 2} ${x + 2 * a},${y} ${x + 2 * a},${y + a * hgt} ${x + a},${y + a / 2 + a * hgt}" fill="${h(r)}"/>`;
    const P = p.primary, A = p.accent, d = (c, t) => mix(c, "000000", t), l = (c, t) => mix(c, "ffffff", t);
    const slab = (x, y, a, c) => cube(x, y, a, l(c, 0.25), d(c, 0.25), d(c, 0.45), 0.18);
    let g = slab(s * 0.1, s * 0.62, s * 0.4, mix(p.bg, P, 0.35));
    g += cube(s * 0.36, s * 0.45, s * 0.14, l(P, 0.3), P, d(P, 0.35), 1.6) + cube(s * 0.2, s * 0.57, s * 0.1, l(A, 0.3), A, d(A, 0.35), 0.9) + cube(s * 0.58, s * 0.57, s * 0.1, l(A, 0.3), A, d(A, 0.35), 0.7);
    g += `<line x1="${s * 0.5}" y1="${s * 0.38}" x2="${s * 0.5}" y2="${s * 0.1}" stroke="${h(l(P, 0.4))}" stroke-width="${s * 0.008}"/>` + [0.12, 0.18, 0.24].map((r2) => `<path d="M ${s * (0.5 - r2 * 0.5)} ${s * (0.1 + r2 * 0.25)} A ${s * r2 * 0.6} ${s * r2 * 0.6} 0 0 1 ${s * (0.5 + r2 * 0.5)} ${s * (0.1 + r2 * 0.25)}" fill="none" stroke="${h(A)}" stroke-opacity=".7" stroke-width="${s * 0.006}"/>`).join("");
    return `<defs>${blur("gl", s * 0.04)}</defs><ellipse cx="${s * 0.5}" cy="${s * 0.7}" rx="${s * 0.42}" ry="${s * 0.14}" fill="${h(P)}" fill-opacity=".35" filter="url(#gl)"/>` + g;
  },
  halo(p, s) { return `<defs><radialGradient id="ha" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="${h(p.primary)}" stop-opacity=".75"/><stop offset=".45" stop-color="${h(p.primary)}" stop-opacity=".25"/><stop offset="1" stop-color="${h(p.primary)}" stop-opacity="0"/></radialGradient></defs><circle cx="${s / 2}" cy="${s / 2}" r="${s / 2}" fill="url(#ha)"/>`; },
  ribbon(p, s) { return HEROES.orbs(p, s); },
};

async function hero(kind, palette, { w = 1200, h: H = 1200 } = {}) {
  const fn = HEROES[kind]; if (!fn) throw new Error(`unknown hero "${kind}"`);
  const s = Math.min(w, H);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${s}" height="${s}" viewBox="0 0 ${s} ${s}">${fn(palette, s)}</svg>`;
  return sharp(Buffer.from(svg)).png().toBuffer();
}

// sparkline / area image with gradient fill (decorative, for KPI tiles)
async function sparkline(values, color, { w = 900, h: H = 300, fill = true } = {}) {
  const min = Math.min(...values), max = Math.max(...values), n = values.length;
  const pts = values.map((v, i) => [i / (n - 1) * w, H - 12 - (v - min) / (max - min || 1) * (H - 24)]);
  const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${H}"><defs><linearGradient id="sf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${h(color)}" stop-opacity=".45"/><stop offset="1" stop-color="${h(color)}" stop-opacity="0"/></linearGradient>${blur("sg", 6)}</defs>${fill ? `<path d="${d} L ${w} ${H} L 0 ${H} Z" fill="url(#sf)"/>` : ""}<path d="${d}" fill="none" stroke="${h(color)}" stroke-width="10" stroke-opacity=".5" filter="url(#sg)"/><path d="${d}" fill="none" stroke="${h(color)}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${pts[n - 1][0] - 8}" cy="${pts[n - 1][1]}" r="9" fill="${h(color)}"/></svg>`;
  return sharp(Buffer.from(svg)).png().toBuffer();
}

module.exports = { background, hero, sparkline, RECIPES: [...Object.keys(RECIPES), "image"], HEROES: Object.keys(HEROES), mix };
