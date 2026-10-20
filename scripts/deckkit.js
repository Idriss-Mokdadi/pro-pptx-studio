// deckkit.js v2 — style-driven, animated, font-embedded PowerPoint decks on pptxgenjs. MIT License.
//
//   const { Deck } = require("<skill>/scripts/deckkit.js");
//   const deck = new Deck({ style: "nebula", title: "SentinelCore 5G", footer: "SentinelCore 5G · PFA 2026", lang: "fr" });
//   deck.cover({...}).agenda({...}).section({...}).cards({...}) ... ;
//   await deck.save("deck.pptx");
//
// Every method queues one slide and returns the deck. See references/components.md.

const fs = require("fs");
const os = require("os");
const path = require("path");
const PptxGenJS = require("pptxgenjs");
const sharp = require("sharp");
const BG = require("./backgrounds.js");
const { finalize } = require("./motion.js");
const POST = require("./post.js");

const ROOT = path.join(__dirname, "..");
const DATA = require("./dataroot.js").dataRoot();
const ICONS = JSON.parse(fs.readFileSync(path.join(ROOT, "assets", "icons.json"), "utf8"));
const OBJ_INDEX = JSON.parse(fs.readFileSync(path.join(DATA, "assets", "3d", "index.json"), "utf8"));

const W = 13.333, H = 7.5, M = 0.7, CW = W - 2 * M;
const Y0 = 2.2, Y1 = 6.6, CH = Y1 - Y0;

const LABELS = {
  en: { agenda: "Agenda", part: "Part", thanks: "Thank you", questions: "Questions & discussion", today: "Today", target: "With our solution", source: "Source", presented: "Presented by", supervised: "Supervised by" },
  fr: { agenda: "Sommaire", part: "Partie", thanks: "Merci de votre attention", questions: "Questions & discussion", today: "Aujourd'hui", target: "Avec notre solution", source: "Source", presented: "Présenté par", supervised: "Encadré par" },
};
const MOTION = {
  none: { transition: "none", speed: "med", mode: "none", item: "fade", emph: "fade", line: "fade", stagger: 0 },
  subtle: { transition: "morph", speed: "med", mode: "auto", item: "fade", emph: "fade", line: "wipe", stagger: 110 },
  lively: { transition: "morph", speed: "slow", mode: "auto", item: "rise", emph: "pop", line: "wipe", stagger: 150 },
  click: { transition: "morph", speed: "med", mode: "click", item: "rise", emph: "pop", line: "wipe", stagger: 0 },
};
// average glyph width / font size, used to estimate wrapping
const GLYPH = { "Anton": 0.43, "Bebas Neue": 0.38, "Big Shoulders Display": 0.42, "Oswald": 0.46, "Barlow Condensed": 0.42, "Saira Condensed": 0.45, "Orbitron": 0.74, "Unbounded": 0.72, "Russo One": 0.64, "Audiowide": 0.68, "Archivo Black": 0.66, "Press Start 2P": 0.98, "Silkscreen": 0.8, "Sora": 0.6, "Plus Jakarta Sans": 0.56, "Inter": 0.54, "Montserrat": 0.66, "Outfit": 0.52, "Exo 2": 0.56, "Red Hat Display": 0.63, "JetBrains Mono": 0.6, "Space Mono": 0.62, "Fraunces": 0.56, "Londrina Solid": 0.45, "Poppins": 0.62, "Tomorrow": 0.6, "Saira": 0.56, "Chakra Petch": 0.56, "Lora": 0.55, "Jost": 0.52, "DM Sans": 0.55, "Playfair Display": 0.56, "Cormorant Garamond": 0.48, "Source Serif 4": 0.54, "Bodoni Moda": 0.55, "Instrument Serif": 0.45, "Shrikhand": 0.66, "Syne": 0.68, "Fredoka": 0.56, "Bricolage Grotesque": 0.55, "Caveat": 0.42, "Zilla Slab": 0.52, "Alfa Slab One": 0.66, "Instrument Sans": 0.54, "Manrope": 0.56, "Kanit": 0.56, "Rajdhani": 0.48, "Lexend": 0.58, "VT323": 0.45, "Titillium Web": 0.52, "Barlow": 0.52 };
const CONDENSED = ["Anton", "Bebas Neue", "Big Shoulders Display", "Oswald", "Barlow Condensed", "Saira Condensed", "Londrina Solid", "Rajdhani", "Caveat", "Instrument Serif", "Cormorant Garamond"];
const WIDE = ["Orbitron", "Unbounded", "Russo One", "Audiowide", "Archivo Black", "Press Start 2P", "Silkscreen", "Shrikhand", "Alfa Slab One", "Syne"];

const hex6 = (c) => String(c).replace("#", "").toUpperCase();
function lum(hx) { const c = [0, 2, 4].map((i) => parseInt(hex6(hx).slice(i, i + 2), 16) / 255).map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4)); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; }
function contrast(a, b) { const [x, y] = [lum(a), lum(b)]; return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
const mix = (a, b, t) => BG.mix(hex6(a), hex6(b), t).toUpperCase();

function loadStyle(style) {
  if (style && typeof style === "object") return JSON.parse(JSON.stringify(style));
  const id = style || "nebula";
  const p = fs.existsSync(id) ? id : path.join(DATA, "styles", `${id}.json`);
  if (!fs.existsSync(p)) throw new Error(`unknown style "${id}". Run: node scripts/styles.js list`);
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

let reactLib = null;
function iconData(name, color) {
  if (!name) return null;
  if (!reactLib) reactLib = { React: require("react"), RDS: require("react-dom/server"), sets: {} };
  const SETS = { Lu: "lu", Pi: "pi", Tb: "tb", Md: "md", Fa: "fa6" };
  const prefix = Object.keys(SETS).find((p) => name.startsWith(p));
  if (!prefix) throw new Error(`icon "${name}": use a semantic name (${Object.keys(ICONS).slice(0, 12).join(", ")}…) or a react-icons name like LuShieldCheck`);
  const set = reactLib.sets[prefix] || (reactLib.sets[prefix] = require("react-icons/" + SETS[prefix]));
  const Comp = set[name]; if (!Comp) throw new Error(`icon "${name}" not found`);
  let svg = reactLib.RDS.renderToStaticMarkup(reactLib.React.createElement(Comp, { size: 256, color: "#" + hex6(color) }));
  if (!/\bcolor=/.test(svg)) svg = svg.replace("<svg", `<svg color="#${hex6(color)}"`);
  return svg;
}
const iconCache = new Map();
async function renderIcon(name, color, filled) {
  if (!name) return null;
  const pair = ICONS[name]; const real = pair ? pair[filled ? 1 : 0] : name;
  const key = real + color; if (iconCache.has(key)) return iconCache.get(key);
  const png = await sharp(Buffer.from(iconData(real, color))).resize(256, 256).png().toBuffer();
  const d = "image/png;base64," + png.toString("base64"); iconCache.set(key, d); return d;
}
function objPath(name) {
  if (!name) return null;
  if (fs.existsSync(name)) return name;
  const slug = String(name).toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const keys = Object.keys(OBJ_INDEX);
  const k = keys.find((x) => x === slug) || keys.find((x) => x.startsWith(slug)) || keys.find((x) => x.includes(slug));
  if (!k) throw new Error(`3D object "${name}" not found. Available: ${keys.slice(0, 40).join(", ")}…`);
  return path.join(DATA, "assets", "3d", k + ".png");
}
const TOPIC_OBJ = [[/\b(ai|ia|intelligence|machine learning|llm|robot)/i, "robot"], [/(secur|cyber|threat|attack|intrusion)/i, "shield"], [/(5g|4g|telecom|antenna|network|réseau|ran\b|core)/i, "satellite-antenna"], [/(energy|énergie|power|grid|steg|délestage|electric)/i, "high-voltage"], [/(iot|sensor|capteur|embedded|esp32)/i, "electric-plug"], [/(data|analytics|dashboard|kpi)/i, "bar-chart"], [/(health|santé|hospital|clinic|uv|saniti)/i, "microbe"], [/(school|education|thesis|pfa|stage|internship|soutenance)/i, "graduation-cap"], [/(cloud)/i, "cloud"], [/(code|software|app|logiciel)/i, "laptop"], [/(startup|pitch|launch)/i, "rocket"], [/(event|hackathon|workshop)/i, "party-popper"]];

async function roundedImage(file, wIn, hIn, radiusIn, mode = "cover") {
  const pxPerIn = 220; const w = Math.max(40, Math.round(wIn * pxPerIn)), h = Math.max(40, Math.round(hIn * pxPerIn)), r = Math.round(radiusIn * pxPerIn);
  const img = await sharp(file).resize(w, h, { fit: mode === "contain" ? "contain" : "cover", background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toBuffer();
  const mask = Buffer.from(`<svg width="${w}" height="${h}"><rect width="${w}" height="${h}" rx="${r}" ry="${r}"/></svg>`);
  const out = await sharp(img).composite([{ input: mask, blend: "dest-in" }]).png().toBuffer();
  return "image/png;base64," + out.toString("base64");
}

class Deck {
  constructor(opts = {}) {
    this.st = loadStyle(opts.style);
    if (opts.colors) Object.assign(this.st.colors, opts.colors);
    if (opts.fonts) Object.assign(this.st.fonts, opts.fonts);
    this.c = this.st.colors; this.F = this.st.fonts;
    this.opts = opts; this.L = LABELS[opts.lang] || LABELS.en;
    this.motion = MOTION[opts.motion || "subtle"]; if (!this.motion) throw new Error(`motion: ${Object.keys(MOTION).join(", ")}`);
    this.footer = opts.footer ?? opts.title ?? "";
    this.logos = opts.logos || [];
    this.ops = []; this.plan = []; this.charts = []; this.warnings = []; this.sections = []; this.section_ = null;
    this.dark = this.st.mode === "dark";
    this.tmp = fs.mkdtempSync(path.join(os.tmpdir(), "pps-"));
    this.heroObj = opts.hero || null;
    if (opts.hero && (!this.st.hero || this.st.hero.kind === "none")) this.st.hero = { kind: "3d", halo: true }; // a typographic style can still carry a 3D object
    const p = (this.pres = new PptxGenJS());
    p.layout = "LAYOUT_WIDE"; p.title = opts.title || "Presentation"; if (opts.author) p.author = opts.author;
    p.theme = { headFontFace: this.F.display, bodyFontFace: this.F.body };
    const sz = (f) => (CONDENSED.includes(f) ? "c" : WIDE.includes(f) ? "w" : "n");
    const k = sz(this.F.display), kh = sz(this.F.head);
    this.size = { cover: { c: 100, w: 50, n: 68 }[k], section: { c: 120, w: 60, n: 80 }[k], title: { c: 40, w: 25, n: 30 }[kh], stat: { c: 72, w: 46, n: 56 }[k] };
    this._checkContrast();
  }

  _checkContrast() {
    const c = this.c;
    if (contrast(c.text, c.bg) < 4.5) this.warnings.push(`style text/background contrast ${contrast(c.text, c.bg).toFixed(1)}:1 is below 4.5:1`);
    if (contrast(c.muted, c.bg) < 4.5) this.warnings.push(`style muted text contrast ${contrast(c.muted, c.bg).toFixed(1)}:1 is below 4.5:1`);
  }

  // ---------- small helpers ----------
  font(role) { return { display: this.F.display, head: this.F.head, body: this.F.body, mono: this.F.mono || "JetBrains Mono" }[role] || role; }
  up(s, role = "head") { const cs = role === "display" ? this.F.displayCase : this.F.headCase; return cs === "upper" ? String(s).toUpperCase() : String(s); }
  best(fill, opts = [this.c.text, this.c.onPrimary, "FFFFFF", "111111"]) { return opts.map(hex6).sort((a, b) => contrast(b, fill) - contrast(a, fill))[0]; }

  _lines(text, w, size, face, bold) {
    const g = (GLYPH[face] || 0.56) * (bold ? 1.05 : 1) * (/^[^a-z]*$/.test(text) && /[A-Z]/.test(text) ? 1.18 : 1) * (/^[\d.,%+\-×x\s$€]+$/.test(String(text).trim()) ? 1.28 : 1);
    const per = Math.max(1, Math.floor(w / ((size / 72) * g)));
    let lines = 0;
    for (const para of String(text || "").split("\n")) { let cur = 0; lines++; for (const word of para.split(/\s+/)) { const n = word.length + (cur ? 1 : 0); if (cur + n > per && cur > 0) { lines++; cur = word.length; } else cur += n; } }
    return lines;
  }
  _need(text, w, size, bold, face) { return text ? (this._lines(text, w, size, face || this.F.body, bold) * size * 1.22) / 72 : 0; }
  _wordW(text, size, face, bold) { const g = (GLYPH[face] || 0.56) * (bold ? 1.05 : 1); const longest = String(text || "").split(/\s+/).reduce((m, x) => Math.max(m, x.length * (/^[^a-z]*$/.test(x) && /[A-Z]/.test(x) ? 1.12 : 1)), 0); return (longest * size * g) / 72; }
  _fitSize(text, w, h, size, face, bold, min) { let s = size; while (s > min && ((this._lines(text, w, s, face, bold) * s * 1.18) / 72 > h || this._wordW(text, s, face, bold) > w)) s -= 2; return s; }

  _txt(s, ctx, text, o) {
    const face = this.font(o.font || "body"); const size = o.fontSize || 14;
    const plain = Array.isArray(text) ? text.map((r) => r.text).join("") : String(text ?? "");
    let size_ = size; while (size_ > 9 && plain && this._wordW(plain, size_, face, o.bold) > o.w) size_ -= 1;
    if (size_ !== size) { o = { ...o, fontSize: size_ }; }
    if (o.fit !== false && plain && this._need(plain, o.w - 0.04, size, o.bold, face) > o.h + 0.08) this.warnings.push(`slide ${ctx.n}: text may overflow ${o.objectName || ""} → "${plain.slice(0, 48)}…"`);
    const opts = { isTextBox: true, margin: 0, fontFace: face, fontSize: size, color: this.c.text, valign: "top", paraSpaceAfter: 0, ...o };
    delete opts.font; delete opts.fit;
    s.addText(Array.isArray(text) ? text : plain, opts);
    return o.objectName;
  }
  _shape(s, type, o) { s.addShape(this.pres.shapes[type] || type, o); return o.objectName; }
  async _img(s, data, o) { s.addImage({ ...(typeof data === "string" && data.startsWith("image/") ? { data } : { path: data }), ...o }); return o.objectName; }

  // card surface in the style's own language; returns colors to use inside
  _card(s, x, y, w, h, name, { emphasis = false, fill = null } = {}) {
    const c = this.c, k = this.st.card.kind, r = this.st.card.radius ?? 0.14, S = this.pres.shapes;
    const RR = r > 0 ? S.ROUNDED_RECTANGLE : S.RECTANGLE; const rr = Math.min(0.5, r / Math.min(w, h));
    const names = [name];
    let inside = { text: c.text, muted: c.muted, ink: c.ink };
    const sh = () => ({ type: "outer", color: "000000", opacity: this.dark ? 0.35 : 0.12, blur: 12, offset: 3, angle: 90 });
    if (fill) { s.addShape(RR, { x, y, w, h, rectRadius: rr, fill: { color: fill }, line: { color: fill, width: 0 }, objectName: name }); const t = this.best(fill); return { names, inside: { text: t, muted: t, ink: t } }; }
    switch (k) {
      case "glass": s.addShape(RR, { x, y, w, h, rectRadius: rr, fill: { color: c.surface, transparency: emphasis ? Math.max(70, c.surfaceAlpha - 10) : c.surfaceAlpha }, line: { color: emphasis ? c.primary : c.border, width: 1, transparency: emphasis ? 20 : c.borderAlpha }, shadow: sh(), objectName: name }); break;
      case "tile": s.addShape(RR, { x, y, w, h, rectRadius: rr, fill: { color: emphasis ? c.primary : c.surface }, line: { color: emphasis ? c.primary : mix(c.surface, "FFFFFF", 0.06), width: 0.75 }, objectName: name }); if (emphasis) inside = { text: c.onPrimary, muted: c.onPrimary, ink: c.onPrimary }; break;
      case "hud": {
        s.addShape(S.RECTANGLE, { x, y, w, h, fill: { color: c.surface, transparency: c.surfaceAlpha }, line: { color: c.primary, width: 1, transparency: emphasis ? 20 : 60 }, objectName: name });
        const L = Math.min(0.28, w * 0.15), t = 2.25;
        [[x, y, 1, 1], [x + w, y, -1, 1], [x, y + h, 1, -1], [x + w, y + h, -1, -1]].forEach(([px, py, dx, dy], i) => {
          s.addShape(S.LINE, { x: dx > 0 ? px : px - L, y: py, w: L, h: 0, line: { color: c.primary, width: t }, objectName: `${name}_b${i}a` });
          s.addShape(S.LINE, { x: px, y: dy > 0 ? py : py - L, w: 0, h: L, line: { color: c.primary, width: t }, objectName: `${name}_b${i}b` });
          names.push(`${name}_b${i}a`, `${name}_b${i}b`);
        }); break; }
      case "hex": s.addShape(S.SNIP_2_DIAG_RECTANGLE || "snip2DiagRect", { x, y, w, h, rectRadius: 0.18, fill: { color: c.surface, transparency: c.surfaceAlpha }, line: { color: c.primary, width: 1.25, transparency: emphasis ? 10 : c.borderAlpha }, objectName: name }); break;
      case "outline": s.addShape(RR, { x, y, w, h, rectRadius: rr, fill: { color: c.surface, transparency: this.dark ? 30 : 0 }, line: { color: emphasis ? c.primary : c.border, width: 1.25, transparency: emphasis ? 0 : c.borderAlpha }, objectName: name }); break;
      case "brutal": s.addShape(RR, { x, y, w, h, rectRadius: rr, fill: { color: emphasis ? c.primary : (this.dark ? c.surface : "FFFFFF") }, line: { color: "111111", width: 2.5 }, shadow: { type: "outer", color: "111111", opacity: 1, blur: 0, offset: 6, angle: 45 }, objectName: name }); if (emphasis) { const t = this.best(c.primary); inside = { text: t, muted: t, ink: t }; } else if (!this.dark) inside = { text: "111111", muted: "333333", ink: "111111" }; break;
      case "block": { const f = emphasis ? c.accent : c.primary; s.addShape(RR, { x, y, w, h, rectRadius: rr, fill: { color: f }, line: { color: f, width: 0 }, objectName: name }); const t = this.best(f); inside = { text: t, muted: t, ink: t }; break; }
      case "soft": s.addShape(RR, { x, y, w, h, rectRadius: rr, fill: { color: c.surface, transparency: c.surfaceAlpha }, line: { color: emphasis ? c.primary : c.border, width: emphasis ? 1.5 : 0.75, transparency: emphasis ? 0 : 30 }, shadow: { type: "outer", color: "1B2A4A", opacity: 0.1, blur: 16, offset: 4, angle: 90 }, objectName: name }); break;
      default: s.addShape(RR, { x, y, w, h, rectRadius: rr, fill: { color: c.surface, transparency: c.surfaceAlpha || 0 }, line: { color: emphasis ? c.primary : c.border, width: emphasis ? 1.25 : 0.75, transparency: emphasis ? 0 : (c.borderAlpha ?? 0) }, objectName: name });
    }
    return { names, inside };
  }

  // icon in a filled circle (bento-style) or a 3D object
  async _icon(s, it, x, y, size, name, onFill) {
    const c = this.c;
    if (it.obj) { await this._img(s, objPath(it.obj), { x: x - size * 0.1, y: y - size * 0.1, w: size * 1.2, h: size * 1.2, objectName: name }); return [name]; }
    if (!it.icon) return [];
    const circle = onFill || c.primary;
    s.addShape(this.pres.shapes.OVAL, { x, y, w: size, h: size, fill: { color: circle }, line: { color: circle, width: 0 }, objectName: name + "c" });
    const d = await renderIcon(it.icon, this.best(circle, ["FFFFFF", "111111", c.onPrimary]), this.st.icons === "filled" || this.st.card.kind === "tile");
    s.addImage({ data: d, x: x + size * 0.24, y: y + size * 0.24, w: size * 0.52, h: size * 0.52, objectName: name });
    return [name + "c", name];
  }

  _heroName() { return this.heroObj || this.st.hero?.objects?.[0] || (TOPIC_OBJ.find(([re]) => re.test(`${this.opts.title} ${this.opts.topic || ""}`)) || [0, "rocket"])[1]; }

  async _hero(s, ctx, x, y, size, { name = "!!hero", halo = true } = {}) {
    const k = this.st.hero?.kind || "none"; if (k === "none") return [];
    const pal = { ...this.c, bg: this.c.bg };
    const out = [];
    if (k === "orbs" || k === "iso") {
      const f = path.join(this.tmp, `hero-${k}.png`);
      if (!fs.existsSync(f)) fs.writeFileSync(f, await BG.hero(k, pal, { w: 1400, h: 1400 }));
      await this._img(s, f, { x, y, w: size, h: size, objectName: name }); out.push(name); return out;
    }
    if (k === "3d") {
      if (halo && this.st.hero.halo !== false) {
        const f = path.join(this.tmp, "halo.png"); if (!fs.existsSync(f)) fs.writeFileSync(f, await BG.hero("halo", pal, { w: 900, h: 900 }));
        await this._img(s, f, { x: x - size * 0.25, y: y - size * 0.25, w: size * 1.5, h: size * 1.5, objectName: name + "glow" }); out.push(name + "glow");
      }
      await this._img(s, objPath(this._heroName()), { x, y, w: size, h: size, objectName: name }); out.push(name);
    }
    return out;
  }

  // ---------- slide scaffolding ----------
  _new(kind, o, layout = "PX_CONTENT") {
    const n = this.plan.length + 1;
    const s = this.pres.addSlide({ masterName: layout, ...(this.sections.length ? { sectionTitle: this.section_ || this.sections[0] } : {}) });
    if (o.notes) s.addNotes(o.notes);
    const m = this.motion; const mode = o.motion === undefined ? m.mode : o.motion === "none" ? "none" : o.motion;
    const entry = { transition: m.transition === "none" ? "none" : n === 1 ? "fade" : m.transition, speed: m.speed, mode, stagger: m.stagger, steps: [], kind };
    this.plan.push(entry);
    return { n, s, entry, step: (names, role = "item") => { const l = (Array.isArray(names) ? names : [names]).flat().filter(Boolean); if (l.length) entry.steps.push({ names: l, effect: m[role] || "fade" }); } };
  }

  _chrome(s, ctx, kicker) {
    const c = this.c, ch = this.st.chrome || {}, S = this.pres.shapes;
    const label = kicker === undefined ? this.section_ || "" : kicker;
    if (ch.nav && this.sections.length > 1) {
      const n = this.sections.length, w = Math.min(1.9, 7.6 / n);
      this.sections.forEach((t, i) => this._txt(s, ctx, String(t).toUpperCase(), { x: W - M - (n - i) * w, y: 0.32, w: w - 0.1, h: 0.3, fontSize: 10, bold: t === this.section_, color: t === this.section_ ? c.text : c.muted, charSpacing: 1, align: "right", objectName: `nav${i}`, fit: false }));
    }
    if (label && ch.kicker !== "none") {
      const L = String(label).toUpperCase();
      if (ch.kicker === "bracket") this._txt(s, ctx, `[ ${L} ]`, { x: M, y: 0.5, w: 8, h: 0.35, fontSize: 12, bold: true, color: c.ink, charSpacing: 2, font: "body", objectName: "kicker", fit: false });
      else if (ch.kicker === "slash") this._txt(s, ctx, `// ${L}`, { x: M, y: 0.5, w: 8, h: 0.35, fontSize: 12, bold: true, color: c.ink, charSpacing: 1, font: "mono", objectName: "kicker", fit: false });
      else {
        if (ch.kicker === "hex") s.addShape(S.HEXAGON, { x: M, y: 0.56, w: 0.22, h: 0.2, fill: { color: c.primary }, line: { color: c.primary, width: 0 }, objectName: "!!dot" });
        else s.addShape(S.OVAL, { x: M, y: 0.585, w: 0.15, h: 0.15, fill: { color: c.primary }, line: { color: c.primary, width: 0 }, objectName: "!!dot" });
        this._txt(s, ctx, L, { x: M + 0.32, y: 0.48, w: 8, h: 0.38, fontSize: 12, bold: true, color: c.ink, charSpacing: 2, valign: "middle", objectName: "kicker", fit: false });
      }
    }
  }

  _title(s, ctx, title, box) {
    if (!title) return 0;
    const [w, h, size] = box || [CW, 1.15, this.size.title];
    const raw = Array.isArray(title) ? title : [{ text: String(title) }];
    const runs = raw.map((r) => ({ ...r, text: this.up(r.text) }));
    const plain = runs.map((r) => r.text).join("");
    const fs_ = this._fitSize(plain, w, h, size, this.F.head, true, Math.round(size * 0.72));
    const lines = this._lines(plain, w, fs_, this.F.head, true);
    if ((lines * fs_ * 1.18) / 72 > h + 0.06) this.warnings.push(`slide ${ctx.n} title too long → shorten "${plain.slice(0, 50)}…"`);
    s.addText(runs.map((r) => ({ text: r.text, options: { ...(r.options || {}), fontSize: fs_ } })), { placeholder: "title" });
    return Math.min(h, (lines * fs_ * 1.2) / 72);
  }

  _layouts(bgPath) {
    const p = this.pres, c = this.c, F = this.F, ch = this.st.chrome || {};
    const bg = { path: bgPath };
    const foot = [];
    if (ch.footer === "text" && this.footer) foot.push({ text: { text: this.footer, options: { x: M, y: 6.98, w: 7, h: 0.3, fontFace: F.body, fontSize: 10, color: c.muted, margin: 0 } } });
    if (ch.footer === "logos" && this.logos.length) this.logos.forEach((l, i) => foot.push({ image: { path: l.path || l, x: W / 2 - (this.logos.length * 0.75) / 2 + i * 0.75, y: 6.92, w: 0.6, h: 0.4, sizing: { type: "contain", w: 0.6, h: 0.4 } } }));
    const num = ch.page === "none" ? undefined : { x: W - M - 1.0, y: 6.98, w: 1.0, h: 0.3, fontFace: F.body, fontSize: 10, color: c.muted, align: "right" };
    const ph = (x, y, w, h, size, extra = {}) => ({ placeholder: { options: { name: "title", type: "title", x, y, w, h, fontFace: F.head, fontSize: size, bold: true, italic: !!F.displayItalic, color: c.text, align: "left", valign: "top", margin: 0, ...extra }, text: "" } });
    p.defineSlideMaster({ title: "PX_COVER", background: bg, objects: [] });
    p.defineSlideMaster({ title: "PX_CONTENT", background: bg, objects: [ph(M, 0.95, CW, 1.15, this.size.title), ...foot], slideNumber: num });
    p.defineSlideMaster({ title: "PX_SPLIT", background: bg, objects: [ph(M, 0.95, 5.6, 1.5, this.size.title), ...foot], slideNumber: num });
    p.defineSlideMaster({ title: "PX_PLAIN", background: bg, objects: [...foot], slideNumber: num });
  }

  _queue(fn) { this.ops.push(fn); return this; }

  // ================= components =================
  cover(o) {
    if (!this.sections.length) { this.sections.push(o.section || "Intro"); }
    return this._queue(async () => {
      if (!this.section_) { this.section_ = this.sections[0]; this.pres.addSection({ title: this.section_ }); }
      const ctx = this._new("cover", o, "PX_COVER"), { s } = ctx, c = this.c;
      const heroKind = this.st.hero?.kind || "none";
      const hasArt = (heroKind !== "none" || o.image) && o.layout !== "display";
      const tw = hasArt ? 7.2 : CW;
      const align = hasArt ? "left" : (this.F.displayCase === "upper" && !this.dark ? "center" : "left");
      const names = [];
      if (o.image) { const d = await roundedImage(o.image, 5.4, 6.1, 0.25); await this._img(s, d, { x: W - M - 5.4, y: 0.7, w: 5.4, h: 6.1, objectName: "!!hero" }); names.push("!!hero"); }
      else if (hasArt) names.push(...(await this._hero(s, ctx, W - M - 4.9, 1.25, 4.9)));
      const k = o.kicker && this._txt(s, ctx, String(o.kicker).toUpperCase(), { x: M, y: align === "center" ? 1.35 : 1.55, w: tw, h: 0.4, fontSize: 14, bold: true, charSpacing: 3, color: c.ink, align, objectName: "kicker", fit: false });
      const title = this.up(o.title, "display");
      const ts = this._fitSize(title, tw, 2.7, this.size.cover, this.F.display, true, Math.round(this.size.cover * 0.55));
      const tl = this._lines(title, tw, ts, this.F.display, true), th = (tl * ts * 1.08) / 72;
      const ty = align === "center" ? 1.9 : 2.1;
      this._txt(s, ctx, title, { x: M, y: ty, w: tw, h: th + 0.1, font: "display", fontSize: ts, bold: true, italic: !!this.F.displayItalic, color: c.text, align, lineSpacingMultiple: 0.92, objectName: "title", fit: false, glow: this.dark ? { size: 8, opacity: 0.25, color: c.primary } : undefined });
      let y = ty + th + 0.3;
      const sub = o.subtitle && this._txt(s, ctx, o.subtitle, { x: M, y, w: Math.min(tw, 7.2) + (align === "center" ? CW - 7.2 : 0), h: this._need(o.subtitle, Math.min(tw, 7.2), 19) + 0.1, fontSize: 19, color: c.muted, align, objectName: "subtitle" });
      if (o.subtitle) y += this._need(o.subtitle, Math.min(tw, 7.2), 19) + 0.45;
      const meta = [...(o.meta || []), o.date].filter(Boolean);
      const my = Math.max(y, 5.3);
      const mt = meta.length && this._txt(s, ctx, meta.map((t, i) => ({ text: t, options: { breakLine: i < meta.length - 1, bold: i === 0, color: i === 0 ? c.text : c.muted } })), { x: M, y: my, w: tw, h: 1.3, fontSize: 14, align, paraSpaceAfter: 4, objectName: "meta", fit: false });
      const lg = [];
      if (this.logos.length && o.logos !== false) { this.logos.forEach((l, i) => { s.addImage({ path: l.path || l, x: M + i * 1.1, y: 6.75, w: 0.95, h: 0.5, sizing: { type: "contain", w: 0.95, h: 0.5 }, objectName: `logo${i}` }); lg.push(`logo${i}`); }); }
      ctx.step(names, "emph"); ctx.step([k, sub].filter(Boolean)); ctx.step([mt, ...lg].filter(Boolean));
    });
  }

  agenda(o) {
    return this._queue(async () => {
      const ctx = this._new("agenda", o), { s } = ctx, c = this.c;
      this._chrome(s, ctx, o.kicker === undefined ? this.L.agenda : o.kicker);
      this._title(s, ctx, o.title || this.L.agenda);
      const items = o.items || [], n = items.length, cols = n <= 5 ? n : Math.ceil(n / 2), rows = n <= 5 ? 1 : 2, gap = 0.3;
      const w = (CW - gap * (cols - 1)) / cols, h = rows === 1 ? 3.2 : (CH - gap - 0.2) / 2;
      for (let i = 0; i < n; i++) {
        const it = typeof items[i] === "string" ? { head: items[i] } : items[i];
        const x = M + (i % cols) * (w + gap), y = Y0 + 0.1 + Math.floor(i / cols) * (h + gap) + (rows === 1 ? 0.45 : 0);
        const cur = o.current === i, dim = o.current !== undefined && !cur;
        const { names, inside } = this._card(s, x, y, w, h, `ag${i}`, { emphasis: cur });
        names.push(this._txt(s, ctx, String(i + 1).padStart(2, "0"), { x: x + 0.3, y: y + 0.25, w: w - 0.6, h: 0.8, font: "display", fontSize: 48, bold: true, color: dim ? inside.muted : inside.ink, objectName: `ag${i}n`, wrap: false, fit: false }));
        names.push(this._txt(s, ctx, it.head, { x: x + 0.3, y: y + h - 0.35 - this._need(it.head, w - 0.6, 17, true), w: w - 0.6, h: this._need(it.head, w - 0.6, 17, true) + 0.05, fontSize: 17, bold: true, color: dim ? inside.muted : inside.text, objectName: `ag${i}t` }));
        ctx.step(names);
      }
      if (this.st.hero?.kind === "3d" || this.st.hero?.kind === "orbs" || this.st.hero?.kind === "iso") await this._hero(s, ctx, W - M - 1.3, 0.35, 1.3, { halo: false });
    });
  }

  section(o) {
    this.sections.push(o.title);
    return this._queue(async () => {
      this.section_ = o.title; this.pres.addSection({ title: o.title });
      const ctx = this._new("section", o, "PX_PLAIN"), { s } = ctx, c = this.c;
      const center = this.F.displayCase === "upper" && !this.dark && !(this.st.hero?.kind && this.st.hero.kind !== "none");
      const art = this.st.hero?.kind && this.st.hero.kind !== "none";
      const tw = art ? 8.4 : CW;
      const word = this.up(o.title, "display");
      const fsz = this._fitSize(word, tw, 3.0, this.size.section, this.F.display, true, 40);
      const th = (this._lines(word, tw, fsz, this.F.display, true) * fsz * 1.02) / 72;
      const ty = Math.max(1.6, (H - th) / 2 - 0.3);
      const num = o.number && this._txt(s, ctx, `${this.L.part} ${o.number}`.toUpperCase(), { x: M, y: ty - 0.6, w: tw, h: 0.4, fontSize: 14, bold: true, charSpacing: 3, color: c.ink, align: center ? "center" : "left", objectName: "kicker", fit: false });
      this._txt(s, ctx, word, { x: M, y: ty, w: tw, h: th + 0.1, font: "display", fontSize: fsz, bold: true, italic: !!this.F.displayItalic, color: center ? c.ink : c.text, align: center ? "center" : "left", lineSpacingMultiple: 0.9, objectName: "title", fit: false });
      const sub = o.subtitle && this._txt(s, ctx, o.subtitle, { x: M, y: ty + th + 0.25, w: center ? CW : 7.4, h: 1.0, fontSize: 18, color: c.muted, align: center ? "center" : "left", objectName: "subtitle" });
      const hero = art ? await this._hero(s, ctx, W - M - 3.6, (H - 3.6) / 2, 3.6) : [];
      ctx.step(hero, "emph"); ctx.step([num, sub].filter(Boolean));
    });
  }

  statement(o) {
    return this._queue(async () => {
      const ctx = this._new("statement", o, "PX_PLAIN"), { s } = ctx, c = this.c;
      this._chrome(s, ctx, o.kicker);
      let runs = [{ text: this.up(o.text) }];
      if (o.highlight && o.text.includes(o.highlight)) { const [a, ...rest] = o.text.split(o.highlight); runs = [{ text: this.up(a) }, { text: this.up(o.highlight), options: { color: c.ink } }, { text: this.up(rest.join(o.highlight)) }].filter((r) => r.text); }
      const plain = runs.map((r) => r.text).join("");
      const fsz = this._fitSize(plain, 10.8, 3.0, Math.round(this.size.title * 1.35), this.F.head, true, 26);
      const th = (this._lines(plain, 10.8, fsz, this.F.head, true) * fsz * 1.15) / 72;
      const y = (H - th) / 2 - 0.35;
      this._txt(s, ctx, runs.map((r) => ({ text: r.text, options: { ...(r.options || {}) } })), { x: M, y, w: 10.8, h: th + 0.1, font: "head", fontSize: fsz, bold: true, color: c.text, objectName: "statement", fit: false });
      const sup = o.support && this._txt(s, ctx, o.support, { x: M, y: y + th + 0.35, w: 9.5, h: 1.0, fontSize: 18, color: c.muted, objectName: "support" });
      ctx.step(sup);
    });
  }

  cards(o) {
    return this._queue(async () => {
      const ctx = this._new("cards", o), { s } = ctx;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      const items = o.items || [], n = items.length, cols = n <= 4 ? n : 3, rows = Math.ceil(n / cols), gap = 0.3;
      const w = (CW - gap * (cols - 1)) / cols, compact = rows > 1;
      const tw = w - 0.7;
      const headH = Math.max(...items.map((it) => this._need(this.up(it.head), tw, 18, true, this.F.head))) + 0.08;
      const textH = Math.max(...items.map((it) => this._need(it.text, tw, 14, false)));
      const top = compact ? 0.95 : 1.35;
      const h = compact ? (CH - gap) / 2 : Math.min(CH - 0.1, Math.max(2.8, top + headH + textH + 0.45));
      const y0 = compact ? Y0 : Y0 + Math.max(0, (CH - h) / 2 - 0.1);
      for (let i = 0; i < n; i++) {
        const it = items[i], x = M + (i % cols) * (w + gap), y = y0 + Math.floor(i / cols) * (h + gap);
        const { names, inside } = this._card(s, x, y, w, h, `cd${i}`, { emphasis: !!it.highlight });
        const isz = compact ? 0.55 : 0.78;
        names.push(...(await this._icon(s, it, x + 0.35, y + 0.32, isz, `cd${i}i`)));
        const hy = y + (it.icon || it.obj ? (compact ? 0.32 + isz + 0.18 : top) : 0.35);
        names.push(this._txt(s, ctx, this.up(it.head), { x: x + 0.35, y: hy, w: tw, h: headH, font: "head", fontSize: 18, bold: true, color: inside.text, objectName: `cd${i}h` }));
        if (it.text) names.push(this._txt(s, ctx, it.text, { x: x + 0.35, y: hy + headH, w: tw, h: y + h - (hy + headH) - 0.2, fontSize: 14, color: inside.muted, objectName: `cd${i}t` }));
        ctx.step(names);
      }
    });
  }

  // Bento grid (Ivan Volti style). items: {type:'hero'|'stat'|'feature'|'chips'|'people'|'image'|'quote', ...}
  bento(o) {
    return this._queue(async () => {
      const ctx = this._new("bento", o), { s } = ctx, c = this.c, S = this.pres.shapes;
      this._chrome(s, ctx, o.kicker); const th = this._title(s, ctx, o.title);
      const items = o.items || []; const n = items.length;
      const P = { 3: [[0, 0, 2, 3], [2, 0, 2, 2], [2, 2, 2, 1]], 4: [[0, 0, 2, 3], [2, 0, 2, 1], [2, 1, 1, 2], [3, 1, 1, 2]], 5: [[1, 0, 2, 2], [0, 0, 1, 3], [3, 0, 1, 1], [3, 1, 1, 2], [1, 2, 2, 1]], 6: [[1, 0, 2, 2], [0, 0, 1, 2], [3, 0, 1, 1], [3, 1, 1, 2], [0, 2, 1, 1], [1, 2, 2, 1]], 7: [[1, 0, 2, 2], [0, 0, 1, 2], [3, 0, 1, 1], [3, 1, 1, 2], [0, 2, 1, 1], [1, 2, 1, 1], [2, 2, 1, 1]] }[Math.min(7, Math.max(3, n))];
      if (!P) throw new Error("bento takes 3 to 7 items");
      const top = o.title ? Y0 - 0.15 : 0.9, gap = 0.22, gh = Y1 - top, cw = (CW - gap * 3) / 4, rh = (gh - gap * 2) / 3;
      const heroIdx = Math.max(0, items.findIndex((it) => it.type === "hero"));
      const order = [heroIdx, ...items.map((_, i) => i).filter((i) => i !== heroIdx)];
      for (let k = 0; k < Math.min(n, P.length); k++) {
        const it = items[order[k]], [cx, cy, sw, sh] = P[k];
        const x = M + cx * (cw + gap), y = top + cy * (rh + gap), w = sw * cw + (sw - 1) * gap, h = sh * rh + (sh - 1) * gap;
        const isHero = it.type === "hero";
        const { names, inside } = this._card(s, x, y, w, h, `bt${k}`, { emphasis: isHero, fill: isHero && this.st.card.kind !== "tile" ? c.primary : null });
        const pad = 0.3;
        if (isHero) {
          const tTop = y + (it.kicker ? 0.7 : 0.4), tH = h * 0.36;
          if (it.obj || this.st.hero?.kind === "3d") { const room = y + h - (tTop + tH) - 0.1; const sz = Math.min(w * 0.6, room); if (sz > 0.6) { await this._img(s, objPath(it.obj || this._heroName()), { x: x + (w - sz) / 2, y: y + h - sz - 0.08, w: sz, h: sz, objectName: `bt${k}o` }); names.push(`bt${k}o`); } }
          if (it.kicker) names.push(this._txt(s, ctx, it.kicker, { x: x + pad, y: y + 0.3, w: w - 2 * pad, h: 0.35, fontSize: 13, bold: true, color: inside.text, align: "center", objectName: `bt${k}k`, fit: false }));
          names.push(this._txt(s, ctx, it.title, { x: x + pad, y: tTop, w: w - 2 * pad, h: tH, font: "display", fontSize: this._fitSize(it.title, w - 2 * pad, tH, 40, this.F.display, true, 20), bold: true, color: inside.text, align: "center", objectName: `bt${k}t`, fit: false }));
        } else if (it.type === "stat") {
          const vsz = this._fitSize(String(it.value), w - 2 * pad, Math.min(1.0, h * 0.5), Math.min(54, h * 26), this.F.display, true, 20);
          names.push(this._txt(s, ctx, String(it.value), { x: x + pad, y: y + h / 2 - 0.75, w: w - 2 * pad, h: 0.9, font: "display", fontSize: vsz, bold: true, color: it.accent ? c.accent : inside.ink, align: "center", valign: "bottom", objectName: `bt${k}v`, wrap: false, fit: false, glow: this.dark ? { size: 10, opacity: 0.3, color: it.accent ? c.accent : c.primary } : undefined }));
          names.push(this._txt(s, ctx, it.label || "", { x: x + pad, y: y + h / 2 + 0.2, w: w - 2 * pad, h: 0.5, fontSize: 14, color: inside.muted, align: "center", objectName: `bt${k}l` }));
        } else if (it.type === "chips") {
          names.push(this._txt(s, ctx, it.head || "", { x: x + pad, y: y + 0.28, w: w - 2 * pad, h: 0.4, fontSize: 16, bold: true, color: inside.text, objectName: `bt${k}h` }));
          let cx2 = x + pad, cy2 = y + 0.85;
          (it.items || []).forEach((t, j) => { const cwid = 0.35 + t.length * 0.09; if (cx2 + cwid > x + w - pad) { cx2 = x + pad; cy2 += 0.48; } if (cy2 > y + h - 0.5) return; s.addShape(S.ROUNDED_RECTANGLE, { x: cx2, y: cy2, w: cwid, h: 0.38, rectRadius: 0.5, fill: { color: j % 2 ? c.accent : c.primary, transparency: 75 }, line: { color: j % 2 ? c.accent : c.primary, width: 1 }, objectName: `bt${k}c${j}` }); this._txt(s, ctx, t, { x: cx2, y: cy2, w: cwid, h: 0.38, fontSize: 12, color: inside.text, align: "center", valign: "middle", objectName: `bt${k}ct${j}`, fit: false }); names.push(`bt${k}c${j}`, `bt${k}ct${j}`); cx2 += cwid + 0.12; });
        } else if (it.type === "people") {
          const ph = it.photos || [], cnt = Math.min(4, ph.length || 3), sz = Math.min(0.75, h * 0.42), row = w > h * 1.6;
          const vx = row ? x + pad : x + pad, vw = row ? w * 0.45 : w - 2 * pad;
          names.push(this._txt(s, ctx, String(it.value || ""), { x: vx, y: row ? y + h / 2 - 0.55 : y + 0.2, w: vw, h: 0.7, font: "display", fontSize: Math.min(40, h * 22), bold: true, color: c.accent, align: row ? "left" : "center", objectName: `bt${k}v`, wrap: false, fit: false }));
          names.push(this._txt(s, ctx, it.label || "", { x: vx, y: row ? y + h / 2 + 0.12 : y + 0.85, w: vw, h: 0.4, fontSize: 13, color: inside.muted, align: row ? "left" : "center", objectName: `bt${k}l` }));
          const ax0 = row ? x + w - pad - (cnt * sz * 0.72 + sz * 0.28) : x + w / 2 - (cnt * sz * 0.72 + sz * 0.28) / 2, ay = row ? y + (h - sz) / 2 : y + h - sz - 0.25;
          for (let j = 0; j < cnt; j++) { const px = ax0 + j * sz * 0.72; if (ph[j]) { const d = await roundedImage(ph[j], sz, sz, sz / 2); await this._img(s, d, { x: px, y: ay, w: sz, h: sz, objectName: `bt${k}p${j}` }); } else s.addShape(S.OVAL, { x: px, y: ay, w: sz, h: sz, fill: { color: j % 2 ? c.accent : c.primary }, line: { color: c.surface, width: 2 }, objectName: `bt${k}p${j}` }); names.push(`bt${k}p${j}`); }
        } else if (it.type === "image") {
          const d = await roundedImage(it.path, w - 0.24, h - 0.24, Math.max(0.05, (this.st.card.radius || 0.14) - 0.06)); await this._img(s, d, { x: x + 0.12, y: y + 0.12, w: w - 0.24, h: h - 0.24, objectName: `bt${k}img` }); names.push(`bt${k}img`);
        } else {
          const hasIcon = it.icon || it.obj; const row = h < 1.9 && hasIcon; const isz = row ? Math.min(0.6, h - 0.5) : 0.6;
          const tx = row ? x + pad + isz + 0.2 : x + pad, tw2 = w - (tx - x) - pad;
          const hh = this._need(it.head, tw2, 16, true) + 0.05, thh = it.text ? this._need(it.text, tw2, 13) + 0.05 : 0;
          const textY = row ? y + (h - hh - thh) / 2 : y + h - pad - hh - thh;
          if (hasIcon) names.push(...(await this._icon(s, it, x + pad, row ? y + (h - isz) / 2 : y + pad, isz, `bt${k}i`, k % 2 ? c.accent : c.primary)));
          names.push(this._txt(s, ctx, it.head || "", { x: tx, y: textY, w: tw2, h: hh, fontSize: 16, bold: true, color: inside.text, objectName: `bt${k}h` }));
          if (it.text) names.push(this._txt(s, ctx, it.text, { x: tx, y: textY + hh, w: tw2, h: thh, fontSize: 13, color: inside.muted, objectName: `bt${k}t` }));
        }
        ctx.step(names, isHero ? "emph" : "item");
      }
    });
  }

  stats(o) {
    return this._queue(async () => {
      const ctx = this._new("stats", o), { s } = ctx, c = this.c;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      const items = o.items || [], n = items.length, gap = 0.3, w = (CW - gap * (n - 1)) / n, h = o.source ? 3.9 : 4.2;
      items.forEach((it, i) => {
        const x = M + i * (w + gap), y = Y0 + 0.05;
        const { names, inside } = this._card(s, x, y, w, h, `st${i}`, { emphasis: !!it.highlight });
        const v = String(it.value); const vs = this._fitSize(v, w - 0.7, 1.3, this.size.stat, this.F.display, true, 30);
        names.push(this._txt(s, ctx, v, { x: x + 0.35, y: y + 0.35, w: w - 0.7, h: 1.35, font: "display", fontSize: vs, bold: true, color: it.highlight ? c.accent : inside.ink, valign: "bottom", objectName: `st${i}v`, wrap: false, fit: false, glow: this.dark ? { size: 12, opacity: 0.35, color: it.highlight ? c.accent : c.primary } : undefined }));
        names.push(this._txt(s, ctx, it.label, { x: x + 0.35, y: y + 1.85, w: w - 0.7, h: 0.75, fontSize: 18, bold: true, color: inside.text, objectName: `st${i}l` }));
        if (it.note) names.push(this._txt(s, ctx, it.note, { x: x + 0.35, y: y + 2.6, w: w - 0.7, h: h - 2.85, fontSize: 14, color: inside.muted, objectName: `st${i}n` }));
        ctx.step(names, "emph");
      });
      if (o.source) this._txt(s, ctx, `${this.L.source}: ${o.source}`, { x: M, y: Y1 - 0.2, w: CW, h: 0.3, fontSize: 11, italic: true, color: c.muted, objectName: "source" });
    });
  }

  // KPI dashboard: rings, number tiles with deltas, trend sparkline
  kpi(o) {
    return this._queue(async () => {
      const ctx = this._new("kpi", o), { s } = ctx, c = this.c, S = this.pres.shapes;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      const gap = 0.25, ringW = 3.6, rest = CW - ringW - gap, colW = (rest - gap) / 2, rowH = (CH - gap) / 2;
      const ring = o.ring || (o.rings && o.rings[0]);
      if (ring) {
        const { names, inside } = this._card(s, M, Y0, ringW, CH, "kr");
        const d = 2.6, rx = M + (ringW - d) / 2, ry = Y0 + 0.45; const pct = Math.max(0, Math.min(100, ring.value)) / 100;
        s.addShape(S.BLOCK_ARC, { x: rx, y: ry, w: d, h: d, angleRange: [0, 359.9], arcThicknessRatio: 0.16, fill: { color: c.primary, transparency: 80 }, line: { color: c.primary, width: 0, transparency: 100 }, objectName: "krt" });
        s.addShape(S.BLOCK_ARC, { x: rx, y: ry, w: d, h: d, angleRange: [270, (270 + pct * 359.9) % 360], arcThicknessRatio: 0.16, fill: { color: ring.color || c.primary }, line: { color: c.primary, width: 0, transparency: 100 }, objectName: "kra" });
        names.push("krt", "kra");
        names.push(this._txt(s, ctx, ring.display || `${ring.value}%`, { x: rx, y: ry + d / 2 - 0.45, w: d, h: 0.7, font: "display", fontSize: 40, bold: true, color: inside.text, align: "center", valign: "middle", objectName: "krv", wrap: false, fit: false }));
        names.push(this._txt(s, ctx, ring.label || "", { x: M + 0.3, y: ry + d + 0.3, w: ringW - 0.6, h: CH - d - 1.0, fontSize: 15, color: inside.muted, align: "center", objectName: "krl" }));
        ctx.step(names, "emph");
      }
      const tiles = (o.tiles || []).slice(0, 4);
      const hasTrend = !!o.trend; const slots = hasTrend ? [[0, 0], [1, 0]] : [[0, 0], [1, 0], [0, 1], [1, 1]];
      const tx0 = ring ? M + ringW + gap : M, tw = ring ? colW : (CW - gap) / 2;
      for (let i = 0; i < Math.min(tiles.length, slots.length); i++) {
        const t = tiles[i], [cx, cy] = slots[i], x = tx0 + cx * (tw + gap), y = Y0 + cy * (rowH + gap);
        const { names, inside } = this._card(s, x, y, tw, rowH, `kt${i}`);
        names.push(this._txt(s, ctx, t.label, { x: x + 0.3, y: y + 0.25, w: tw - 0.6, h: 0.4, fontSize: 14, color: inside.muted, objectName: `kt${i}l` }));
        names.push(this._txt(s, ctx, String(t.value), { x: x + 0.3, y: y + 0.65, w: tw - 0.6, h: 0.9, font: "display", fontSize: 44, bold: true, color: i % 2 ? c.accent : inside.ink, objectName: `kt${i}v`, wrap: false, fit: false, glow: this.dark ? { size: 10, opacity: 0.3, color: i % 2 ? c.accent : c.primary } : undefined }));
        if (t.delta) { const up = !String(t.delta).trim().startsWith("-"); const col = (t.good ?? up) ? "34D399" : "F87171"; s.addShape(S.ROUNDED_RECTANGLE, { x: x + 0.3, y: y + rowH - 0.6, w: 1.25, h: 0.36, rectRadius: 0.5, fill: { color: col, transparency: 80 }, line: { color: col, width: 0.75 }, objectName: `kt${i}d` }); this._txt(s, ctx, `${up ? "▲" : "▼"} ${String(t.delta).replace(/^[-+]/, "")}`, { x: x + 0.3, y: y + rowH - 0.6, w: 1.25, h: 0.36, fontSize: 12, bold: true, color: this.dark ? col : mix(col, "000000", 0.35), align: "center", valign: "middle", objectName: `kt${i}dt`, fit: false }); names.push(`kt${i}d`, `kt${i}dt`); }
        ctx.step(names, "emph");
      }
      if (hasTrend) {
        const x = tx0, y = Y0 + rowH + gap, w = ring ? rest : CW;
        const { names, inside } = this._card(s, x, y, w, rowH, "ktr");
        names.push(this._txt(s, ctx, o.trend.label || "", { x: x + 0.3, y: y + 0.22, w: w - 0.6, h: 0.4, fontSize: 14, color: inside.muted, objectName: "ktrl" }));
        const f = path.join(this.tmp, `spark${ctx.n}.png`); fs.writeFileSync(f, await BG.sparkline(o.trend.values, o.trend.color || c.accent, { w: Math.round((w - 0.6) * 150), h: Math.round((rowH - 0.85) * 150) }));
        await this._img(s, f, { x: x + 0.3, y: y + 0.65, w: w - 0.6, h: rowH - 0.85, objectName: "ktrs" }); names.push("ktrs");
        ctx.step(names, "line");
      }
    });
  }

  // Native chart, styled after writing (gradient bars, glow lines, highlighted point)
  chart(o) {
    return this._queue(async () => {
      const ctx = this._new("chart", o), { s } = ctx, c = this.c, p = this.pres;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      const tk = o.takeaway, cw = tk ? 7.9 : CW, chh = o.source ? CH - 0.35 : CH;
      const types = { bar: p.charts.BAR, column: p.charts.BAR, line: p.charts.LINE, area: p.charts.AREA, pie: p.charts.PIE, doughnut: p.charts.DOUGHNUT };
      const type = o.type || "column"; if (!types[type]) throw new Error(`chart type: ${Object.keys(types).join(", ")}`);
      const data = o.data || [], multi = data.length > 1, round = ["pie", "doughnut"].includes(type), pts = data[0] ? data[0].values.length : 0;
      const series = this.st.series || [c.primary, c.accent];
      const grid = mix(c.muted, c.bg, 0.6);
      const opt = {
        x: M, y: Y0, w: cw, h: chh, objectName: "chart",
        chartColors: (round ? series : multi ? series : [c.primary]).slice(0, Math.max(data.length, round ? pts : 1)),
        catAxisLabelColor: c.muted, valAxisLabelColor: c.muted, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
        catAxisLineShow: false, valAxisLineShow: false, valGridLine: { color: grid, size: 0.5 }, catGridLine: { style: "none" },
        showValue: !multi && pts <= 12 && !["line", "area"].includes(type), dataLabelColor: round ? c.onPrimary : c.text, dataLabelFontSize: 12, dataLabelFontFace: "+mn-lt", dataLabelFontBold: true,
        showLegend: multi || round, legendPos: "b", legendColor: c.muted, legendFontFace: "+mn-lt", legendFontSize: 12,
        valAxisLabelFormatCode: o.format || "General", dataLabelFormatCode: o.format || "General",
      };
      if (type === "bar" || type === "column") { opt.barDir = type === "bar" ? "bar" : "col"; opt.barGapWidthPct = 45; opt.dataLabelPosition = "outEnd"; }
      if (type === "line") { opt.lineSize = 3; opt.lineDataSymbol = "circle"; opt.lineDataSymbolSize = 8; }
      if (round) { opt.showPercent = !o.showValue; opt.showValue = !!o.showValue; opt.dataLabelPosition = "bestFit"; opt.holeSize = 62; opt.dataBorder = { pt: 2, color: c.bg }; }
      if (o.chartOptions) Object.assign(opt, o.chartOptions);
      s.addChart(types[type], data, opt);
      this.charts.push({ type, highlight: o.highlight, colors: opt.chartColors, accent: c.accent, glow: this.dark, horizontal: type === "bar", gradient: o.gradient !== false });
      ctx.step("chart");
      if (round && o.center) { this._txt(s, ctx, o.center.value, { x: M + cw / 2 - 1.2, y: Y0 + chh / 2 - 0.6, w: 2.4, h: 0.7, font: "display", fontSize: 36, bold: true, color: c.text, align: "center", valign: "middle", objectName: "ctrv", fit: false }); if (o.center.label) this._txt(s, ctx, o.center.label, { x: M + cw / 2 - 1.2, y: Y0 + chh / 2 + 0.05, w: 2.4, h: 0.4, fontSize: 12, color: c.muted, align: "center", objectName: "ctrl", fit: false }); }
      if (tk) {
        const x = M + cw + 0.35, w = CW - cw - 0.35;
        const { names, inside } = this._card(s, x, Y0 + 0.1, w, chh - 0.2, "tk", { emphasis: true });
        if (tk.value) names.push(this._txt(s, ctx, tk.value, { x: x + 0.35, y: Y0 + 0.45, w: w - 0.7, h: 1.1, font: "display", fontSize: this._fitSize(tk.value, w - 0.7, 1.1, 54, this.F.display, true, 30), bold: true, color: c.accent, valign: "bottom", objectName: "tkv", wrap: false, fit: false, glow: this.dark ? { size: 12, opacity: 0.35, color: c.accent } : undefined }));
        if (tk.label) names.push(this._txt(s, ctx, tk.label, { x: x + 0.35, y: Y0 + 1.65, w: w - 0.7, h: 0.75, fontSize: 17, bold: true, color: inside.text, objectName: "tkl" }));
        if (tk.text) names.push(this._txt(s, ctx, tk.text, { x: x + 0.35, y: Y0 + 2.45, w: w - 0.7, h: chh - 2.8, fontSize: 14, color: inside.muted, objectName: "tkt" }));
        ctx.step(names, "emph");
      }
      if (o.source) this._txt(s, ctx, `${this.L.source}: ${o.source}`, { x: M, y: Y1 - 0.2, w: CW, h: 0.3, fontSize: 11, italic: true, color: c.muted, objectName: "source" });
    });
  }

  // Curved roadmap with milestones; `current` = index of the milestone in progress
  roadmap(o) {
    return this._queue(async () => {
      const ctx = this._new("roadmap", o), { s } = ctx, c = this.c, S = this.pres.shapes;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      const st = o.steps || [], n = st.length; if (n < 2) throw new Error("roadmap needs 2+ steps");
      const x0 = M + 0.3, x1 = W - M - 0.3, ymid = Y0 + CH / 2 + 0.05, amp = 0.55;
      const f = (t) => ymid + amp * Math.sin(t * Math.PI * (n > 4 ? 2 : 1.5) + 0.4);
      const N = 80, pts = [...Array(N + 1)].map((_, i) => { const t = i / N; return { x: x0 + t * (x1 - x0), y: f(t) }; });
      const bx = x0, by = Math.min(...pts.map((p) => p.y)) - 0.1, bw = x1 - x0, bh = Math.max(...pts.map((p) => p.y)) - by + 0.1;
      const rel = (arr) => arr.map((p, i) => ({ x: p.x - bx, y: p.y - by, ...(i === 0 ? { moveTo: true } : {}) }));
      this._shape(s, S.CUSTOM_GEOMETRY || "custGeom", { x: bx, y: by, w: bw, h: bh, points: rel(pts), line: { color: c.muted, width: 6, transparency: 70, dashType: "solid" }, fill: { type: "none" }, objectName: "rdbase" });
      const cur = o.current ?? -1; const tCur = cur < 0 ? 0 : (cur + 0.5) / n;
      const done = pts.filter((p) => (p.x - x0) / (x1 - x0) <= tCur);
      if (done.length > 1) this._shape(s, S.CUSTOM_GEOMETRY || "custGeom", { x: bx, y: by, w: bw, h: bh, points: rel(done), line: { color: c.accent, width: 6 }, fill: { type: "none" }, objectName: "rddone" });
      ctx.step(["rdbase", done.length > 1 ? "rddone" : null], "line");
      for (let i = 0; i < n; i++) {
        const t = (i + 0.5) / n, x = x0 + t * (x1 - x0), y = f(t), it = st[i], isCur = i === cur, isDone = i < cur;
        const d = isCur ? 0.62 : 0.5, col = isCur ? c.accent : isDone ? c.primary : mix(c.muted, c.bg, 0.3);
        s.addShape(S.OVAL, { x: x - d / 2, y: y - d / 2, w: d, h: d, fill: { color: col }, line: { color: this.dark ? c.bg : "FFFFFF", width: 3 }, shadow: isCur ? { type: "outer", color: c.accent, opacity: 0.6, blur: 14, offset: 0, angle: 0 } : undefined, objectName: `rd${i}d` });
        const names = [`rd${i}d`];
        if (it.icon) { const ic = await renderIcon(it.icon, this.best(col, ["FFFFFF", "111111"]), true); s.addImage({ data: ic, x: x - d * 0.28, y: y - d * 0.28, w: d * 0.56, h: d * 0.56, objectName: `rd${i}i` }); names.push(`rd${i}i`); }
        const above = y > ymid - 0.05 ? true : false; const colW = (x1 - x0) / n - 0.1;
        const ly = above ? y - d / 2 - 1.45 : y + d / 2 + 0.15;
        names.push(this._txt(s, ctx, it.label || "", { x: x - colW / 2, y: ly, w: colW, h: 0.35, fontSize: 12, bold: true, charSpacing: 1, color: isCur ? c.accent : c.ink, align: "center", objectName: `rd${i}l`, fit: false }));
        names.push(this._txt(s, ctx, it.head, { x: x - colW / 2, y: ly + 0.34, w: colW, h: 0.45, fontSize: 16, bold: true, color: c.text, align: "center", objectName: `rd${i}h` }));
        if (it.text) names.push(this._txt(s, ctx, it.text, { x: x - colW / 2, y: ly + 0.8, w: colW, h: 0.6, fontSize: 12, color: c.muted, align: "center", objectName: `rd${i}t` }));
        ctx.step(names);
      }
    });
  }

  // Straight colorful timeline (pastel milestones), alternating labels
  timeline(o) {
    return this._queue(async () => {
      const ctx = this._new("timeline", o), { s } = ctx, c = this.c, S = this.pres.shapes;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      const st = o.steps || [], n = st.length, cols = this.st.series, ay = Y0 + CH / 2, colW = CW / n;
      ctx.step(this._shape(s, S.LINE, { x: M, y: ay, w: CW, h: 0, line: { color: c.muted, width: 2, transparency: 50 }, objectName: "tlaxis" }), "line");
      for (let i = 0; i < n; i++) {
        const it = st[i], x = M + i * colW + colW / 2, col = cols[i % cols.length], up = i % 2 === 0;
        const names = [];
        s.addShape(S.OVAL, { x: x - 0.22, y: ay - 0.22, w: 0.44, h: 0.44, fill: { color: col }, line: { color: this.dark ? c.bg : "FFFFFF", width: 3 }, objectName: `tl${i}d` }); names.push(`tl${i}d`);
        s.addShape(S.LINE, { x, y: up ? ay - 0.75 : ay + 0.22, w: 0, h: 0.53, line: { color: col, width: 1.5 }, objectName: `tl${i}s` }); names.push(`tl${i}s`);
        const by = up ? ay - 1.18 : ay + 0.78;
        s.addShape(S.ROUNDED_RECTANGLE, { x: x - 0.62, y: by, w: 1.24, h: 0.42, rectRadius: 0.5, fill: { color: col }, line: { color: col, width: 0 }, objectName: `tl${i}b` });
        names.push(`tl${i}b`, this._txt(s, ctx, it.label || "", { x: x - 0.62, y: by, w: 1.24, h: 0.42, fontSize: 12, bold: true, color: this.best(col, ["111111", "FFFFFF"]), align: "center", valign: "middle", objectName: `tl${i}bl`, fit: false }));
        const ty = up ? by - 1.15 : by + 0.55;
        names.push(this._txt(s, ctx, it.head, { x: x - colW / 2 + 0.08, y: ty, w: colW - 0.16, h: 0.42, fontSize: 15, bold: true, color: c.text, align: "center", objectName: `tl${i}h` }));
        if (it.text) names.push(this._txt(s, ctx, it.text, { x: x - colW / 2 + 0.08, y: ty + 0.42, w: colW - 0.16, h: 0.65, fontSize: 12, color: c.muted, align: "center", objectName: `tl${i}t` }));
        ctx.step(names);
      }
    });
  }

  process(o) {
    return this._queue(async () => {
      const ctx = this._new("process", o), { s } = ctx, c = this.c, S = this.pres.shapes;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      const st = o.steps || [], n = st.length, gap = 0.5, w = (CW - gap * (n - 1)) / n;
      const headH = Math.max(...st.map((x) => this._need(x.head, w - 0.6, 17, true))) + 0.08, textH = Math.max(...st.map((x) => this._need(x.text, w - 0.6, 13)));
      const h = Math.min(CH, Math.max(2.6, 1.25 + headH + textH + 0.4)), y = Y0 + Math.max(0, (CH - h) / 2 - 0.1);
      for (let i = 0; i < n; i++) {
        const it = st[i], x = M + i * (w + gap);
        const { names, inside } = this._card(s, x, y, w, h, `pr${i}`, { emphasis: !!it.highlight });
        if (it.icon || it.obj) names.push(...(await this._icon(s, it, x + 0.3, y + 0.3, 0.62, `pr${i}i`)));
        else names.push(this._txt(s, ctx, String(i + 1).padStart(2, "0"), { x: x + 0.3, y: y + 0.28, w: 1.2, h: 0.65, font: "display", fontSize: 30, bold: true, color: inside.ink, objectName: `pr${i}n`, fit: false }));
        names.push(this._txt(s, ctx, this.up(it.head), { x: x + 0.3, y: y + 1.15, w: w - 0.6, h: headH, font: "head", fontSize: 17, bold: true, color: inside.text, objectName: `pr${i}h` }));
        if (it.text) names.push(this._txt(s, ctx, it.text, { x: x + 0.3, y: y + 1.15 + headH, w: w - 0.6, h: h - 1.35 - headH, fontSize: 13, color: inside.muted, objectName: `pr${i}t` }));
        if (i < n - 1) { s.addShape(S.CHEVRON, { x: x + w + gap / 2 - 0.12, y: y + h / 2 - 0.14, w: 0.24, h: 0.28, fill: { color: c.ink }, line: { color: c.ink, width: 0 }, objectName: `pr${i}a` }); names.push(`pr${i}a`); }
        ctx.step(names);
      }
    });
  }

  compare(o) {
    return this._queue(async () => {
      const ctx = this._new("compare", o), { s } = ctx, c = this.c;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      const w = (CW - 0.4) / 2, h = CH;
      for (const [k, side, good] of [[0, o.left || {}, false], [1, o.right || {}, true]]) {
        const x = M + k * (w + 0.4), id = good ? "R" : "L";
        const { names, inside } = this._card(s, x, Y0, w, h, `cmp${id}`, { emphasis: good });
        names.push(this._txt(s, ctx, String(side.tag || (good ? this.L.target : this.L.today)).toUpperCase(), { x: x + 0.4, y: Y0 + 0.32, w: w - 0.8, h: 0.35, fontSize: 12, bold: true, charSpacing: 2, color: good ? c.accent : inside.muted, objectName: `cmp${id}k`, fit: false }));
        names.push(this._txt(s, ctx, this.up(side.head || ""), { x: x + 0.4, y: Y0 + 0.7, w: w - 0.8, h: 0.6, font: "head", fontSize: 24, bold: true, color: inside.text, objectName: `cmp${id}h` }));
        const items = side.items || [], rowH = Math.min(0.72, (h - 1.7) / Math.max(1, items.length));
        const ic = await renderIcon(good ? "LuCheck" : "LuMinus", good ? c.accent : c.muted);
        items.forEach((t, i) => { const iy = Y0 + 1.55 + i * rowH; s.addImage({ data: ic, x: x + 0.4, y: iy + 0.04, w: 0.28, h: 0.28, objectName: `cmp${id}${i}i` }); names.push(`cmp${id}${i}i`, this._txt(s, ctx, t, { x: x + 0.85, y: iy, w: w - 1.25, h: rowH - 0.05, fontSize: 16, color: inside.text, objectName: `cmp${id}${i}t` })); });
        ctx.step(names);
      }
    });
  }

  // layers: [{name, items:[str|{text,highlight}]}]  or  groups: [{name, items:[...]}] (left→right with arrows)
  architecture(o) {
    return this._queue(async () => {
      const ctx = this._new("architecture", o), { s } = ctx, c = this.c, S = this.pres.shapes;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      if (o.groups) {
        const g = o.groups, n = g.length, gap = 0.55, w = (CW - gap * (n - 1)) / n;
        for (let i = 0; i < n; i++) {
          const x = M + i * (w + gap), it = g[i]; const em = !!it.highlight;
          const { names, inside } = this._card(s, x, Y0, w, CH, `ag${i}`, { emphasis: em });
          names.push(this._txt(s, ctx, String(it.name).toUpperCase(), { x: x + 0.25, y: Y0 + 0.22, w: w - 0.5, h: 0.35, fontSize: 12, bold: true, charSpacing: 2, color: em ? c.accent : inside.ink, objectName: `ag${i}n`, wrap: false, fit: false }));
          const items = it.items || [], ih = Math.min(0.75, (CH - 0.9 - 0.15 * (items.length - 1)) / Math.max(1, items.length));
          items.forEach((t, j) => { const txt = typeof t === "string" ? t : t.text, hi = typeof t !== "string" && t.highlight; const yy = Y0 + 0.75 + j * (ih + 0.15);
            s.addShape(S.ROUNDED_RECTANGLE, { x: x + 0.25, y: yy, w: w - 0.5, h: ih, rectRadius: 0.2, fill: { color: hi ? c.accent : (this.dark ? mix(c.bg, "FFFFFF", 0.08) : "FFFFFF") }, line: { color: hi ? c.accent : c.primary, width: 0.75, transparency: hi ? 0 : 50 }, objectName: `ag${i}_${j}` });
            names.push(`ag${i}_${j}`, this._txt(s, ctx, txt, { x: x + 0.3, y: yy, w: w - 0.6, h: ih, fontSize: 14, bold: !!hi, color: hi ? this.best(c.accent) : c.text, align: "center", valign: "middle", objectName: `ag${i}_${j}t`, fit: false })); });
          if (i < n - 1) { s.addShape(S.LINE, { x: x + w + 0.08, y: Y0 + CH / 2, w: gap - 0.16, h: 0, line: { color: c.ink, width: 2, endArrowType: "triangle", beginArrowType: o.bidirectional ? "triangle" : undefined }, objectName: `ag${i}a` }); names.push(`ag${i}a`); }
          ctx.step(names);
        }
        return;
      }
      const L = o.layers || [], n = L.length, gap = 0.16, bh = Math.min(1.1, (CH - gap * (n - 1)) / n), lw = 2.6;
      const groups = [];
      L.forEach((ly, i) => {
        const y = Y0 + i * (bh + gap); const { names, inside } = this._card(s, M, y, CW, bh, `ar${i}`);
        names.push(this._txt(s, ctx, ly.name, { x: M + 0.3, y, w: lw - 0.3, h: bh, fontSize: 14, bold: true, color: inside.ink, valign: "middle", objectName: `ar${i}l` }));
        const items = ly.items || [], k = items.length, cg = 0.16, cx0 = M + lw, cwid = CW - lw - 0.25, chipW = (cwid - cg * (k - 1)) / Math.max(1, k), chipH = bh - 0.32;
        items.forEach((t, j) => { const txt = typeof t === "string" ? t : t.text, hi = typeof t !== "string" && t.highlight; const x = cx0 + j * (chipW + cg);
          s.addShape(S.ROUNDED_RECTANGLE, { x, y: y + 0.16, w: chipW, h: chipH, rectRadius: 0.2, fill: { color: hi ? c.primary : (this.dark ? mix(c.bg, "FFFFFF", 0.06) : "FFFFFF") }, line: { color: hi ? c.primary : c.primary, width: 0.75, transparency: hi ? 0 : 55 }, objectName: `ar${i}_${j}` });
          names.push(`ar${i}_${j}`, this._txt(s, ctx, txt, { x: x + 0.06, y: y + 0.16, w: chipW - 0.12, h: chipH, fontSize: 13, bold: !!hi, color: hi ? c.onPrimary : c.text, align: "center", valign: "middle", objectName: `ar${i}_${j}t`, fit: false })); });
        groups[i] = names;
      });
      (o.build === "up" ? [...groups.keys()].reverse() : [...groups.keys()]).forEach((i) => ctx.step(groups[i]));
    });
  }

  // Device mockups: device = laptop | phone | browser | tablet | phones (screens: [paths])
  mockup(o) {
    return this._queue(async () => {
      const ctx = this._new("mockup", o, "PX_SPLIT"), { s } = ctx, c = this.c, S = this.pres.shapes;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title, [5.6, 1.5, this.size.title]);
      const dev = o.device || "laptop", screens = o.screens || (o.screen ? [o.screen] : []);
      if (!screens.length) throw new Error("mockup needs screen: 'path.png' or screens: [...]");
      const ax = 6.6, aw = W - M - ax, names = [];
      const bez = this.dark ? "1D2230" : "1B1F2A", glowC = c.primary;
      const glow = (x, y, w, h) => { s.addShape(S.OVAL, { x: x + w * 0.1, y: y + h * 0.85, w: w * 0.8, h: h * 0.18, fill: { color: glowC, transparency: 75 }, line: { color: glowC, width: 0, transparency: 100 }, objectName: "mkglow" }); names.push("mkglow"); };
      if (dev === "laptop") {
        const sw = aw * 0.92, sh = sw * 0.625, x = ax + (aw - sw) / 2, y = 1.0;
        glow(x, y, sw, sh + 0.4);
        s.addShape(S.ROUNDED_RECTANGLE, { x, y, w: sw, h: sh, rectRadius: 0.06, fill: { color: bez }, line: { color: "3A4152", width: 1 }, objectName: "mkb" });
        const d = await roundedImage(screens[0], sw - 0.24, sh - 0.3, 0.04); await this._img(s, d, { x: x + 0.12, y: y + 0.15, w: sw - 0.24, h: sh - 0.3, objectName: "mks" });
        s.addShape(S.TRAPEZOID, { x: x - 0.45, y: y + sh, w: sw + 0.9, h: 0.22, fill: { color: "2C3242" }, line: { color: "3A4152", width: 1 }, flipV: true, objectName: "mkbase" });
        s.addShape(S.ROUNDED_RECTANGLE, { x: x + sw / 2 - 0.55, y: y + sh, w: 1.1, h: 0.07, rectRadius: 0.5, fill: { color: "4A5163" }, line: { color: "4A5163", width: 0 }, objectName: "mknotch" });
        names.push("mkb", "mks", "mkbase", "mknotch");
        if (screens[1]) { const pw = 1.55, ph = pw * 2.05, px = x + sw - pw * 0.6, py = y + sh - ph + 0.7; s.addShape(S.ROUNDED_RECTANGLE, { x: px, y: py, w: pw, h: ph, rectRadius: 0.16, fill: { color: bez }, line: { color: "3A4152", width: 1 }, shadow: { type: "outer", color: "000000", opacity: 0.45, blur: 18, offset: 6, angle: 90 }, objectName: "mkpb" }); const d2 = await roundedImage(screens[1], pw - 0.14, ph - 0.14, 0.13); await this._img(s, d2, { x: px + 0.07, y: py + 0.07, w: pw - 0.14, h: ph - 0.14, objectName: "mkps" }); names.push("mkpb", "mkps"); }
      } else if (dev === "browser") {
        const sw = aw, bh = 0.42, sh = sw * 0.6, x = ax, y = 1.1;
        glow(x, y, sw, sh);
        s.addShape(S.ROUNDED_RECTANGLE, { x, y, w: sw, h: sh, rectRadius: 0.04, fill: { color: this.dark ? "1A1F2B" : "FFFFFF" }, line: { color: this.dark ? "323A4D" : "D5DAE3", width: 1 }, shadow: { type: "outer", color: "000000", opacity: 0.35, blur: 18, offset: 6, angle: 90 }, objectName: "mkb" });
        ["FF5F57", "FEBC2E", "28C840"].forEach((col, i) => s.addShape(S.OVAL, { x: x + 0.2 + i * 0.22, y: y + 0.14, w: 0.13, h: 0.13, fill: { color: col }, line: { color: col, width: 0 }, objectName: `mkd${i}` }));
        s.addShape(S.ROUNDED_RECTANGLE, { x: x + 1.0, y: y + 0.09, w: sw - 1.4, h: 0.24, rectRadius: 0.5, fill: { color: this.dark ? "262C3B" : "EEF1F6" }, line: { color: this.dark ? "262C3B" : "EEF1F6", width: 0 }, objectName: "mkurl" });
        if (o.url) this._txt(s, ctx, o.url, { x: x + 1.15, y: y + 0.09, w: sw - 1.7, h: 0.24, fontSize: 10, color: c.muted, valign: "middle", objectName: "mkurlt", fit: false });
        await this._img(s, await roundedImage(screens[0], sw - 0.04, sh - bh - 0.02, 0.02), { x: x + 0.02, y: y + bh, w: sw - 0.04, h: sh - bh - 0.02, objectName: "mks" });
        names.push("mkb", "mkd0", "mkd1", "mkd2", "mkurl", "mks");
      } else {
        const k = dev === "phones" ? Math.min(4, screens.length) : 1; const tablet = dev === "tablet";
        const gap = 0.25; let ph = tablet ? 4.6 : 4.9, pw = tablet ? ph * 0.75 : ph * 0.49; if (k * pw + (k - 1) * gap > aw) { pw = (aw - (k - 1) * gap) / k; ph = tablet ? pw / 0.75 : pw / 0.49; } const tot = k * pw + (k - 1) * gap, x0 = ax + (aw - tot) / 2, y = 1.15 + Math.max(0, (4.9 - ph) / 2);
        glow(x0, y, tot, ph);
        for (let i = 0; i < k; i++) { const x = x0 + i * (pw + gap); s.addShape(S.ROUNDED_RECTANGLE, { x, y, w: pw, h: ph, rectRadius: tablet ? 0.08 : 0.16, fill: { color: bez }, line: { color: "3A4152", width: 1 }, shadow: { type: "outer", color: "000000", opacity: 0.4, blur: 16, offset: 6, angle: 90 }, objectName: `mkb${i}` }); await this._img(s, await roundedImage(screens[i], pw - 0.16, ph - 0.16, tablet ? 0.18 : 0.3), { x: x + 0.08, y: y + 0.08, w: pw - 0.16, h: ph - 0.16, objectName: `mks${i}` }); names.push(`mkb${i}`, `mks${i}`); }
      }
      ctx.step(names, "emph");
      const items = o.items || []; const rowH = Math.min(1.1, (6.5 - 2.75) / Math.max(1, items.length));
      items.forEach((it, i) => { const y = 2.75 + i * rowH; const head = typeof it === "string" ? it : it.head, text = typeof it === "string" ? null : it.text;
        s.addShape(S.OVAL, { x: M, y: y + 0.1, w: 0.14, h: 0.14, fill: { color: c.accent }, line: { color: c.accent, width: 0 }, objectName: `mi${i}b` });
        const nm = [`mi${i}b`, this._txt(s, ctx, head, { x: M + 0.35, y, w: 5.1, h: 0.4, fontSize: 17, bold: true, color: c.text, objectName: `mi${i}h` })];
        if (text) nm.push(this._txt(s, ctx, text, { x: M + 0.35, y: y + 0.4, w: 5.1, h: rowH - 0.45, fontSize: 14, color: c.muted, objectName: `mi${i}t` }));
        ctx.step(nm); });
    });
  }

  // About me (one person) — portrait, name, role, bio, chips, highlights
  about(o) {
    return this._queue(async () => {
      const ctx = this._new("about", o, "PX_PLAIN"), { s } = ctx, c = this.c, S = this.pres.shapes;
      this._chrome(s, ctx, o.kicker === undefined ? "" : o.kicker);
      const pw = 4.3, ph = 5.4, px = M, py = 1.05, names = [];
      s.addShape(S.ROUNDED_RECTANGLE, { x: px + 0.18, y: py + 0.18, w: pw, h: ph, rectRadius: 0.06, fill: { color: c.accent }, line: { color: c.accent, width: 0 }, objectName: "abg" });
      if (o.photo) await this._img(s, await roundedImage(o.photo, pw, ph, 0.25), { x: px, y: py, w: pw, h: ph, objectName: "!!portrait" });
      else { s.addShape(S.ROUNDED_RECTANGLE, { x: px, y: py, w: pw, h: ph, rectRadius: 0.06, fill: { color: c.primary }, line: { color: c.primary, width: 0 }, objectName: "!!portrait" }); this._txt(s, ctx, (o.name || "?").split(/\s+/).map((w) => w[0]).slice(0, 2).join(""), { x: px, y: py, w: pw, h: ph, font: "display", fontSize: 96, bold: true, color: c.onPrimary, align: "center", valign: "middle", objectName: "abini", fit: false }); }
      names.push("abg", "!!portrait");
      ctx.step(names, "emph");
      const x = px + pw + 0.8, w = W - M - x;
      const k = this._txt(s, ctx, String(o.label || "About me").toUpperCase(), { x, y: 1.15, w, h: 0.35, fontSize: 13, bold: true, charSpacing: 3, color: c.ink, objectName: "abk", fit: false });
      const nm = this._txt(s, ctx, this.up(o.name || "", "display"), { x, y: 1.55, w, h: 1.4, font: "display", fontSize: this._fitSize(this.up(o.name || "", "display"), w, 1.4, 54, this.F.display, true, 30), bold: true, color: c.text, objectName: "abn", fit: false });
      const rl = this._txt(s, ctx, o.role || "", { x, y: 2.95, w, h: 0.45, fontSize: 18, color: c.accent, bold: true, objectName: "abr" });
      const bio = o.bio && this._txt(s, ctx, o.bio, { x, y: 3.5, w, h: 1.15, fontSize: 15, color: c.muted, objectName: "abb" });
      ctx.step([k, nm, rl, bio].filter(Boolean));
      const chips = []; let cx = x, cy = 4.8;
      (o.chips || []).forEach((t, j) => { const cw2 = 0.4 + t.length * 0.095; if (cx + cw2 > W - M) { cx = x; cy += 0.48; } s.addShape(S.ROUNDED_RECTANGLE, { x: cx, y: cy, w: cw2, h: 0.38, rectRadius: 0.5, fill: { color: c.primary, transparency: 80 }, line: { color: c.primary, width: 1 }, objectName: `abc${j}` }); this._txt(s, ctx, t, { x: cx, y: cy, w: cw2, h: 0.38, fontSize: 12, color: c.text, align: "center", valign: "middle", objectName: `abct${j}`, fit: false }); chips.push(`abc${j}`, `abct${j}`); cx += cw2 + 0.12; });
      ctx.step(chips);
      const hl = o.highlights || []; const hw = (w - 0.25 * (hl.length - 1)) / Math.max(1, hl.length);
      hl.forEach((h2, j) => { const hx = x + j * (hw + 0.25), hy = 5.75; const nmz = [this._txt(s, ctx, String(h2.value), { x: hx, y: hy, w: hw, h: 0.55, font: "display", fontSize: 28, bold: true, color: c.ink, objectName: `abh${j}v`, fit: false }), this._txt(s, ctx, h2.label, { x: hx, y: hy + 0.55, w: hw, h: 0.4, fontSize: 12, color: c.muted, objectName: `abh${j}l` })]; ctx.step(nmz, "emph"); });
    });
  }

  // Team: members [{name, role, photo}]
  team(o) {
    return this._queue(async () => {
      const ctx = this._new("team", o), { s } = ctx, c = this.c, S = this.pres.shapes;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      const m = o.members || [], n = m.length, gap = 0.3, w = Math.min(2.4, (CW - gap * (n - 1)) / n), tot = n * w + (n - 1) * gap, x0 = M + (CW - tot) / 2, ph = w * 1.15, y = Y0 + 0.2;
      for (let i = 0; i < n; i++) {
        const it = m[i], x = x0 + i * (w + gap), names = [];
        s.addShape(S.ROUNDED_RECTANGLE, { x, y, w, h: ph, rectRadius: 0.12, fill: { color: i % 2 ? c.accent : c.primary }, line: { color: c.primary, width: 0 }, objectName: `tm${i}bg` }); names.push(`tm${i}bg`);
        if (it.photo) { await this._img(s, await roundedImage(it.photo, w, ph, 0.25), { x, y, w, h: ph, objectName: `tm${i}p` }); names.push(`tm${i}p`); }
        else names.push(this._txt(s, ctx, it.name.split(/\s+/).map((z) => z[0]).slice(0, 2).join(""), { x, y, w, h: ph, font: "display", fontSize: 40, bold: true, color: this.best(i % 2 ? c.accent : c.primary), align: "center", valign: "middle", objectName: `tm${i}ini`, fit: false }));
        names.push(this._txt(s, ctx, it.name, { x: x - 0.1, y: y + ph + 0.15, w: w + 0.2, h: 0.45, fontSize: 16, bold: true, color: c.text, align: "center", objectName: `tm${i}n` }));
        names.push(this._txt(s, ctx, it.role || "", { x: x - 0.1, y: y + ph + 0.58, w: w + 0.2, h: 0.4, fontSize: 13, color: c.muted, align: "center", objectName: `tm${i}r` }));
        ctx.step(names);
      }
    });
  }

  // Code window with simple syntax highlighting; highlight: [line numbers 1-based]
  code(o) {
    return this._queue(async () => {
      const ctx = this._new("code", o), { s } = ctx, c = this.c, S = this.pres.shapes;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      const lines = String(o.code || "").replace(/\t/g, "  ").split("\n"); const side = o.note ? 3.6 : 0;
      const w = CW - side - (side ? 0.35 : 0); const maxLen = Math.max(...lines.map((l) => l.length), 10); const fsz = Math.max(11, Math.min(18, Math.floor(((CH - 0.7) / Math.max(1, lines.length)) * 72 / 1.45), Math.floor(((w - 0.7) * 72) / (maxLen * 0.62))));
      const h = Math.min(CH, 0.75 + lines.length * fsz * 1.45 / 72 + 0.25);
      const bgc = this.dark ? mix(c.bg, "000000", 0.35) : "1E2230";
      s.addShape(S.ROUNDED_RECTANGLE, { x: M, y: Y0, w, h, rectRadius: 0.05, fill: { color: bgc }, line: { color: c.primary, width: 1, transparency: 60 }, shadow: { type: "outer", color: "000000", opacity: 0.45, blur: 20, offset: 6, angle: 90 }, objectName: "cw" });
      ["FF5F57", "FEBC2E", "28C840"].forEach((col, i) => s.addShape(S.OVAL, { x: M + 0.25 + i * 0.24, y: Y0 + 0.2, w: 0.14, h: 0.14, fill: { color: col }, line: { color: col, width: 0 }, objectName: `cwd${i}` }));
      if (o.file) this._txt(s, ctx, o.file, { x: M + 1.1, y: Y0 + 0.13, w: w - 1.4, h: 0.3, font: "mono", fontSize: 11, color: "8B93A7", objectName: "cwf", fit: false });
      const KW = /\b(def|return|if|else|elif|for|while|in|import|from|as|class|const|let|var|function|async|await|new|true|false|True|False|None|null|void|int|float|char|struct|include|public|private|static|try|catch|except|with|lambda|yield|break|continue)\b/;
      const tok = (ln) => { const out = []; const re = /(#.*$|\/\/.*$|"[^"]*"|'[^']*'|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b(?=\()|\b[A-Za-z_]\w*\b|\s+|.)/g; let m2; while ((m2 = re.exec(ln))) { const t = m2[0]; let col = "E6E6E6"; if (/^(#|\/\/)/.test(t)) col = "6A7590"; else if (/^["']/.test(t)) col = "C3E88D"; else if (/^\d/.test(t)) col = "F78C6C"; else if (KW.test(t) && /^[A-Za-z_]\w*$/.test(t)) col = "C792EA"; else if (/^[A-Za-z_]\w*$/.test(t) && ln.slice(m2.index + t.length).startsWith("(")) col = "82AAFF"; out.push({ text: t, options: { color: col } }); } return out; };
      const hl = new Set(o.highlight || []); const lh = fsz * 1.45 / 72, top = Y0 + 0.6;
      hl.forEach((n2) => { s.addShape(S.RECTANGLE, { x: M + 0.02, y: top + (n2 - 1) * lh, w: w - 0.04, h: lh, fill: { color: c.primary, transparency: 80 }, line: { color: c.primary, width: 0, transparency: 100 }, objectName: `cwh${n2}` }); s.addShape(S.RECTANGLE, { x: M + 0.02, y: top + (n2 - 1) * lh, w: 0.06, h: lh, fill: { color: c.accent }, line: { color: c.accent, width: 0 }, objectName: `cwhb${n2}` }); });
      const runs = []; lines.forEach((ln, i) => { const t = tok(ln); if (!t.length) t.push({ text: " ", options: {} }); t[t.length - 1].options = { ...t[t.length - 1].options, breakLine: i < lines.length - 1 }; runs.push(...t); });
      s.addText(runs, { x: M + 0.35, y: top, w: w - 0.6, h: lines.length * lh + 0.1, fontFace: this.font("mono"), fontSize: fsz, margin: 0, valign: "top", lineSpacing: fsz * 1.45, isTextBox: true, objectName: "cwc" });
      ctx.step(["cw", "cwd0", "cwd1", "cwd2", o.file ? "cwf" : null, "cwc"]);
      if (hl.size) ctx.step([...hl].flatMap((n2) => [`cwh${n2}`, `cwhb${n2}`]), "emph");
      if (o.note) ctx.step(this._txt(s, ctx, o.note, { x: M + w + 0.35, y: Y0 + 0.2, w: side, h: CH - 0.4, fontSize: 16, color: c.muted, objectName: "cwn" }));
    });
  }

  image(o) {
    return this._queue(async () => {
      const ctx = this._new("image", o, "PX_SPLIT"), { s } = ctx, c = this.c, S = this.pres.shapes;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title, [5.6, 1.5, this.size.title]);
      const x = 6.6, w = W - M - x, h = 5.6, y = 1.0;
      const d = await roundedImage(o.path, w, h, (this.st.card.radius || 0.12) + 0.05, o.fit === "contain" ? "contain" : "cover");
      await this._img(s, d, { x, y, w, h, objectName: "img", shadow: { type: "outer", color: "000000", opacity: this.dark ? 0.45 : 0.15, blur: 20, offset: 6, angle: 90 } });
      ctx.step("img", "emph");
      const items = o.items || []; const rowH = Math.min(1.1, (6.5 - 2.75) / Math.max(1, items.length));
      items.forEach((it, i) => { const yy = 2.75 + i * rowH; const head = typeof it === "string" ? it : it.head, text = typeof it === "string" ? null : it.text;
        s.addShape(S.OVAL, { x: M, y: yy + 0.1, w: 0.14, h: 0.14, fill: { color: c.accent }, line: { color: c.accent, width: 0 }, objectName: `im${i}b` });
        const nm = [`im${i}b`, this._txt(s, ctx, head, { x: M + 0.35, y: yy, w: 5.1, h: 0.4, fontSize: 17, bold: !!text, color: c.text, objectName: `im${i}h` })];
        if (text) nm.push(this._txt(s, ctx, text, { x: M + 0.35, y: yy + 0.4, w: 5.1, h: rowH - 0.45, fontSize: 14, color: c.muted, objectName: `im${i}t` }));
        ctx.step(nm); });
      if (o.caption) this._txt(s, ctx, o.caption, { x, y: y + h + 0.1, w, h: 0.3, fontSize: 11, italic: true, color: c.muted, objectName: "cap" });
    });
  }

  table(o) {
    return this._queue(async () => {
      const ctx = this._new("table", o), { s } = ctx, c = this.c;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      const head = o.headers || [], rows = o.rows || [];
      if (rows.length > 8) this.warnings.push(`slide ${ctx.n}: ${rows.length} rows; keep ≤ 8 or split`);
      const rowFill = this.dark ? mix(c.bg, "FFFFFF", 0.06) : "FFFFFF", alt = this.dark ? mix(c.bg, "FFFFFF", 0.1) : mix(c.bg, c.primary, 0.05);
      const cell = (t, r, ci) => { const isH = r < 0, hi = r === o.highlightRow || ci === o.highlightCol;
        return { text: String(t), options: { bold: isH || hi, color: isH ? c.onPrimary : hi ? (this.dark ? c.accent : c.ink) : c.text, fill: { color: isH ? c.primary : hi ? mix(this.dark ? c.bg : "FFFFFF", c.accent, 0.18) : r % 2 ? alt : rowFill }, align: ci === 0 ? "left" : o.align || "left", valign: "middle" } }; };
      const data = [head.map((h2, ci) => cell(h2, -1, ci)), ...rows.map((row, r) => row.map((v, ci) => cell(v, r, ci)))];
      s.addTable(data, { x: M, y: Y0 + 0.05, w: CW, colW: o.colW, rowH: Math.min(0.55, CH / data.length), fontFace: this.F.body, fontSize: o.fontSize || 14, margin: [0.06, 0.15, 0.06, 0.15], border: { type: "solid", pt: 0.75, color: this.dark ? mix(c.bg, "FFFFFF", 0.15) : "D9DEE7" }, objectName: "table" });
      ctx.step("table");
      if (o.source) this._txt(s, ctx, `${this.L.source}: ${o.source}`, { x: M, y: Y1 - 0.2, w: CW, h: 0.3, fontSize: 11, italic: true, color: c.muted, objectName: "source" });
    });
  }

  points(o) {
    return this._queue(async () => {
      const ctx = this._new("points", o), { s } = ctx, c = this.c, S = this.pres.shapes;
      this._chrome(s, ctx, o.kicker); this._title(s, ctx, o.title);
      const items = o.items || [], rowH = Math.min(1.2, CH / items.length), lw = o.obj || o.visual ? 7.4 : CW;
      for (let i = 0; i < items.length; i++) {
        const it = typeof items[i] === "string" ? { head: items[i] } : items[i], y = Y0 + i * rowH;
        s.addShape(S.OVAL, { x: M, y: y + 0.02, w: 0.52, h: 0.52, fill: { color: c.primary }, line: { color: c.primary, width: 0 }, objectName: `pt${i}b` });
        const nm = [`pt${i}b`, this._txt(s, ctx, String(i + 1), { x: M, y: y + 0.02, w: 0.52, h: 0.52, fontSize: 15, bold: true, color: c.onPrimary, align: "center", valign: "middle", objectName: `pt${i}n`, fit: false }),
          this._txt(s, ctx, it.head, { x: M + 0.8, y: y - 0.02, w: lw - 0.8, h: 0.42, fontSize: 18, bold: true, color: c.text, objectName: `pt${i}h` })];
        if (it.text) nm.push(this._txt(s, ctx, it.text, { x: M + 0.8, y: y + 0.4, w: lw - 0.8, h: rowH - 0.5, fontSize: 14, color: c.muted, objectName: `pt${i}t` }));
        ctx.step(nm);
      }
      if (o.obj) { await this._img(s, path.join(this.tmp, "halo.png"), { x: M + 7.9, y: Y0 - 0.3, w: 4.4, h: 4.4, objectName: "ptglow" }).catch(() => {}); }
      if (o.obj) { await this._img(s, objPath(o.obj), { x: M + 8.5, y: Y0 + 0.2, w: 3.3, h: 3.3, objectName: "!!hero" }); ctx.step("!!hero", "emph"); }
    });
  }

  quote(o) {
    return this._queue(async () => {
      const ctx = this._new("quote", o, "PX_PLAIN"), { s } = ctx, c = this.c;
      const mk = this._txt(s, ctx, "“", { x: M - 0.05, y: 0.7, w: 1.6, h: 1.6, font: "display", fontSize: 120, bold: true, color: c.ink, objectName: "qm", fit: false });
      const fsz = this._fitSize(o.text, 10.8, 2.8, 36, this.F.head, true, 24); const th = (this._lines(o.text, 10.8, fsz, this.F.head, true) * fsz * 1.2) / 72;
      this._txt(s, ctx, o.text, { x: M, y: 2.2, w: 10.8, h: th + 0.1, font: "head", fontSize: fsz, bold: true, italic: true, color: c.text, objectName: "qt", fit: false });
      const au = o.author && this._txt(s, ctx, [{ text: o.author, options: { bold: true, color: c.text } }, ...(o.role ? [{ text: "  ·  " + o.role, options: { color: c.muted } }] : [])], { x: M, y: 2.2 + th + 0.4, w: 10, h: 0.5, fontSize: 16, objectName: "qa" });
      ctx.step(mk, "emph"); ctx.step(au);
    });
  }

  closing(o = {}) {
    return this._queue(async () => {
      const ctx = this._new("closing", o, "PX_COVER"), { s } = ctx, c = this.c;
      const art = this.st.hero?.kind && this.st.hero.kind !== "none"; const tw = art ? 7.4 : CW; const align = art ? "left" : "center";
      const hero = art ? await this._hero(s, ctx, W - M - 4.6, 1.4, 4.6) : [];
      const k = this._txt(s, ctx, String(o.kicker || this.L.questions).toUpperCase(), { x: M, y: 1.9, w: tw, h: 0.4, fontSize: 14, bold: true, charSpacing: 3, color: c.ink, align, objectName: "kicker", fit: false });
      const title = this.up(o.title || this.L.thanks, "display"); const ts = this._fitSize(title, tw, 2.2, this.size.cover, this.F.display, true, 36); const th = (this._lines(title, tw, ts, this.F.display, true) * ts * 1.05) / 72;
      this._txt(s, ctx, title, { x: M, y: 2.4, w: tw, h: th + 0.1, font: "display", fontSize: ts, bold: true, italic: !!this.F.displayItalic, color: c.text, align, objectName: "title", fit: false });
      const sub = o.subtitle && this._txt(s, ctx, o.subtitle, { x: M, y: 2.4 + th + 0.25, w: tw, h: 0.6, fontSize: 19, color: c.muted, align, objectName: "subtitle" });
      const ct = o.contact && o.contact.length && this._txt(s, ctx, o.contact.join("\n"), { x: M, y: 2.4 + th + 1.1, w: tw, h: 1.3, fontSize: 15, color: c.text, align, paraSpaceAfter: 4, objectName: "contact" });
      ctx.step(hero, "emph"); ctx.step([k, sub].filter(Boolean)); ctx.step(ct);
    });
  }

  custom(o, fn) {
    return this._queue(async () => {
      const ctx = this._new("custom", o, o.plain ? "PX_PLAIN" : "PX_CONTENT"), { s } = ctx;
      if (o.header !== false) this._chrome(s, ctx, o.kicker);
      if (!o.plain) this._title(s, ctx, o.title);
      await fn({ slide: s, pptx: this.pres, colors: this.c, style: this.st, grid: { W, H, M, CW, Y0, Y1, CH },
        text: (t, opts) => this._txt(s, ctx, t, opts), shape: (type, opts) => this._shape(s, type, opts), card: (x, y, w, h, name, opt) => this._card(s, x, y, w, h, name, opt),
        icon: (it, x, y, size, name) => this._icon(s, it, x, y, size, name), object: (name) => objPath(name), image: (file, w, h, r) => roundedImage(file, w, h, r ?? 0.12),
        step: (names, role) => ctx.step(names, role) });
    });
  }

  palette() {
    const c = this.c, sr = this.st.series || [];
    return { name: this.st.name, colors: { dk1: c.text, lt1: c.bg, dk2: c.muted, lt2: c.bg2 || c.bg, accent1: c.primary, accent2: c.accent, accent3: sr[2] || c.ink, accent4: sr[3] || c.accent2 || c.ink, accent5: c.ink, accent6: c.muted, hlink: c.ink, folHlink: c.muted } };
  }

  async save(file) {
    const bgPath = path.join(this.tmp, "background.jpg");
    fs.writeFileSync(bgPath, await BG.background(this.st.background, { ...this.c, primary: this.c.primary, accent: this.c.accent, accent2: this.c.accent2 }, { w: 2400, h: 1350 }));
    this.bgPath = bgPath;
    this._layouts(bgPath);
    for (const op of this.ops) await op();
    await this.pres.writeFile({ fileName: file });
    const motion = await finalize(file, { slides: this.plan }, this.palette());
    const charts = await POST.charts(file, this.charts);
    const fonts = this.opts.embedFonts === false ? { skipped: true } : POST.embedFonts(file, path.join(DATA, "assets", "fonts"));
    const out = { file, style: this.st.id, slides: this.plan.length, motion: this.opts.motion || "subtle", animatedSlides: motion.animated, charts, fonts, warnings: this.warnings, missingAnimationTargets: motion.missing };
    console.log(JSON.stringify(out, null, 2));
    return out;
  }
}

module.exports = { Deck, loadStyle, objPath, renderIcon, roundedImage, GLYPH, GRID: { W, H, M, CW, Y0, Y1, CH } };
