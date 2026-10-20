"""Fonts for template decks (MIT License): extract a template's embedded fonts (for previews and
text measuring), swap a template font for a themed one, and embed the new font in the file."""
import io, os, re, struct, sys
from fontTools.ttLib import TTFont
from lxml import etree
from .pkg import q

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import embed_fonts as EF  # noqa: E402

from .assets import fonts_dir
SKILL_FONTS = fonts_dir()


def eot_to_sfnt(b):
    eot, fds, ver, flags = struct.unpack('<IIII', b[:16])
    data = bytes(b[eot - fds:eot])
    if flags & 0x10000000:
        data = bytes(x ^ 0x50 for x in data)
    return data


def extract_fonts(pkg, out_dir):
    """Write each embedded font as a TTF/OTF named after the typeface PowerPoint uses. Returns faces."""
    os.makedirs(out_dir, exist_ok=True)
    faces = []
    for face, items in pkg.embedded_fonts().items():
        for style, part, _ in items:
            try:
                data = eot_to_sfnt(pkg.files[part])
                tt = TTFont(io.BytesIO(data))
                sub = {'regular': 'Regular', 'bold': 'Bold', 'italic': 'Italic', 'boldItalic': 'Bold Italic'}[style]
                n = tt['name']
                for rec in list(n.names):
                    if rec.nameID in (1, 2, 4, 6, 16, 17, 21, 22):
                        n.removeNames(nameID=rec.nameID)
                n.setName(face, 1, 3, 1, 0x409)
                n.setName(sub, 2, 3, 1, 0x409)
                n.setName(face + ('' if sub == 'Regular' else ' ' + sub), 4, 3, 1, 0x409)
                n.setName(re.sub(r'[^A-Za-z0-9-]', '', face) + '-' + sub.replace(' ', ''), 6, 3, 1, 0x409)
                if 'OS/2' in tt:
                    tt['OS/2'].usWeightClass = 700 if 'bold' in style.lower() else 400
                    tt['OS/2'].fsSelection = (tt['OS/2'].fsSelection & ~0b1100001) | (0x20 if style == 'bold' else 0x1 if style == 'italic' else 0x21 if style == 'boldItalic' else 0x40)
                if 'head' in tt:
                    tt['head'].macStyle = {'regular': 0, 'bold': 1, 'italic': 2, 'boldItalic': 3}[style]
                ext = '.otf' if data[:4] == b'OTTO' else '.ttf'
                tt.save(os.path.join(out_dir, re.sub(r'[^A-Za-z0-9]+', '_', face) + '_' + style + ext))
                faces.append(face)
            except Exception as e:
                print('font extract failed', face, e, file=sys.stderr)
    return sorted(set(faces))


def faces_in(pkg, parts):
    faces = set()
    for p in parts:
        faces.update(re.findall(r'typeface="([^"+][^"]*)"', etree.tostring(pkg.xml(p)).decode('utf8')))
    return faces


def swap_fonts(pkg, parts, mapping, bold_map=None):
    """mapping {old_face: new_face}; old faces like 'Inter Bold' map to new face with b=1 when
    bold_map says so ({old_face: True})."""
    n = 0
    for p in parts:
        x = pkg.xml(p)
        for tag in ('a:latin', 'a:ea', 'a:cs', 'a:sym'):
            for e in x.iter(q(tag)):
                old = e.get('typeface')
                if old in mapping:
                    e.set('typeface', mapping[old])
                    n += 1
                    if bold_map and old in bold_map:
                        rpr = e.getparent()
                        rpr.set('b', '1' if bold_map[old] else '0')
        pkg.touch(p)
    return n


def embed_skill_fonts(pkg, faces=None, subset=True):
    """Embed fonts the deck uses that exist in the skill's font folder and are not embedded yet."""
    idx = EF.font_index(SKILL_FONTS)
    have = pkg.embedded_fonts()
    used = faces or faces_in(pkg, pkg.slides())
    chars = set(range(0x20, 0x7F)) | set(range(0xA0, 0x100)) | {0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x20AC, 0x2192}
    for p in pkg.slides():
        for t in pkg.xml(p).iter(q('a:t')):
            chars.update(ord(c) for c in (t.text or ''))
    done = []
    for face in sorted(used):
        if face in have or face not in idx:
            continue
        styles = []
        for sty in ('regular', 'bold', 'italic', 'boldItalic'):
            path = idx[face].get(sty)
            if path:
                styles.append((sty, EF.eot_bytes(EF.subset_font(path, chars, subset))))
        if styles and pkg.add_embedded_font(face, styles):
            done.append(face)
    return done


THEME_FONTS = {
    # chosen by the user on Style Board 2 (display, body)
    'cyber': [('VT323', 'Share Tech Mono'), ('Orbitron', 'Share Tech Mono'), ('Black Ops One', 'Rajdhani')],
    'ai': [('Exo 2', 'Exo 2'), ('Orbitron', 'Exo 2'), ('Audiowide', 'Inter')],
    'telecom': [('Saira', 'Inter'), ('Rajdhani', 'Inter'), ('Sora', 'Inter'), ('Titillium Web', 'Titillium Web')],
    'energy': [('Barlow Condensed', 'Barlow'), ('Teko', 'Barlow'), ('Big Shoulders Display', 'Barlow')],
    'defense': [('Bebas Neue', 'Montserrat'), ('Big Shoulders Display', 'Inter'), ('Montserrat', 'Inter')],
    'event': [('Bungee', 'Montserrat'), ('Monoton', 'Montserrat'), ('Bowlby One', 'Inter'), ('Rubik Mono One', 'Inter')],
}


NUMLIKE = re.compile(r'^\s*[+\-]?\$?\d[\d.,]*\s?(%|[kKmMbB]\+?|\+|x)?\.?\s*$')


def swap_by_role(pkg, parts, display, body, keep=()):
    """Give every text shape the theme's display or body face depending on its role on the slide:
    big text and numbers get the display face, everything else the body face. Bold comes from the
    old face name ('Inter Bold' -> b=1). Faces in `keep` (e.g. icon fonts) are left alone."""
    W, _ = pkg.size()
    big = 36 * W / 12192000 * 100
    n = 0
    for p in parts:
        x = pkg.xml(p)
        sps = [sp for sp in x.iter(q('p:sp')) if sp.find('.//' + q('a:t')) is not None]
        sizes = []
        for sp in sps:
            szs = [int(r.get('sz')) for r in sp.iter(q('a:rPr')) if r.get('sz')]
            sizes.append(max(szs) if szs else 1800)
        top = max(sizes) if sizes else 1800
        for sp, mx in zip(sps, sizes):
            txt = ''.join(t.text or '' for t in sp.iter(q('a:t')))
            role_disp = mx >= big or mx >= 0.55 * top or bool(NUMLIKE.match(txt))
            face = display if role_disp else body
            for rpr in list(sp.iter(q('a:rPr'))) + list(sp.iter(q('a:endParaRPr'))):
                lat = rpr.find(q('a:latin'))
                old = lat.get('typeface') if lat is not None else ''
                if old in keep:
                    continue
                if re.search(r'(?i)bold|black|heavy|extra ?bold|semi ?bold', old):
                    rpr.set('b', '1')
                elif re.search(r'(?i)light|thin', old):
                    rpr.set('b', '0')
                for tag in ('a:latin', 'a:ea', 'a:cs', 'a:sym'):
                    e = rpr.find(q(tag))
                    if e is None and tag == 'a:latin':
                        e = etree.SubElement(rpr, q('a:latin'))
                        # schema order: latin must come before ea/cs/sym/hlink*: move it before them
                        for later in ('a:ea', 'a:cs', 'a:sym', 'a:hlinkClick', 'a:hlinkMouseOver', 'a:rtl', 'a:extLst'):
                            le = rpr.find(q(later))
                            if le is not None:
                                le.addprevious(e)
                                break
                    if e is not None:
                        e.set('typeface', face)
                        n += 1
        pkg.touch(p)
    return n
