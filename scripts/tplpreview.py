#!/usr/bin/env python3
"""Show the user's title on the covers of the best-matching library templates (MIT License).

  python3 tplpreview.py brief.json outdir

brief.json: {"title": "...", "subtitle": "...", "meta": ["Presented by ...", "June 2026"],
             "topic": "cybersecurity awareness", "theme": "cyber", "n": 6,
             "templates": [optional ids], "color": "#00FF88" (optional recolor variant),
             "lib": optional library path, "mode": "dark"|"light"}
Writes outdir/covers.jpg (letters A, B, ...) and outdir/choices.json. For every template it renders
the cover as designed; when "theme" is set it also renders one variant with the theme fonts.
"""
import concurrent.futures as cf, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
import tplbuild  # noqa: E402
from tplkit import fonts as F  # noqa: E402

PLACEHOLDER = re.compile(r'(?i)really|borcelle|www\.|\.com|@|presented by|lars|aaron|adam|olivia|timmerman|salford|larana|ginyard|cloudlet|company|inc\.|university|20[2-9]\d|\b\d{1,2}(st|nd|rd|th)?\b')


def _colors(lib, tid, names):
    """First-run fill color of each named shape on the cover (None when it is not a plain color)."""
    from tplkit import pkg as P
    try:
        pk = P.Pkg(tplbuild.template_path(lib, tid))
        x = pk.xml(pk.slides()[0])
    except Exception:
        return {}
    out = {}
    for n in names:
        sh = P.find_shape(x, n)
        c = sh.find('.//' + P.q('a:rPr') + '/' + P.q('a:solidFill')) if sh is not None else None
        v = c[0].get('val') if c is not None and len(c) else None
        out[n] = v
    return out


def cover_plan(meta, brief, lib=None, tid=None):
    s = meta['slides'][0]
    tops = [t for t in s['texts'] if t['top']]
    titles = [t for t in tops if t['kind'] == 'title']
    if not titles and tops:
        titles = [max(tops, key=lambda t: t['size'])]
    rest = [t for t in tops if t not in titles]
    text, remove = {}, []
    words = brief['title'].split()
    same_look = False
    if len(titles) >= 2 and len(words) > 4 and lib:
        cols = _colors(lib, tid, [t['name'] for t in titles[:2]])
        same_look = len(set(cols.values())) == 1
    if len(titles) >= 2 and len(words) > 4 and same_look:
        # a long title over a "Digital / Media" style cover: one headline across both slots
        titles.sort(key=lambda t: (t['box'] or [0, 0])[1])
        text[titles[0]['name']] = {'text': brief['title'], 'fit': 'title', 'merge': [t['name'] for t in titles[1:]]}
    elif len(titles) >= 2:
        titles.sort(key=lambda t: (t['box'] or [0, 0])[1])
        k = max(1, round(len(words) * len(titles[0]['text']) / max(1, sum(len(t['text']) for t in titles[:2]))))
        text[titles[0]['name']] = {'text': ' '.join(words[:k]), 'fit': 'title'}
        text[titles[1]['name']] = {'text': ' '.join(words[k:]) or ' ', 'fit': 'title'}
        for t in titles[2:]:
            remove.append(t['name'])
    elif titles:
        text[titles[0]['name']] = {'text': brief['title'], 'fit': 'title'}
    rest.sort(key=lambda t: -t['chars'])
    if brief.get('subtitle') and rest and rest[0]['chars'] >= 12:
        text[rest[0]['name']] = brief['subtitle']
        rest = rest[1:]
    meta_items = list(brief.get('meta', []))
    rest.sort(key=lambda t: ((t['box'] or [0, 0])[1], (t['box'] or [0])[0]))
    for t in rest:
        if t['kind'] in ('number', 'step') and not PLACEHOLDER.search(t['text']):
            remove.append(t['name'])
        elif meta_items:
            text[t['name']] = meta_items.pop(0)
        else:
            remove.append(t['name'])
    return text, remove


def render_one(pptx, outdir):
    subprocess.run([sys.executable, os.path.join(HERE, 'render.py'), pptx, outdir, '--dpi', '40', '--cols', '1'], capture_output=True, timeout=600)
    f = os.path.join(outdir, 'slide-1.jpg')
    return f if os.path.exists(f) else None


def main():
    brief = json.load(open(sys.argv[1]))
    out = os.path.abspath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    lib = tplbuild.lib_path(brief)
    if brief.get('templates'):
        ids = brief['templates']
    else:
        r = subprocess.run([sys.executable, os.path.join(HERE, 'library.py'), 'find', brief.get('topic', brief['title']), '--lib', lib, '--n', str(brief.get('n', 6) + 4)] +
                           (['--mode', brief['mode']] if brief.get('mode') else []), capture_output=True, text=True)
        rows = [json.loads(l) for l in r.stdout.splitlines() if l.strip()]
        ids = []
        for row in rows:
            m = json.load(open(os.path.join(lib, row['id'], 'meta.json')))
            tags = set(m.get('extra_tags', []))
            if tags & {'kit', 'document', 'a4', 'square', 'portrait', 'poster'} or abs(m['aspect'] - 16 / 9) > 0.05:
                continue
            ids.append(row['id'])
        ids = ids[:brief.get('n', 6)]
    jobs = []
    for tid in ids:
        meta = json.load(open(os.path.join(lib, tid, 'meta.json')))
        text, remove = cover_plan(meta, brief, lib, tid)
        variants = [('as designed', None)]
        if brief.get('theme'):
            variants.append(('%s fonts' % brief['theme'], brief['theme'] + ':0'))
        for label, ft in variants:
            spec = {'lib': lib, 'base': tid, 'out': os.path.join(out, '%s%s.pptx' % (tid, '' if not ft else '-' + ft.replace(':', ''))),
                    'motion': 'none', 'slides': [{'use': '#1', 'text': text, 'remove': remove, 'animate': 'none'}]}
            if ft:
                spec['fonts'] = {'theme': ft}
            if brief.get('color') and ft:
                spec['recolor'] = brief['color']
            jobs.append((tid, label, ft, spec))
    results = []
    for tid, label, ft, spec in jobs:
        try:
            rep = tplbuild.build(spec)
            txt = spec['slides'][0]['text']
            heads = {k for k, v in txt.items() if isinstance(v, dict) and v.get('fit') == 'title'}
            over = [n for f in rep.get('fits', []) if f.get('shape') in heads for n in f.get('overlaps', []) if n not in txt]
            if over:   # stickers placed over the sample title would hide the new one: drop them
                spec['slides'][0]['remove'] = spec['slides'][0]['remove'] + over
                tplbuild.build(spec)
            results.append((tid, label, ft, spec['out']))
        except Exception as e:
            print(json.dumps({'template': tid, 'variant': label, 'error': repr(e)}))
    with cf.ThreadPoolExecutor(3) as ex:
        imgs = list(ex.map(lambda r: render_one(r[3], r[3][:-5] + '-r'), results))
    W = 520
    tiles = []
    choices = {}
    for k, ((tid, label, ft, path), img) in enumerate(zip(results, imgs)):
        if not img:
            continue
        letter = chr(65 + len(choices)) if len(choices) < 26 else str(len(choices))
        choices[letter] = {'template': tid, 'fonts': ft, 'variant': label, 'pptx': path}
        im = Image.open(img).convert('RGB')
        im = im.resize((W, int(W * im.height / im.width)))
        t = Image.new('RGB', (W, im.height + 34), (18, 18, 22))
        t.paste(im, (0, 0))
        d = ImageDraw.Draw(t)
        try:
            fnt = ImageFont.truetype(os.path.join(F.SKILL_FONTS, 'Inter', 'Inter-Bold.ttf'), 18)
            fs = ImageFont.truetype(os.path.join(F.SKILL_FONTS, 'Inter', 'Inter-Regular.ttf'), 13)
        except Exception:
            fnt = fs = None
        d.text((8, im.height + 7), letter, fill=(255, 220, 60), font=fnt)
        d.text((34, im.height + 10), ('%s · %s' % (tid, label))[:70], fill=(220, 220, 225), font=fs)
        tiles.append(t)
    cols = 2 if brief.get('theme') else 3
    h = max(t.height for t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * W + (cols + 1) * 10, rows * h + (rows + 1) * 10), (60, 60, 66))
    for i, t in enumerate(tiles):
        sheet.paste(t, (10 + (i % cols) * (W + 10), 10 + (i // cols) * (h + 10)))
    sheet.save(os.path.join(out, 'covers.jpg'), quality=86)
    json.dump(choices, open(os.path.join(out, 'choices.json'), 'w'), indent=1)
    print(json.dumps({'sheet': os.path.join(out, 'covers.jpg'), 'choices': {k: '%s (%s)' % (v['template'], v['variant']) for k, v in choices.items()}}, indent=1))


if __name__ == '__main__':
    main()
