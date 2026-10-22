// banner.js — social, event, webinar and print banners in the same styles as the decks. MIT License.
//
//   const { Banner, SIZES } = require("<skill>/scripts/banner.js");
//   const b = new Banner({ style: "nebula", size: "linkedin-post", layout: "event",
//     kicker: "Student Club", title: "Tech Day 2026", subtitle: "Talks and a hackathon",
//     details: [{ icon: "calendar", text: "[date]" }, { icon: "map", text: "[venue]" }],
//     cta: "Register now", logos: ["logo.png"], obj: "high-voltage" });
//   await b.save("techday-linkedin");   // writes .pptx (editable), .png (exact pixels), .pdf
//
// layouts: event | webinar | announcement | achievement | quote | profile (LinkedIn banner) | countdown
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");
const PptxGenJS = require("pptxgenjs");
const BG = require("./backgrounds.js");
const { loadStyle, objPath, renderIcon, roundedImage, GLYPH } = require("./deckkit.js");
const POST = require("./post.js");

// pixel sizes (checked against Metricool's 2026 guide) and print sizes in mm
const SIZES = {
  "linkedin-banner": { px: [1584, 396] }, "linkedin-company": { px: [1128, 376] }, "linkedin-post": { px: [1200, 627] }, "linkedin-square": { px: [1080, 1080] },
  "facebook-cover": { px: [1702, 630] }, "facebook-event": { px: [1920, 1005] }, "facebook-post": { px: [1200, 1200] },
  "instagram-square": { px: [1080, 1080] }, "instagram-portrait": { px: [1080, 1350] }, "story": { px: [1080, 1920] },
  "x-header": { px: [1500, 500] }, "x-post": { px: [1200, 675] }, "youtube-thumbnail": { px: [1280, 720] }, "youtube-banner": { px: [2048, 1152] },
  "webinar": { px: [1920, 1080] }, "slide": { px: [1920, 1080] },
  "a4": { mm: [210, 297] }, "a3": { mm: [297, 420] }, "a2": { mm: [420, 594] }, "rollup": { mm: [850, 2000] }, "a4-landscape": { mm: [297, 210] },
};

const hex6 = (c) => String(c).replace("#", "").toUpperCase();
function lum(hx) { const c = [0, 2, 4].map((i) => parseInt(hex6(hx).slice(i, i + 2), 16) / 255).map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4)); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; }
const contrast = (a, b) => { const [x, y] = [lum(a), lum(b)]; return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
const GLY = 0.58;

class Banner {
  constructor(o) {
    this.o = o; this.st = loadStyle(o.style); if (o.colors) Object.assign(this.st.colors, o.colors);
    this.c = this.st.colors; this.F = this.st.fonts;
    const sz = typeof o.size === "string" ? SIZES[o.size] : o.size;
    if (!sz) throw new Error(`size: ${Object.keys(SIZES).join(", ")} or {px:[w,h]} / {mm:[w,h]}`);
    if (sz.px) { this.pxW = sz.px[0]; this.pxH = sz.px[1]; this.W = this.pxW / 100; this.H = this.pxH / 100; this.dpi = 100; this.print = false; }
    else { this.W = sz.mm[0] / 25.4; this.H = sz.mm[1] / 25.4; this.dpi = 150; this.pxW = Math.round(this.W * 150); this.pxH = Math.round(this.H * 150); this.print = true; }
    this.tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ppsb-"));
    this.u = Math.min(this.W, this.H); // base unit
    this.ratio = this.W / this.H;
  }
  up(t, role = "display") { const cs = role === "display" ? this.F.displayCase : this.F.headCase; return cs === "upper" ? String(t).toUpperCase() : String(t); }
  best(fill) { return [this.c.text, "FFFFFF", "111111"].map(hex6).sort((a, b) => contrast(b, fill) - contrast(a, fill))[0]; }
  fit(text, w, h, size, min) { let s = size; const lines = (sz) => { const per = Math.max(1, Math.floor(w / ((sz / 72) * GLY))); let n = 0; for (const p of String(text).split("\n")) { let cur = 0; n++; for (const wd of p.split(/\s+/)) { const k = wd.length + (cur ? 1 : 0); if (cur + k > per && cur > 0) { n++; cur = wd.length; } else cur += k; } } return n; }; const longest = Math.max(...String(text).split(/\s+/).map((x) => x.length)); while (s > min && ((lines(s) * s * 1.12) / 72 > h || (longest * s * GLY) / 72 > w)) s -= 1; return s; }

  // measure text height (inches) for a font size, box width and face
  _lines(text, w, size, face, upper) { const g = (GLYPH[face] || 0.58) * (upper ? 1.12 : 1) * 1.04; const per = Math.max(1, Math.floor(w / ((size / 72) * g))); let n = 0; for (const p of String(text).split("\n")) { let cur = 0; n++; for (const wd of p.split(/\s+/)) { const k = wd.length + (cur ? 1 : 0); if (cur + k > per && cur > 0) { n++; cur = wd.length; } else cur += k; } } return n; }
  _wordOk(text, w, size, face, upper) { const g = (GLYPH[face] || 0.58) * (upper ? 1.12 : 1) * 1.04; const longest = Math.max(...String(text).split(/\s+/).map((x) => x.length)); return (longest * size * g) / 72 <= w; }

  _blocks(o, layout, f) {
    const u = this.u, wide = this.ratio > 2.2, B = [];
    const k = (x) => x * u * f;
    if (o.kicker) B.push({ kind: "kicker", text: String(o.kicker).toUpperCase(), size: Math.max(8, k(wide ? 6.5 : 4)), face: this.F.body, lh: 1.25, gap: 0.5 });
    const main = layout === "achievement" ? (o.title || "1st place") : layout === "countdown" ? String(o.count ?? 3) : o.title || "";
    if (main) B.push({ kind: "title", text: layout === "quote" ? `\u201C${main}\u201D` : this.up(main), size: k(layout === "countdown" ? 36 : wide ? 15 : 12), face: layout === "quote" ? this.F.head : this.F.display, lh: 1.05, gap: 0.3, upper: this.F.displayCase === "upper" });
    if (layout === "countdown") B.push({ kind: "unit", text: this.up(o.unit || "days left", "head"), size: k(6), face: this.F.head, lh: 1.2, gap: 0.6 });
    if (o.subtitle) B.push({ kind: "subtitle", text: o.subtitle, size: Math.max(8, k(wide ? 6 : 4.6)), face: this.F.body, lh: 1.3, gap: 0.7 });
    if (o.speaker && layout === "webinar") B.push({ kind: "speaker", text: `${o.speaker.name}\n${o.speaker.role || ""}`, size: Math.max(8, k(4.2)), face: this.F.body, lh: 1.3, gap: 0.6 });
    for (const d of o.details || []) { const dd = typeof d === "string" ? { text: d } : d; B.push({ kind: "detail", text: dd.text, icon: dd.icon, size: Math.max(8, k(wide ? 5 : 3.8)), face: this.F.body, lh: 1.25, gap: 0.35 }); }
    if (o.cta) B.push({ kind: "cta", text: o.cta, size: Math.max(9, k(wide ? 5 : 4)), face: this.F.body, lh: 2.0, gap: 0 });
    return B;
  }
  _measure(B, w) { let tot = 0; for (const b of B) { const iw = b.icon ? w - (b.size * 1.6) / 72 : w; b.n = b.kind === "cta" ? 1 : this._lines(b.text, iw, b.size, b.face, b.upper); b.h = (b.n * b.size * b.lh) / 72; b.ok = this._wordOk(b.text, iw, b.size, b.face, b.upper); tot += b.h + (b.size * b.gap) / 72; } return tot; }
  _fitBlocks(o, layout, w, hAvail) { let f = 1, B, tot; for (; f > 0.3; f -= 0.04) { B = this._blocks(o, layout, f); tot = this._measure(B, w); if (tot <= hAvail && B.every((b) => b.ok)) break; } return { B, tot, f }; }

  async save(base) {
    const o = this.o, c = this.c, W = this.W, H = this.H, u = this.u, p = new PptxGenJS();
    p.defineLayout({ name: "BANNER", width: W, height: H }); p.layout = "BANNER";
    const bg = path.join(this.tmp, "bg.jpg");
    fs.writeFileSync(bg, await BG.background(this.st.background, c, { w: Math.min(3200, Math.round(this.pxW * 1.5)), h: Math.min(3200, Math.round(this.pxH * 1.5)) }));
    const s = p.addSlide(); s.background = { path: bg };
    const m = u * 0.08, layout = o.layout || "event";
    const wide = this.ratio > 2.2, land = this.ratio >= 1.15, portrait = this.ratio < 0.85;
    const logoH = o.logos && o.logos.length ? u * (wide ? 0.16 : 0.09) : 0;
    const artKind = this.st.hero?.kind || "none";
    const hasArt = !!(o.photo || o.obj || artKind !== "none" || layout === "achievement");
    let tx = m, tw = W - 2 * m, ax, ay, as, top = m, bottom = H - m - (logoH ? logoH + m * 0.6 : 0);
    let fit;
    if (hasArt && (wide || land)) {
      as = Math.min(H - 2 * m, W * (wide ? 0.3 : 0.42)); ax = W - m - as; ay = (H - as) / 2; tw = ax - m - tx;
      if (layout === "profile") { tx = W * 0.3; tw = ax - m * 0.5 - tx; }
      fit = this._fitBlocks(o, layout, tw, bottom - top);
    } else if (hasArt) {
      fit = this._fitBlocks(o, layout, tw, (bottom - top) * 0.6);
      as = Math.max(W * 0.3, Math.min(W * 0.62, bottom - top - fit.tot - m * 0.8)); ax = (W - as) / 2; ay = top;
      top = ay + as + m * 0.5;
    } else fit = this._fitBlocks(o, layout, tw, bottom - top);
    // art
    if (hasArt) {
      if (o.photo) { const d = await roundedImage(o.photo, as, as, layout === "webinar" ? as / 2 : as * 0.08); s.addImage({ data: d, x: ax, y: ay, w: as, h: as }); if (layout === "webinar") s.addShape(p.shapes.OVAL, { x: ax - as * 0.03, y: ay - as * 0.03, w: as * 1.06, h: as * 1.06, fill: { type: "none" }, line: { color: c.accent, width: Math.max(2, u * 2) } }); }
      else if ((artKind === "orbs" || artKind === "iso") && !o.obj) { const f = path.join(this.tmp, "hero.png"); fs.writeFileSync(f, await BG.hero(artKind, c, { w: 1400, h: 1400 })); s.addImage({ path: f, x: ax, y: ay, w: as, h: as }); }
      else { const f = path.join(this.tmp, "halo.png"); fs.writeFileSync(f, await BG.hero("halo", c, { w: 900, h: 900 })); s.addImage({ path: f, x: ax - as * 0.15, y: ay - as * 0.15, w: as * 1.3, h: as * 1.3 }); s.addImage({ path: objPath(o.obj || (layout === "achievement" ? "trophy" : (this.st.hero?.objects?.[0] || "rocket"))), x: ax + as * 0.1, y: ay + as * 0.1, w: as * 0.8, h: as * 0.8 }); }
    }
    const T = (text, opt) => s.addText(text, { isTextBox: true, margin: 0, fontFace: this.F.body, color: c.text, valign: "top", ...opt });
    const center = !(wide || land) || !hasArt && layout !== "profile" && !wide;
    const al = center ? "center" : "left";
    let y = top + Math.max(0, (bottom - top - fit.tot) / 2);
    for (const b of fit.B) {
      if (b.kind === "kicker") T(b.text, { x: tx, y, w: tw, h: b.h + 0.02, fontSize: b.size, bold: true, charSpacing: 2, color: c.ink, align: al });
      else if (b.kind === "title") T(b.text, { x: tx, y, w: tw, h: b.h + 0.05, fontFace: b.face, fontSize: b.size, bold: true, italic: !!this.F.displayItalic || layout === "quote", color: layout === "countdown" ? c.accent : c.text, align: al, lineSpacingMultiple: 0.95, glow: this.st.mode === "dark" ? { size: Math.max(4, u * 1.2), opacity: 0.3, color: c.primary } : undefined });
      else if (b.kind === "unit") T(b.text, { x: tx, y, w: tw, h: b.h, fontFace: b.face, fontSize: b.size, bold: true, align: al });
      else if (b.kind === "subtitle") T(b.text, { x: tx, y, w: tw, h: b.h + 0.02, fontSize: b.size, color: c.muted, align: al });
      else if (b.kind === "speaker") { const [n1, r1] = b.text.split("\n"); T([{ text: n1, options: { bold: true, breakLine: true } }, { text: r1, options: { color: c.muted } }], { x: tx, y, w: tw, h: b.h + 0.02, fontSize: b.size, align: al }); }
      else if (b.kind === "detail") {
        const iz = (b.size * 1.15) / 72, textW = Math.min(tw - iz * 1.5, (b.text.length * b.size * (GLYPH[b.face] || 0.58) * 1.22) / 72 + b.size / 72);
        const bx = center ? tx + (tw - textW - (b.icon ? iz * 1.5 : 0)) / 2 : tx;
        if (b.icon) { const ic = await renderIcon(b.icon, c.ink, true); s.addImage({ data: ic, x: bx, y: y + ((b.size * 1.25) / 72 - iz) / 2, w: iz, h: iz }); }
        T(b.text, { x: bx + (b.icon ? iz * 1.5 : 0), y, w: center ? textW : tw - iz * 1.5, h: b.h + 0.02, fontSize: b.size, bold: true });
      } else if (b.kind === "cta") {
        const cw2 = Math.min(tw, (b.text.length * b.size * 0.62) / 72 + (b.size * 1.6) / 72), ch = (b.size * 2.0) / 72, cx = center ? tx + (tw - cw2) / 2 : tx;
        s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: cx, y, w: cw2, h: ch, rectRadius: 0.5, fill: { color: c.accent }, line: { color: c.accent, width: 0 } });
        T(b.text, { x: cx, y, w: cw2, h: ch, fontSize: b.size, bold: true, color: this.best(c.accent), align: "center", valign: "middle" });
      }
      y += b.h + (b.size * b.gap) / 72;
    }
    if (logoH) { const lw = logoH * 2.2, gap = logoH * 0.4; const tot = o.logos.length * lw + (o.logos.length - 1) * gap; const lx = center ? (W - tot) / 2 : tx; o.logos.forEach((l, i) => s.addImage({ path: l, x: lx + i * (lw + gap), y: H - m - logoH, w: lw, h: logoH, sizing: { type: "contain", w: lw, h: logoH } })); }
    if (o.handle) { const hs = Math.max(8, u * 3); T(o.handle, { x: m, y: H - m - (hs * 1.4) / 72, w: W - 2 * m, h: (hs * 1.4) / 72, fontSize: hs, color: c.muted, align: "right" }); }
    const pptx = base + ".pptx"; await p.writeFile({ fileName: pptx });
    const fonts = POST.embedFonts(pptx, path.join(require("./dataroot.js").dataRoot(), "assets", "fonts"));
    // export PNG at exact pixels and PDF
    const r = spawnSync("python3", [path.join(__dirname, "render.py"), pptx, this.tmp + "/r", "--dpi", String(this.dpi), "--cols", "1", "--png"], { encoding: "utf8" });
    const pdfSrc = path.join(this.tmp, "r", path.basename(base) + ".pdf");
    let png = null; if (r.status === 0) { const first = r.stdout.split("\n").find((l) => /slide-\d+\.png$/.test(l)); if (first) { png = base + ".png"; await require("sharp")(first).resize(this.pxW, this.pxH).png().toFile(png); } if (fs.existsSync(pdfSrc)) fs.copyFileSync(pdfSrc, base + ".pdf"); }
    const out = { pptx, png, pdf: fs.existsSync(base + ".pdf") ? base + ".pdf" : null, size: `${this.pxW}x${this.pxH}px`, style: this.st.id, layout, fonts: fonts.embedded };
    console.log(JSON.stringify(out)); return out;
  }
}
module.exports = { Banner, SIZES };
