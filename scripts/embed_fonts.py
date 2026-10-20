#!/usr/bin/env python3
"""Embed the fonts a .pptx uses into the file itself (EOT parts, the way PowerPoint and Canva do it),
so the deck looks the same on a laptop that does not have those fonts installed. MIT License.

usage: python3 embed_fonts.py deck.pptx <fonts_dir> [--no-subset]
Only fonts found in <fonts_dir> (OFL fonts shipped with the skill) are embedded; others are left alone.
Needs: fontTools (pip install fonttools).
"""
import io, os, re, struct, sys, zipfile, json
from fontTools.ttLib import TTFont
from fontTools import subset

def font_index(d):
    idx = {}
    for root, _, files in os.walk(d):
        for f in files:
            if not f.lower().endswith(('.ttf', '.otf')): continue
            p = os.path.join(root, f)
            try:
                t = TTFont(p, lazy=True)
                fam = t['name'].getDebugName(1); sty = (t['name'].getDebugName(2) or 'Regular').lower()
                key = {'regular': 'regular', 'bold': 'bold', 'italic': 'italic', 'bold italic': 'boldItalic'}.get(sty)
                if fam and key: idx.setdefault(fam, {})[key] = p
            except Exception:
                pass
    return idx

def eot_bytes(data):
    t = TTFont(io.BytesIO(data))
    nm = t['name']; os2 = t['OS/2']
    def s(i):
        v = nm.getDebugName(i) or ''
        return v.encode('utf-16-le')
    pan = os2.panose
    panose = bytes([pan.bFamilyType, pan.bSerifStyle, pan.bWeight, pan.bProportion, pan.bContrast, pan.bStrokeVariation, pan.bArmStyle, pan.bLetterForm, pan.bMidline, pan.bXHeight])
    italic = 1 if (os2.fsSelection & 1) else 0
    body = panose + struct.pack('<BBIHH', 1, italic, os2.usWeightClass, 0, 0x504C)
    body += struct.pack('<IIII', os2.ulUnicodeRange1, os2.ulUnicodeRange2, os2.ulUnicodeRange3, os2.ulUnicodeRange4)
    body += struct.pack('<II', getattr(os2, 'ulCodePageRange1', 1), getattr(os2, 'ulCodePageRange2', 0))
    body += struct.pack('<I', t['head'].checkSumAdjustment) + b'\0' * 16 + struct.pack('<H', 0)
    for i, nid in enumerate((1, 2, 5, 4)):
        v = s(nid); body += struct.pack('<H', len(v)) + v
        body += struct.pack('<H', 0)  # padding2..padding5
    body += struct.pack('<H', 0)  # RootStringSize (version 2.1+)
    body += struct.pack('<II', 0, 0) + struct.pack('<H', 0) + struct.pack('<H', 0) + struct.pack('<II', 0, 0)  # v2.2 fields, all empty
    total = 16 + len(body) + len(data)
    return struct.pack('<IIII', total, len(data), 0x00020002, 0) + body + data

def subset_font(path, chars, do_subset=True):
    f = TTFont(path)
    if do_subset:
        o = subset.Options(); o.name_IDs = ['*']; o.notdef_outline = True; o.layout_features = ['kern', 'liga', 'calt', 'ccmp', 'locl', 'mark', 'mkmk', 'case']; o.hinting = False
        sb = subset.Subsetter(o); sb.populate(unicodes=sorted(chars)); sb.subset(f)
    f['OS/2'].fsType = 0
    b = io.BytesIO(); f.save(b); return b.getvalue()

def main():
    deck, fdir = sys.argv[1], sys.argv[2]; do_subset = '--no-subset' not in sys.argv
    z = zipfile.ZipFile(deck)
    files = {n: z.read(n) for n in z.namelist()}; z.close()
    if any(n.startswith('ppt/fonts/') for n in files):
        print(json.dumps({"embedded": [], "note": "deck already has embedded fonts"})); return
    faces, chars = set(), set(range(0x20, 0x7F)) | set(range(0xA0, 0x100)) | {0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x20AC, 0x25B2, 0x25BC, 0x2192}
    for n, b in files.items():
        if n.endswith('.xml') and (n.startswith('ppt/slides/') or n.startswith('ppt/slideLayouts/') or n.startswith('ppt/slideMasters/') or n.startswith('ppt/theme/') or n.startswith('ppt/charts/') or n.startswith('ppt/notesSlides/')):
            x = b.decode('utf8', 'ignore')
            faces.update(re.findall(r'<a:latin typeface="([^"+][^"]*)"', x) if n.startswith('ppt/theme/') else re.findall(r'typeface="([^"+][^"]*)"', x))
            for t in re.findall(r'<a:t>([^<]*)</a:t>', x) + re.findall(r'<c:v>([^<]*)</c:v>', x):
                t = t.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&apos;', "'")
                chars.update(ord(ch) for ch in t)
    idx = font_index(fdir)
    use = [f for f in sorted(faces) if f in idx]
    if not use:
        print(json.dumps({"embedded": [], "missing": sorted(faces)})); return
    pres = files['ppt/presentation.xml'].decode('utf8')
    rels = files['ppt/_rels/presentation.xml.rels'].decode('utf8')
    rid_nums = [int(x) for x in re.findall(r'Id="rId(\d+)"', rels)]; nxt = max(rid_nums or [0]) + 1
    lst = ''; k = 1; embedded = []
    for fam in use:
        parts = ''
        for sty in ('regular', 'bold', 'italic', 'boldItalic'):
            p = idx[fam].get(sty)
            if not p: continue
            data = eot_bytes(subset_font(p, chars, do_subset))
            name = f'ppt/fonts/font{k}.fntdata'; files[name] = data
            rels = rels.replace('</Relationships>', f'<Relationship Id="rId{nxt}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/font" Target="fonts/font{k}.fntdata"/></Relationships>')
            parts += f'<p:{sty} r:id="rId{nxt}"/>'; nxt += 1; k += 1
        famx = fam.replace('&', '&amp;').replace('"', '&quot;')
        lst += f'<p:embeddedFont><p:font typeface="{famx}" charset="1"/>{parts}</p:embeddedFont>'
        embedded.append(fam)
    block = f'<p:embeddedFontLst>{lst}</p:embeddedFontLst>'
    m = re.search(r'<p:notesSz\b[^>]*/>|<p:notesSz\b[^>]*>.*?</p:notesSz>', pres, re.S)
    if not m: raise SystemExit('presentation.xml has no notesSz; cannot place embeddedFontLst')
    pres = pres[:m.end()] + block + pres[m.end():]
    head = re.search(r'<p:presentation\b[^>]*>', pres).group(0); newhead = head
    if 'embedTrueTypeFonts' not in head: newhead = newhead.replace('<p:presentation', '<p:presentation embedTrueTypeFonts="1"', 1)
    if 'saveSubsetFonts' not in head: newhead = newhead.replace('<p:presentation', '<p:presentation saveSubsetFonts="1"', 1)
    pres = pres.replace(head, newhead, 1)
    files['ppt/presentation.xml'] = pres.encode('utf8'); files['ppt/_rels/presentation.xml.rels'] = rels.encode('utf8')
    ct = files['[Content_Types].xml'].decode('utf8')
    if 'Extension="fntdata"' not in ct:
        ct = ct.replace('<Default ', '<Default Extension="fntdata" ContentType="application/x-fontdata"/><Default ', 1)
    files['[Content_Types].xml'] = ct.encode('utf8')
    tmp = deck + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as out:
        out.writestr('[Content_Types].xml', files.pop('[Content_Types].xml'))
        for n, b in files.items(): out.writestr(n, b)
    os.replace(tmp, deck)
    print(json.dumps({"embedded": embedded, "missing": sorted(set(faces) - set(use))}))

if __name__ == '__main__':
    main()
