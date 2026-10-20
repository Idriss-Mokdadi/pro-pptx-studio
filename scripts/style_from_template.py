#!/usr/bin/env python3
"""Turn a presentation template you like (a Canva export, Slidesgo, SlidesCarnival, your own old deck)
into a pro-pptx-studio style profile, so new decks can have the same feel. MIT License.

usage: python3 style_from_template.py template.pptx --id my-style [--name "My Style"] [--keep-background]
                                      [--tags ai,security] [--out <skill>/styles]
- Reads theme colors, the colors used on slides, the fonts used, and renders the slides to measure
  brightness and the dominant palette.
- Maps the template's fonts to the closest open (OFL) fonts bundled with the skill.
- --keep-background copies the template's own full-slide background image into
  assets/templates/<id>/ and uses it (recipe "image"). Only do this for templates you are allowed
  to reuse, and keep such a skill private: Canva and SlidesCarnival forbid redistributing their assets.
  Without it, the style gets a generated background in the same colors (safe to share).
Prints the path of the new style JSON and of a reference contact sheet.
"""
import argparse, colorsys, glob, io, json, os, re, shutil, subprocess, sys, tempfile, zipfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from tplkit.assets import data_root  # noqa: E402
ROOT = data_root()  # skill folder, or the unpacked bundle cache
FONT_MAP = {  # common template fonts -> closest bundled OFL font
    'inter': 'Inter', 'montserrat': 'Montserrat', 'poppins': 'Poppins', 'anton': 'Anton', 'big shoulders': 'Big Shoulders Display', 'bebas': 'Bebas Neue',
    'oswald': 'Oswald', 'tt hoves': 'Plus Jakarta Sans', 'gotham': 'Montserrat', 'helvetica': 'Inter', 'arial': 'Inter', 'agrandir narrow': 'Barlow Condensed',
    'agrandir': 'Bricolage Grotesque', 'codec': 'Outfit', 'open sauce': 'Plus Jakarta Sans', 'hk modular': 'Orbitron', 'tomorrow': 'Tomorrow', 'pattanakarn': 'Saira',
    'canva sans': 'DM Sans', 'glacial': 'Outfit', 'extenda': 'Big Shoulders Display', 'marta': 'Fraunces', 'brodille': 'Fraunces', 'octosquares': 'Orbitron',
    'mokoto': 'Audiowide', 'telegraf': 'Manrope', 'days': 'Unbounded', 'alpha': 'Big Shoulders Display', 'heading now': 'Anton', 'londrina': 'Londrina Solid',
    'rubik': 'Outfit', 'source sans': 'Inter', 'open sans': 'Inter', 'roboto': 'Inter', 'adriana': 'Instrument Sans', 'interphases': 'Inter', 'league spartan': 'Outfit',
    'lato': 'Inter', 'raleway': 'Montserrat', 'nunito': 'Outfit', 'quicksand': 'Fredoka', 'playfair': 'Bodoni Moda', 'lora': 'Source Serif 4', 'cormorant': 'Cormorant Garamond',
    'dm serif': 'Fraunces', 'garet': 'Outfit', 'now': 'Inter', 'sora': 'Sora', 'jakarta': 'Plus Jakarta Sans', 'space grotesk': 'Plus Jakarta Sans', 'orbitron': 'Orbitron',
    'exo': 'Exo 2', 'rajdhani': 'Rajdhani', 'chakra': 'Chakra Petch', 'syne': 'Syne', 'archivo black': 'Archivo Black', 'archivo': 'Inter', 'fredoka': 'Fredoka',
    'caveat': 'Caveat', 'jetbrains': 'JetBrains Mono', 'courier': 'Space Mono', 'consolas': 'JetBrains Mono', 'manrope': 'Manrope', 'outfit': 'Outfit', 'kanit': 'Kanit',
    'titillium': 'Titillium Web', 'barlow condensed': 'Barlow Condensed', 'barlow': 'Barlow', 'unbounded': 'Unbounded', 'russo': 'Russo One', 'audiowide': 'Audiowide',
}
CONDENSED = {'Anton', 'Bebas Neue', 'Big Shoulders Display', 'Oswald', 'Barlow Condensed', 'Londrina Solid'}

def map_font(name):
    n = name.lower()
    for k in sorted(FONT_MAP, key=len, reverse=True):
        if k in n: return FONT_MAP[k]
    return 'Inter'

def hexs(rgb): return '%02X%02X%02X' % tuple(int(x) for x in rgb)
def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]; c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def contrast(a, b): x, y = lum(a), lum(b); return (max(x, y) + 0.05) / (min(x, y) + 0.05)
def sat(h): r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)); return colorsys.rgb_to_hsv(r, g, b)[1]
def mixc(a, b, t): return ''.join('%02X' % round(int(a[i:i + 2], 16) + (int(b[i:i + 2], 16) - int(a[i:i + 2], 16)) * t) for i in (0, 2, 4))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('pptx'); ap.add_argument('--id', required=True); ap.add_argument('--name'); ap.add_argument('--tags', default='general')
    ap.add_argument('--keep-background', action='store_true'); ap.add_argument('--out', default=os.path.join(ROOT, 'styles')); a = ap.parse_args()
    z = zipfile.ZipFile(a.pptx); names = z.namelist()
    slides = sorted([n for n in names if re.match(r'ppt/slides/slide\d+\.xml$', n)], key=lambda n: int(re.findall(r'\d+', n)[0]))
    fonts = Counter(); cols = Counter(); big = Counter(); small = Counter()
    for n in slides:
        x = z.read(n).decode('utf8', 'ignore')
        for rpr in re.findall(r'<a:rPr\b[^>]*>.*?</a:rPr>', x, re.S):
            mf = re.search(r'<a:latin typeface="([^"+][^"]*)"', rpr); ms = re.search(r'\bsz="(\d+)"', rpr)
            if mf:
                fonts[mf.group(1)] += 1
                sz = int(ms.group(1)) if ms else 1800
                (big if sz >= 2800 else small)[mf.group(1)] += 1
        cols.update(re.findall(r'<a:srgbClr val="([0-9A-Fa-f]{6})"', x))
    # render for brightness and palette
    tmp = tempfile.mkdtemp(prefix='tpl-')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'render.py'), a.pptx, tmp, '--dpi', '30', '--cols', '4'], capture_output=True, text=True)
    imgs = sorted(glob.glob(os.path.join(tmp, 'slide-*.jpg')))
    from PIL import Image
    edge = Counter(); allc = Counter(); dark_votes = 0
    for p in imgs:
        im = Image.open(p).convert('RGB'); w, h = im.size
        q = im.quantize(colors=8, method=Image.Quantize.MEDIANCUT).convert('RGB')
        for cnt, c in q.getcolors(w * h) or []: allc[hexs(c)] += cnt
        px = [im.getpixel((x, y)) for x in range(0, w, max(1, w // 40)) for y in (2, h - 3)] + [im.getpixel((x, y)) for y in range(0, h, max(1, h // 25)) for x in (2, w - 3)]
        for c in px: edge[hexs([v // 8 * 8 for v in c])] += 1
        mean = sum(sum(c) for c in px) / (3 * len(px)); dark_votes += mean < 128
    dark = dark_votes >= len(imgs) / 2 if imgs else True
    bg = edge.most_common(1)[0][0] if edge else ('0B0B1E' if dark else 'FFFFFF')
    def vivid(c): r_, g_, b_ = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)); hh, ss, vv = colorsys.rgb_to_hsv(r_, g_, b_); return ss * vv
    xml_c = [c.upper() for c, _ in cols.most_common(30) if vivid(c.upper()) > 0.35]
    pix_c = [c for c, _ in allc.most_common(40) if vivid(c) > 0.35]
    cand = list(dict.fromkeys(xml_c + pix_c))
    primary = cand[0] if cand else ('6D4AFF' if dark else '1E40AF')
    accent = next((c for c in cand[1:] if abs(colorsys.rgb_to_hsv(*(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)))[0] - colorsys.rgb_to_hsv(*(int(primary[i:i + 2], 16) / 255 for i in (0, 2, 4)))[0]) > 0.08), cand[1] if len(cand) > 1 else primary)
    text = 'F5F6FA' if dark else '111827'
    muted = mixc(text, bg, 0.35)
    while contrast(muted, bg) < 4.6: muted = mixc(muted, text, 0.2)
    ink = primary
    for _ in range(12):
        if contrast(ink, bg) >= 3.2: break
        ink = mixc(ink, 'FFFFFF' if dark else '000000', 0.15)
    onp = max(['FFFFFF', '111111'], key=lambda t: contrast(t, primary))
    used = [f for f, _ in fonts.most_common() if not f.startswith('+')]
    head_src = (big.most_common(1) or fonts.most_common(1) or [('Inter', 0)])[0][0]
    body_src = next((f for f, _ in small.most_common() if map_font(f) != map_font(head_src)), (small.most_common(1) or [(head_src, 0)])[0][0])
    disp, body = map_font(head_src), map_font(body_src)
    style = {
        'id': a.id, 'name': a.name or a.id.replace('-', ' ').title(), 'group': 'template', 'tags': [t.strip() for t in a.tags.split(',') if t.strip()], 'weight': 70,
        'mode': 'dark' if dark else 'light', 'source': os.path.basename(a.pptx),
        'fonts': {'display': disp, 'head': disp, 'body': body, 'mono': 'JetBrains Mono', 'displayCase': 'upper' if disp in CONDENSED else 'none', 'headCase': 'upper' if disp in CONDENSED else 'none', 'displayItalic': False},
        'colors': {'bg': bg, 'bg2': mixc(bg, primary, 0.12), 'text': text, 'muted': muted, 'primary': primary, 'ink': ink, 'accent': accent, 'accent2': cand[2] if len(cand) > 2 else accent,
                   'onPrimary': onp, 'surface': 'FFFFFF' if dark else 'FFFFFF', 'surfaceAlpha': 90 if dark else 10, 'border': 'FFFFFF' if dark else mixc(bg, '000000', 0.15), 'borderAlpha': 80 if dark else 0},
        'series': [primary, accent] + cand[2:5],
        'background': {'recipe': 'aurora' if dark else 'meshlight'}, 'card': {'kind': 'glass' if dark else 'soft', 'radius': 0.14},
        'chrome': {'kicker': 'dot', 'nav': False, 'footer': 'text', 'page': 'corner'}, 'hero': {'kind': '3d', 'halo': dark},
        'fontsDetected': used[:8],
    }
    if a.keep_background:
        best = None
        sl = slides[1] if len(slides) > 1 else slides[0]
        relp = sl.replace('slides/', 'slides/_rels/') + '.rels'
        rels = z.read(relp).decode('utf8', 'ignore') if relp in names else ''
        for tgt in re.findall(r'Target="\.\./media/([^"]+)"', rels):
            data = z.read('ppt/media/' + tgt)
            try:
                im = Image.open(io.BytesIO(data)); area = im.size[0] * im.size[1]
                if im.size[0] / max(1, im.size[1]) > 1.5 and (best is None or area > best[0]): best = (area, tgt, data)
            except Exception: pass
        if best:
            d = os.path.join(ROOT, 'assets', 'templates', a.id); os.makedirs(d, exist_ok=True)
            out = os.path.join(d, 'background' + os.path.splitext(best[1])[1].lower())
            open(out, 'wb').write(best[2])
            style['background'] = {'recipe': 'image', 'path': os.path.relpath(out, ROOT).replace(os.sep, '/'), 'dim': 0}
    os.makedirs(a.out, exist_ok=True)
    sp = os.path.join(a.out, a.id + '.json'); json.dump(style, open(sp, 'w'), indent=1)
    ref = os.path.join(ROOT, 'assets', 'templates', a.id); os.makedirs(ref, exist_ok=True)
    sheet = os.path.join(tmp, 'sheet.jpg')
    if os.path.exists(sheet): shutil.copy(sheet, os.path.join(ref, 'reference.jpg'))
    print(sp); print(os.path.join(ref, 'reference.jpg'))
    print(json.dumps({'mode': style['mode'], 'fonts': [disp, body], 'detected': used[:6], 'primary': primary, 'accent': accent, 'bg': bg}))

if __name__ == '__main__':
    main()
