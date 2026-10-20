#!/usr/bin/env python3
"""Template library for pro-pptx-studio (MIT License).

  python3 library.py index <folder-or-pptx>... --lib LIB [--source canva|slidescarnival|user] [--jobs 4]
      Adds every new .pptx to the library: copies it, extracts its fonts, renders every slide,
      analyses each slide (text slots, pictures, numbers) and guesses its role. Already indexed
      files (same content) are skipped, so you can point it at a folder you keep adding to.
  python3 library.py find "<topic words>" --lib LIB [--n 8] [--mode dark|light]
  python3 library.py show <id> --lib LIB              one line per slide: role, text slots
  python3 library.py sheet <id> --lib LIB             contact sheet with slide numbers (sheet.jpg)
  python3 library.py covers --lib LIB [--ids a,b]     contact sheet of covers (covers.jpg)
  python3 library.py set <id> --lib LIB [--rating yes|some|no] [--tags a,b] [--roles 1=cover,3=stats]
"""
import argparse, concurrent.futures as cf, glob, hashlib, json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from tplkit.pkg import Pkg, q, top_shapes, shape_box, shape_name, shape_id, shape_text  # noqa: E402
from tplkit.fonts import extract_fonts  # noqa: E402
from tplkit.assets import fonts_dir  # noqa: E402
from tplkit.text import run_style, current_lines  # noqa: E402
from tplkit.recolor import accent_hue  # noqa: E402

TOPICS = {
    'cyber': ['cyber', 'security', 'hacker', 'privacy', 'crime', 'threat', 'lock', 'firewall', 'malware'],
    'ai': ['ai', 'artificial', 'intelligence', 'robot', 'neural', 'machine learning', 'agent', 'futuristic'],
    'telecom': ['5g', 'network', 'telecom', 'wireless', 'cloud', 'connections', 'iot', 'signal'],
    'tech': ['tech', 'technology', 'software', 'it ', 'computer', 'digital', 'engineering', 'startup', 'electronics', 'blockchain', 'data'],
    'energy': ['energy', 'grid', 'power', 'solar', 'electric', 'industrial'],
    'space': ['space', 'galaxy', 'solar system', 'planet', 'aurora', 'comet', 'meteor', 'astronomy'],
    'defense': ['thesis', 'defense', 'defence', 'research', 'university', 'academic', 'college', 'lesson'],
    'pitch': ['pitch', 'business', 'proposal', 'brand', 'marketing', 'consulting', 'strategy', 'report', 'review'],
    'event': ['event', 'launch', 'webinar', 'conference', 'keynote', 'party', 'neon'],
    'social': ['instagram', 'post', 'banner', 'poster', 'story'],
}
# SlidesCarnival templates the user downloaded (names as saved); everything else is treated as Canva.
SC_NAMES = re.compile(r'(?i)slidescarnival|^ai agency pitch|^ai presentation tool|^aurora borealis|^bento design apple|bold text and color morph|^computer science college|^consumer electronics brand|cyber-futuristic ai|dark modern 3d brand guideline|^data privacy training|^digital media slides|^ethics of artificial|futuristic engineering center|gradient minimal software|gradient texture ui morph|^graphic design modern professional|^graphic design proposal|grey and neon yellow.*blockchain|introduction to cyber crime|minimal morph space|^mutius|red and purple 3d modern background|quarterly performance report|it software sales proposal|comets & meteors|^solar system lesson|^the use of ai in marketing|^year-end performance review')
NUM = re.compile(r'^\s*([+\-]?\$?\d[\d.,]*\s?(%|[kKmMbB]\+?|\+|x)?|0?\d\.)\s*$')
STEPNUM = re.compile(r'^\s*0?\d{1,2}\.?\s*$')


def slug(s):
    s = re.sub(r'(?i)\b(presentation|slides?|template|free|ppt|pptx)\b', '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return s[:48] or 'template'


def sha(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load_index(lib):
    p = os.path.join(lib, 'index.json')
    return json.load(open(p)) if os.path.exists(p) else {'templates': {}}


def save_index(lib, idx):
    json.dump(idx, open(os.path.join(lib, 'index.json'), 'w'), indent=1, ensure_ascii=False)


def render(pptx, font_dir, out_dir, width=640):
    """PDF via LibreOffice with the template's own fonts, then one JPG per slide."""
    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='lib_')
    conf = os.path.join(tmp, 'fonts.conf')
    open(conf, 'w').write('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig>'
                          '<include ignore_missing="yes">/etc/fonts/fonts.conf</include>'
                          f'<dir>{font_dir}</dir><dir>{os.path.join(os.path.dirname(os.path.dirname(font_dir)), "_fonts")}</dir>'
                          f'<dir>{fonts_dir()}</dir>'
                          f'<cachedir>{tmp}/cache</cachedir></fontconfig>')
    env = dict(os.environ, FONTCONFIG_FILE=conf, HOME=tmp)
    src = os.path.join(tmp, 'deck.pptx')
    shutil.copy(pptx, src)
    subprocess.run(['soffice', '-env:UserInstallation=file://' + tmp + '/lo', '--headless', '--convert-to', 'pdf', '--outdir', tmp, src],
                   env=env, capture_output=True, timeout=600)
    pdf = os.path.join(tmp, 'deck.pdf')
    if not os.path.exists(pdf):
        return []
    subprocess.run(['pdftoppm', '-jpeg', '-jpegopt', 'quality=85', '-scale-to-x', str(width), '-scale-to-y', '-1', pdf, os.path.join(out_dir, 's')], capture_output=True, timeout=600)
    files = sorted(glob.glob(os.path.join(out_dir, 's-*.jpg')))
    out = []
    for i, f in enumerate(files, 1):
        nf = os.path.join(out_dir, 's%02d.jpg' % i)
        os.replace(f, nf)
        out.append(nf)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def brightness(img_path):
    im = Image.open(img_path).convert('L').resize((64, 36))
    import numpy as np
    return float(np.asarray(im).mean() / 255)


def analyse_slide(pkg, part, n, total, W, H):
    x = pkg.xml(part)
    texts, pics = [], []

    def walk(sh, depth=0, group=None):
        ln = sh.tag.split('}')[1]
        box = shape_box(sh)
        if ln == 'grpSp':
            for ch in sh:
                if ch.tag.split('}')[1] in ('sp', 'pic', 'grpSp', 'graphicFrame', 'cxnSp'):
                    walk(ch, depth + 1, group or shape_name(sh))
            return
        body = sh.find('.//' + q('p:txBody'))
        txt = shape_text(sh).strip()
        if body is not None and txt:
            rpr = sh.find('.//' + q('a:rPr'))
            face, sz, b, spc, caps = run_style(rpr)
            texts.append({'name': shape_name(sh), 'id': shape_id(sh), 'text': txt[:160], 'chars': len(txt), 'size': sz, 'face': face,
                          'bold': b, 'lines': current_lines(sh) if depth == 0 else None, 'box': box if depth == 0 else None,
                          'group': group, 'top': depth == 0})
        blip = sh.find('.//' + q('a:blip'))
        if blip is not None and box:
            rid = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            media = None
            for i, ty, t, m in pkg.rel_list(part):
                if i == rid:
                    media = pkg.resolve(part, t)
            area = box[2] * box[3] / (W * H)
            pics.append({'name': shape_name(sh), 'id': shape_id(sh), 'box': box, 'area': round(area, 3), 'media': media,
                         'png': bool(media and media.lower().endswith('.png')), 'group': group, 'top': depth == 0})

    for sh in top_shapes(x):
        walk(sh)
    sizes = sorted((t['size'] for t in texts if not NUM.match(t['text'])), reverse=True)
    for t in texts:
        if NUM.match(t['text']) and t['size'] >= 20:
            t['kind'] = 'step' if STEPNUM.match(t['text']) else 'number'
        elif sizes and t['size'] == sizes[0] and t['chars'] < 90:
            t['kind'] = 'title'
        elif t['chars'] > 90:
            t['kind'] = 'body'
        elif t['size'] < (sizes[0] * 0.45 if sizes else 12):
            t['kind'] = 'label'
        else:
            t['kind'] = 'subtitle'
    numbers = [t for t in texts if t['kind'] == 'number']
    steps = [t for t in texts if t['kind'] == 'step']
    alltxt = ' '.join(t['text'].lower() for t in texts)
    photos = [p for p in pics if 0.04 < p['area'] < 0.9]
    bg = [p for p in pics if p['area'] >= 0.9]
    if n == 1:
        role = 'cover'
    elif n == total and len(texts) <= 5:
        role = 'closing'
    elif re.search(r'agenda|contents|table of content|outline|sommaire', alltxt):
        role = 'agenda'
    elif len(steps) >= 3:
        role = 'steps'
    elif len(numbers) >= 2:
        role = 'stats'
    elif len(numbers) == 1:
        role = 'big-number'
    elif re.search(r'thank|questions|merci', alltxt):
        role = 'closing'
    elif len(photos) >= 3:
        role = 'gallery-team'
    elif len(texts) <= 2 and not photos:
        role = 'section'
    elif photos:
        role = 'image-text'
    elif len([t for t in texts if t['kind'] in ('subtitle', 'label')]) >= 4:
        role = 'cards'
    else:
        role = 'text'
    return {'n': n, 'part': part, 'role': role, 'texts': texts, 'pictures': pics, 'has_background_image': bool(bg),
            'counts': {'texts': len(texts), 'numbers': len(numbers), 'steps': len(steps), 'photos': len(photos)}}


def palette(pkg, parts, k=6):
    from collections import Counter
    from lxml import etree
    from tplkit.recolor import hex_to_hsv
    c = Counter()
    for p in parts:
        for hx in re.findall(r'srgbClr val="([0-9A-Fa-f]{6})"', etree.tostring(pkg.xml(p)).decode('utf8')):
            c[hx.upper()] += 1
    return [h for h, _ in c.most_common(k * 2)][:k]


def index_one(path, lib, source, rating=None):
    h = sha(path)
    name = os.path.splitext(os.path.basename(path))[0]
    tid = slug(name)
    d = os.path.join(lib, tid)
    k = 2
    while os.path.exists(d) and json.load(open(os.path.join(d, 'meta.json'))).get('sha') != h:
        d = os.path.join(lib, '%s-%d' % (tid, k)); k += 1
    tid = os.path.basename(d)
    os.makedirs(d, exist_ok=True)
    shutil.copy(path, os.path.join(d, 'template.pptx'))
    pkg = Pkg(os.path.join(d, 'template.pptx'))
    faces = extract_fonts(pkg, os.path.join(d, 'fonts'))
    thumbs = render(os.path.join(d, 'template.pptx'), os.path.join(d, 'fonts'), os.path.join(d, 'slides'))
    W, H = pkg.size()
    parts = pkg.slides()
    slides = [analyse_slide(pkg, p, i + 1, len(parts), W, H) for i, p in enumerate(parts)]
    for s, t in zip(slides, thumbs):
        s['thumb'] = os.path.relpath(t, d)
    used_faces = sorted({t['face'] for s in slides for t in s['texts']})
    low = name.lower() + ' ' + ' '.join(t['text'].lower() for s in slides for t in s['texts'][:6])
    tags = [k for k, words in TOPICS.items() if any(re.search(r'\b' + re.escape(w.strip()) + r'\b', low) for w in words)]
    hue = accent_hue(pkg, parts)
    if source == 'auto':
        source = 'slidescarnival' if SC_NAMES.search(name) else 'canva'
    meta = {
        'id': tid, 'name': name, 'sha': h, 'source': source, 'file': 'template.pptx', 'source_file': os.path.basename(path), 'size_emu': [W, H],
        'aspect': round(W / H, 3), 'slides_count': len(parts), 'fonts_used': used_faces, 'fonts_embedded': faces,
        'palette': palette(pkg, parts), 'accent_hue': round(hue * 360) if hue is not None else None,
        'mode': ('dark' if brightness(thumbs[0]) < 0.45 else 'light') if thumbs else None,
        'tags': tags, 'rating': rating, 'notes': '',
        'license': {'canva': 'Canva Content License: for the owner\'s own designs only; do not share the template itself.',
                    'slidescarnival': 'CC BY 4.0: keep a credit to SlidesCarnival (slidescarnival.com) in decks built on it; do not redistribute the file as is.',
                    'user': 'User-provided.'}.get(source, source),
        'slides': slides,
    }
    json.dump(meta, open(os.path.join(d, 'meta.json'), 'w'), indent=1, ensure_ascii=False)
    make_sheet(d, meta)
    return tid, meta


def make_sheet(d, meta, cols=4, w=400):
    ims = []
    for s in meta['slides']:
        p = os.path.join(d, s.get('thumb', ''))
        if s.get('thumb') and os.path.exists(p):
            im = Image.open(p).convert('RGB')
            im = im.resize((w, int(w * im.height / im.width)))
            dr = ImageDraw.Draw(im)
            lab = '%d %s' % (s['n'], s.get('role_override') or s['role'])
            dr.rectangle([0, 0, 8 + 8 * len(lab), 22], fill=(0, 0, 0))
            dr.text((4, 4), lab, fill=(255, 255, 0))
            ims.append(im)
    if not ims:
        return
    h = max(i.height for i in ims)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * w, rows * h), (30, 30, 30))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    sheet.save(os.path.join(d, 'sheet.jpg'), quality=80)


def cmd_index(a):
    os.makedirs(a.lib, exist_ok=True)
    idx = load_index(a.lib)
    known = {v['sha'] for v in idx['templates'].values()}
    files = []
    for p in a.paths:
        files += sorted(glob.glob(os.path.join(p, '*.pptx'))) if os.path.isdir(p) else [p]
    todo = [f for f in files if sha(f) not in known]
    print(json.dumps({'found': len(files), 'new': len(todo)}))
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(index_one, f, a.lib, a.source): f for f in todo}
        for fu in cf.as_completed(futs):
            try:
                tid, meta = fu.result()
                idx['templates'][tid] = {k: meta.get(k) for k in ('id', 'name', 'sha', 'source', 'source_file', 'tags', 'mode', 'accent_hue', 'palette', 'rating', 'slides_count', 'aspect', 'fonts_used')}
                idx['templates'][tid]['roles'] = [s.get('role_override') or s['role'] for s in meta['slides']]
                print(json.dumps({'indexed': tid, 'slides': meta['slides_count'], 'tags': meta['tags'], 'mode': meta['mode']}))
                save_index(a.lib, idx)
            except Exception as e:
                print(json.dumps({'failed': futs[fu], 'error': repr(e)}))


def cmd_find(a):
    idx = load_index(a.lib)
    words = a.topic.lower()
    toks = [w for w in re.findall(r'[a-z0-9]+', words) if len(w) > 1]
    want = {k for k, ws in TOPICS.items() if k in words or any(w.strip() in words for w in ws)}
    rows = []
    for t in idx['templates'].values():
        if t.get('rating') == 'no':
            continue
        extra = set(t.get('extra_tags', []))
        sc = 3 * len(want & extra) + 1 * len(want & set(t['tags']))
        sc += 2 * sum(1 for e in extra if any(e in tok or tok in e for tok in toks if len(tok) > 2))
        sc += {'yes': 2, 'some': 0.5}.get(t.get('rating'), 1)
        if a.mode and t.get('mode') == a.mode:
            sc += 1
        if 'cover-only' in extra:
            sc -= 1.5
        roles = set(t.get('roles', []))
        sc += 0.3 * len(roles & {'stats', 'steps', 'agenda', 'image-text', 'closing', 'chart', 'process'})
        sc += 0.5 if t['slides_count'] >= 8 else 0
        rows.append((round(sc, 2), t['id'], t['name'], t.get('mode'), sorted(extra) or t['tags'], t.get('rating')))
    rows.sort(reverse=True)
    for r in rows[:a.n]:
        print(json.dumps({'score': r[0], 'id': r[1], 'mode': r[3], 'tags': r[4], 'rating': r[5]}))


def cmd_show(a):
    meta = json.load(open(os.path.join(a.lib, a.id, 'meta.json')))
    print('%s  [%s]  %s  fonts=%s  palette=%s' % (meta['id'], meta['mode'], meta['name'], meta['fonts_used'], meta['palette']))
    for s in meta['slides']:
        role = s.get('role_override') or s['role']
        slots = ['%s:%s(%s,%dpt,%sL)"%s"' % (t['kind'], t['name'], t['face'], t['size'], t['lines'], t['text'][:28].replace('\n', ' ')) for t in s['texts'] if t['top']]
        grp = ['%s>%s"%s"' % (t['group'], t['name'], t['text'][:18]) for t in s['texts'] if not t['top']]
        pics = ['%s(%.2f%s)' % (p['name'], p['area'], ',png' if p['png'] else '') for p in s['pictures'] if p['top']]
        print('#%d %-12s %s' % (s['n'], role, ' | '.join(slots)))
        if grp:
            print('    in groups: ' + ' | '.join(grp))
        if pics:
            print('    pictures: ' + ' '.join(pics))


def cmd_sheet(a):
    d = os.path.join(a.lib, a.id)
    make_sheet(d, json.load(open(os.path.join(d, 'meta.json'))))
    print(os.path.join(d, 'sheet.jpg'))


def cmd_covers(a):
    idx = load_index(a.lib)
    ids = a.ids.split(',') if a.ids else sorted(idx['templates'])
    w, cols = 360, 4
    ims = []
    for i in ids:
        p = os.path.join(a.lib, i, 'slides', 's01.jpg')
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert('RGB')
        im = im.resize((w, int(w * im.height / im.width)))
        im2 = Image.new('RGB', (w, im.height + 20), (20, 20, 20))
        im2.paste(im, (0, 0))
        ImageDraw.Draw(im2).text((4, im.height + 4), i[:52], fill=(230, 230, 230))
        ims.append(im2)
    h = max(x.height for x in ims)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * w, rows * h), (10, 10, 10))
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % cols) * w, (k // cols) * h))
    out = a.out or os.path.join(a.lib, 'covers.jpg')
    sheet.save(out, quality=82)
    print(out)


def cmd_rerender(a):
    """Render slides again (after adding fonts to LIB/_fonts) and rebuild the contact sheet."""
    idx = load_index(a.lib)
    ids = sorted(idx['templates']) if a.id == 'all' else a.id.split(',')
    def one(tid):
        d = os.path.join(a.lib, tid)
        meta = json.load(open(os.path.join(d, 'meta.json')))
        src = os.path.join(d, 'template.pptx')
        if not os.path.exists(src):
            sys.path.insert(0, HERE)
            from tplbuild import template_path
            src = template_path(a.lib, tid)
        thumbs = render(src, os.path.join(d, 'fonts'), os.path.join(d, 'slides'))
        for s_, t in zip(meta['slides'], thumbs):
            s_['thumb'] = os.path.relpath(t, d)
        if thumbs:
            meta['mode'] = 'dark' if brightness(thumbs[0]) < 0.45 else 'light'
        json.dump(meta, open(os.path.join(d, 'meta.json'), 'w'), indent=1, ensure_ascii=False)
        make_sheet(d, meta)
        return tid, len(thumbs)
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for tid, n in ex.map(one, ids):
            print(json.dumps({'rendered': tid, 'slides': n}))


def cmd_assets(a):
    """Extract the cut-out pictures (PNG with transparency) of a template, or of one slide, into a
    folder with a numbered contact sheet, for the depth effect and decorations."""
    sys.path.insert(0, HERE)
    from tplbuild import template_path
    import io as _io
    pk = Pkg(template_path(a.lib, a.id))
    parts = pk.slides()
    sel = [parts[a.slide - 1]] if a.slide else parts
    os.makedirs(a.out, exist_ok=True)
    seen, files = set(), []
    for sp in sel:
        for rid, rtype, target, mode in pk.rel_list(sp):
            if mode == 'External' or not rtype.endswith('/image'):
                continue
            mp = pk.resolve(sp, target)
            if mp in seen or not mp.lower().endswith('.png'):
                continue
            seen.add(mp)
            try:
                im = Image.open(_io.BytesIO(pk.files[mp]))
            except Exception:
                continue
            if im.mode not in ('RGBA', 'LA') and 'transparency' not in im.info:
                continue
            im = im.convert('RGBA')
            alpha = im.getchannel('A')
            cov = sum(1 for v in alpha.resize((64, 64)).getdata() if v > 20) / 4096
            if cov < 0.05 or cov > 0.97 or min(im.size) < 120:
                continue
            bbox = alpha.getbbox()
            if bbox:
                im = im.crop(bbox)
            f = os.path.join(a.out, '%s-%02d.png' % (a.id[:24], len(files) + 1))
            im.save(f)
            files.append(f)
    if files:
        w = 220
        cols = 6
        rows = (len(files) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * w, rows * (w + 20)), (40, 40, 46))
        dr = ImageDraw.Draw(sheet)
        for k, f in enumerate(files):
            im = Image.open(f)
            im.thumbnail((w - 10, w - 10))
            x0, y0 = (k % cols) * w, (k // cols) * (w + 20)
            sheet.paste(im, (x0 + (w - im.width) // 2, y0 + (w - im.height) // 2), im)
            dr.text((x0 + 4, y0 + w + 2), os.path.basename(f)[-6:-4], fill=(255, 220, 60))
        sheet.save(os.path.join(a.out, 'assets-sheet.jpg'), quality=85)
    print(json.dumps({'cutouts': len(files), 'folder': a.out, 'sheet': os.path.join(a.out, 'assets-sheet.jpg') if files else None}))


def cmd_set(a):
    d = os.path.join(a.lib, a.id)
    meta = json.load(open(os.path.join(d, 'meta.json')))
    idx = load_index(a.lib)
    if a.rating:
        meta['rating'] = a.rating
    if a.tags:
        meta['extra_tags'] = [t.strip() for t in a.tags.split(',') if t.strip()]
    if a.notes:
        meta['notes'] = a.notes
    if a.roles:
        for kv in a.roles.split(','):
            k, v = kv.split('=')
            meta['slides'][int(k) - 1]['role_override'] = v.strip()
    json.dump(meta, open(os.path.join(d, 'meta.json'), 'w'), indent=1, ensure_ascii=False)
    t = idx['templates'][a.id]
    t['rating'] = meta.get('rating')
    t['extra_tags'] = meta.get('extra_tags', [])
    t['roles'] = [s.get('role_override') or s['role'] for s in meta['slides']]
    t['notes'] = meta.get('notes', '')
    save_index(a.lib, idx)
    make_sheet(d, meta)
    print(json.dumps({'id': a.id, 'rating': t['rating'], 'roles': t['roles'], 'extra_tags': t['extra_tags']}))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('index'); s.add_argument('paths', nargs='+'); s.add_argument('--lib', required=True); s.add_argument('--source', default='auto'); s.add_argument('--jobs', type=int, default=3)
    s = sub.add_parser('find'); s.add_argument('topic'); s.add_argument('--lib', required=True); s.add_argument('--n', type=int, default=8); s.add_argument('--mode')
    s = sub.add_parser('show'); s.add_argument('id'); s.add_argument('--lib', required=True)
    s = sub.add_parser('sheet'); s.add_argument('id'); s.add_argument('--lib', required=True)
    s = sub.add_parser('covers'); s.add_argument('--lib', required=True); s.add_argument('--ids'); s.add_argument('--out')
    s = sub.add_parser('rerender'); s.add_argument('id'); s.add_argument('--lib', required=True); s.add_argument('--jobs', type=int, default=3)
    s = sub.add_parser('assets'); s.add_argument('id'); s.add_argument('--lib', required=True); s.add_argument('--slide', type=int); s.add_argument('--out', required=True)
    s = sub.add_parser('set'); s.add_argument('id'); s.add_argument('--lib', required=True); s.add_argument('--rating'); s.add_argument('--tags'); s.add_argument('--roles'); s.add_argument('--notes')
    a = ap.parse_args()
    {'index': cmd_index, 'find': cmd_find, 'show': cmd_show, 'sheet': cmd_sheet, 'covers': cmd_covers, 'set': cmd_set, 'rerender': cmd_rerender, 'assets': cmd_assets}[a.cmd](a)


if __name__ == '__main__':
    main()
