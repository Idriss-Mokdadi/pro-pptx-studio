"""Replace text inside template shapes while keeping the designer's formatting, and fit it
(MIT License). Fitting measures real glyph widths with the template's own fonts, so a longer
title shrinks until it takes no more lines than the template's sample text did."""
import copy, glob, os, re, subprocess
from lxml import etree
from PIL import ImageFont
from .pkg import q, find_shape, shape_box

EMU_PT = 12700
_FONTS = None
_EXTRA_DIRS = []


def add_font_dir(d):
    global _FONTS
    if d and os.path.isdir(d) and d not in _EXTRA_DIRS:
        _EXTRA_DIRS.append(d)
        _FONTS = None


def _index():
    global _FONTS
    if _FONTS is not None:
        return _FONTS
    from fontTools.ttLib import TTFont
    idx = {}
    paths = []
    for d in _EXTRA_DIRS:
        paths += glob.glob(os.path.join(d, '**', '*.[ot]tf'), recursive=True)
    try:
        out = subprocess.run(['fc-list', '--format', '%{file}\n'], capture_output=True, text=True, timeout=30).stdout
        paths += [p for p in out.splitlines() if p.lower().endswith(('.ttf', '.otf'))]
    except Exception:
        pass
    for p in paths:
        try:
            t = TTFont(p, lazy=True, fontNumber=0)
            n = t['name']
            fam = n.getDebugName(16) or n.getDebugName(1)
            sty = (n.getDebugName(17) or n.getDebugName(2) or 'Regular').lower()
            full = n.getDebugName(4) or fam
            bold = 'bold' in sty or 'black' in sty or 'heavy' in sty
            for key in {fam, full, n.getDebugName(1)}:
                if key:
                    idx.setdefault(key, {}).setdefault('b' if bold else 'r', p)
        except Exception:
            continue
    _FONTS = idx
    return idx


_cache = {}


def font_for(face, bold=False, size_pt=20):
    idx = _index()
    ent = idx.get(face) or idx.get(face.replace(' Bold', '')) or {}
    path = ent.get('b' if bold else 'r') or ent.get('r') or ent.get('b')
    if not path:
        fb = idx.get('DejaVu Sans') or idx.get('Liberation Sans') or {}
        path = fb.get('b' if bold else 'r') or fb.get('r')
    key = (path, round(size_pt * 4))
    if key not in _cache:
        _cache[key] = ImageFont.truetype(path, max(1, int(round(size_pt * 4)))) if path else None
    return _cache[key], path is not None and bool(ent)


def text_width_emu(text, face, size_pt, bold=False, spc=0, caps=False):
    f, _ = font_for(face, bold, size_pt)
    if caps:
        text = text.upper()
    if f is None:
        return len(text) * size_pt * 0.55 * EMU_PT
    w = f.getlength(text) / 4.0  # font loaded at 4x size
    return (w + (spc / 100.0) * len(text)) * EMU_PT


def wrap_count(text, face, size_pt, width_emu, bold=False, spc=0, caps=False):
    lines = 0
    for para in text.split('\n'):
        words = para.split(' ')
        cur = ''
        n = 1
        for w in words:
            t = (cur + ' ' + w) if cur else w
            if text_width_emu(t, face, size_pt, bold, spc, caps) <= width_emu or not cur:
                cur = t
                if text_width_emu(cur, face, size_pt, bold, spc, caps) > width_emu * 1.001:
                    n += 0  # a single word wider than the box: counted as overflow by caller
            else:
                n += 1
                cur = w
        lines += n
    return lines


def longest_word_fits(text, face, size_pt, width_emu, bold=False, spc=0, caps=False):
    return all(text_width_emu(w, face, size_pt, bold, spc, caps) <= width_emu * 1.001 for w in re.split(r'\s+', text) if w)


def run_style(rpr):
    if rpr is None:
        return 'Arial', 18.0, False, 0, False
    lat = rpr.find(q('a:latin'))
    face = lat.get('typeface') if lat is not None else 'Arial'
    sz = int(rpr.get('sz', '1800')) / 100.0
    b = rpr.get('b') in ('1', 'true')
    spc = int(rpr.get('spc', '0'))
    caps = rpr.get('cap') == 'all'
    return face, sz, b, spc, caps


def box_width(shape):
    b = shape_box(shape)
    body = shape.find('.//' + q('p:txBody'))
    bp = body.find(q('a:bodyPr')) if body is not None else None
    l = int(bp.get('lIns', '91440')) if bp is not None else 91440
    r = int(bp.get('rIns', '91440')) if bp is not None else 91440
    if bp is not None and bp.get('wrap') == 'none':
        return 10 ** 9
    return (b[2] if b else 5000000) - l - r


def para_runs(p):
    return [r for r in p if r.tag in (q('a:r'), q('a:fld'))]


def para_text(p):
    """Paragraph text with explicit line breaks (a:br) as newlines."""
    out = []
    for e in p:
        if e.tag in (q('a:r'), q('a:fld')):
            t = e.find(q('a:t'))
            out.append(t.text or '' if t is not None else '')
        elif e.tag == q('a:br'):
            out.append('\n')
    return ''.join(out)


def current_lines(shape):
    body = shape.find('.//' + q('p:txBody'))
    w = box_width(shape)
    total = 0
    for p in body.findall(q('a:p')):
        runs = para_runs(p)
        txt = para_text(p)
        if not runs:
            total += 1
            continue
        face, sz, b, spc, caps = run_style(runs[0].find(q('a:rPr')))
        total += wrap_count(txt, face, sz, w, b, spc, caps) if txt else 1
    return total


def esc_keep(s):
    return s


def set_text(slide_x, key, paras, max_lines=None, min_scale=0.55, keep_size=False, color=None, bold=None,
             fit='auto', title_pt=None, trust_box=False):
    """Replace a shape's text. paras: str (\n = new paragraph) or list of str/dict{text, b, color}.
    Formatting of paragraph i comes from template paragraph min(i, n-1). Returns a fit report.
    fit: 'title' = one-paragraph headline, re-flowed by fit_title (balanced lines, size fitted to the
    slot); 'lines' = shrink until it takes no more lines than the template sample; 'auto' = 'title'
    when the sample text is at least title_pt points and the new text is one paragraph."""
    shape = find_shape(slide_x, key)
    if shape is None:
        return {'shape': key, 'error': 'not found'}
    body = shape.find('.//' + q('p:txBody'))
    if body is None:
        return {'shape': key, 'error': 'no text'}
    if isinstance(paras, str):
        paras = paras.split('\n')
    paras = [p if isinstance(p, dict) else {'text': p} for p in paras]
    tpl_ps = [p for p in body.findall(q('a:p'))]
    allowed = max_lines or max(1, current_lines(shape))
    slot = measure_slot(shape, allowed, trust_box)
    if fit == 'auto':
        fit = 'title' if (slot and title_pt and slot['size'] >= title_pt and len(paras) == 1) else 'lines'
    if fit == 'title':
        keep_size = True
    # template paragraphs that carry text define the styles
    styled = [p for p in tpl_ps if para_runs(p)] or tpl_ps
    for p in tpl_ps:
        body.remove(p)
    new_ps = []
    for i, item in enumerate(paras):
        src = styled[min(i, len(styled) - 1)]
        p = etree.SubElement(body, q('a:p'))
        ppr = src.find(q('a:pPr'))
        if ppr is not None:
            p.append(copy.deepcopy(ppr))
        runs = para_runs(src)
        rpr = copy.deepcopy(runs[0].find(q('a:rPr'))) if runs and runs[0].find(q('a:rPr')) is not None else etree.Element(q('a:rPr'))
        if item.get('b') is not None or bold is not None:
            rpr.set('b', '1' if (item.get('b') if item.get('b') is not None else bold) else '0')
        col = item.get('color') or color
        if col:
            for f in rpr.findall(q('a:solidFill')) + rpr.findall(q('a:gradFill')):
                rpr.remove(f)
            sf = etree.Element(q('a:solidFill'))
            etree.SubElement(sf, q('a:srgbClr')).set('val', col.lstrip('#').upper())
            ln = rpr.find(q('a:ln'))
            (ln.addnext(sf) if ln is not None else rpr.insert(0, sf))
        r = etree.SubElement(p, q('a:r'))
        r.append(rpr)
        t = etree.SubElement(r, q('a:t'))
        t.text = item['text']
        if item['text'] != item['text'].strip():
            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        end = src.find(q('a:endParaRPr'))
        if end is not None:
            p.append(copy.deepcopy(end))
        new_ps.append(p)
    # fit
    w = box_width(shape)
    rprs = [p.find(q('a:r') + '/' + q('a:rPr')) for p in new_ps]
    base = [int(r.get('sz', '1800')) for r in rprs]
    scale = 1.0
    if not keep_size:
        while True:
            lines = 0
            ok_words = True
            for p, r, b0 in zip(new_ps, rprs, base):
                face, sz, bb, spc, caps = run_style(r)
                sz = b0 / 100.0 * scale
                txt = p.find(q('a:r') + '/' + q('a:t')).text or ''
                lines += wrap_count(txt, face, sz, w, bb, spc, caps)
                ok_words &= longest_word_fits(txt, face, sz, w, bb, spc, caps)
            if (lines <= allowed and ok_words) or scale <= min_scale:
                break
            scale = round(scale - 0.03, 3)
        if scale < 1:
            for r, b0 in zip(rprs, base):
                r.set('sz', str(int(b0 * scale)))
            # line spacing given in points must follow the font size
            for p in new_ps:
                sp = p.find(q('a:pPr') + '/' + q('a:lnSpc') + '/' + q('a:spcPts'))
                if sp is not None:
                    sp.set('val', str(int(int(sp.get('val')) * scale)))
    if fit == 'title' and slot:
        from .pkg import shape_id
        return {'shape': key, 'title': True, 'id': shape_id(shape), 'slot': slot}
    final = current_lines(shape)
    rep = {'shape': key, 'lines': final, 'allowed': allowed, 'scale': scale}
    if final > allowed:
        rep['warning'] = 'text needs %d lines, template slot holds %d: shorten it' % (final, allowed)
    return rep


def clear_text(slide_x, key):
    shape = find_shape(slide_x, key)
    if shape is not None:
        shape.getparent().remove(shape)


def _para_info(shape):
    w = box_width(shape)
    out = []
    body = shape.find('.//' + q('p:txBody'))
    if body is None:
        return w, out
    for p in body.findall(q('a:p')):
        runs = para_runs(p)
        txt = para_text(p)
        if not runs or not txt.strip():
            continue
        face, sz, b, spc, caps = run_style(runs[0].find(q('a:rPr')))
        out.append((txt, face, sz, b, spc, caps))
    return w, out


def footprints(slide_x):
    """{shape_id: (single_line, max_width_emu, lines)} measured with the current fonts."""
    res = {}
    for sp in slide_x.iter(q('p:sp')):
        if sp.find('.//' + q('a:t')) is None:
            continue
        c = sp.find('.//' + q('p:cNvPr'))
        w, info = _para_info(sp)
        if not info:
            continue
        widths = [text_width_emu(ln, f, s, b, sp_, cp) for t, f, s, b, sp_, cp in info for ln in t.split('\n')]
        lines = sum(wrap_count(t, f, s, w, b, sp_, cp) for t, f, s, b, sp_, cp in info)
        res[c.get('id')] = (lines == len(info), max(widths), lines)
    return res


def keep_footprints(slide_x, before, tol=1.04, min_scale=0.5, skip=()):
    """After a font swap, shrink text so each shape keeps its old width (single-line texts such as
    numbers and labels) or its old line count (paragraphs). Shapes in skip (ids of fitted titles)
    are left to fit_title. Returns the shapes changed."""
    changed = []
    for sp in slide_x.iter(q('p:sp')):
        c = sp.find('.//' + q('p:cNvPr'))
        if c is None or c.get('id') not in before or c.get('id') in skip:
            continue
        single, old_w, old_lines = before[c.get('id')]
        rprs = [r for r in sp.iter(q('a:rPr')) if r.get('sz')] + [r for r in sp.iter(q('a:endParaRPr')) if r.get('sz')]
        if not rprs:
            continue
        base = [int(r.get('sz')) for r in rprs]
        scale = 1.0
        ok = True
        for _ in range(25):
            w, info = _para_info(sp)
            if not info:
                break
            if single:
                nw = max(text_width_emu(ln, f, s, b, sp_, cp) for t, f, s, b, sp_, cp in info for ln in t.split('\n'))
                ok = nw <= old_w * tol and nw <= w * 0.98
            else:
                ok = sum(wrap_count(t, f, s, w, b, sp_, cp) for t, f, s, b, sp_, cp in info) <= old_lines
            if ok or scale <= min_scale:
                break
            scale = round(scale - 0.04, 3)
            for r, b0 in zip(rprs, base):
                r.set('sz', str(int(b0 * scale)))
        if scale < 1:
            changed.append((c.get('name'), scale) if ok else (c.get('name'), scale, 'still too wide: shorten this text'))
    return changed


# ---------------------------------------------------------------- title fitting
TIGHT = 1.0   # line spacing (x single) for titles broken over several lines

def _line_factor(face, bold, lnspc):
    """Height of one line in points per point of font size. PowerPoint and LibreOffice set single
    spacing at 1.2 x the font size whatever the font (measured in LibreOffice on ten fonts)."""
    if lnspc and lnspc[0] == 'pct':
        return 1.2 * lnspc[1]
    return 1.2


def _lnspc(p):
    ls = p.find(q('a:pPr') + '/' + q('a:lnSpc')) if p is not None else None
    if ls is None:
        return None
    pct, pts = ls.find(q('a:spcPct')), ls.find(q('a:spcPts'))
    if pct is not None:
        return ('pct', int(pct.get('val')) / 100000.0)
    if pts is not None:
        return ('pts', int(pts.get('val')) / 100.0)
    return None


def _insets(shape):
    bp = shape.find('.//' + q('a:bodyPr'))
    g = lambda k, d: int(bp.get(k, d)) if bp is not None else d
    return g('lIns', 91440), g('tIns', 45720), g('rIns', 91440), g('bIns', 45720), (bp.get('anchor', 't') if bp is not None else 't')


def _first_style(shape):
    body = shape.find('.//' + q('p:txBody'))
    for p in body.findall(q('a:p')):
        runs = para_runs(p)
        if runs and para_text(p).strip():
            return p, run_style(runs[0].find(q('a:rPr')))
    return None, None


def measure_slot(shape, lines, trust_box=False):
    """The space the template's sample title takes: lines x line height, or the box if taller."""
    p, st = _first_style(shape)
    b = shape_box(shape)
    if st is None or b is None:
        return None
    face, sz, bold, spc, caps = st
    ls = _lnspc(p)
    lh = ls[1] if ls and ls[0] == 'pts' else sz * _line_factor(face, bold, ls)
    l, t, r, bi, anchor = _insets(shape)
    inner = max(0, b[3] - t - bi)
    block = lines * lh * EMU_PT
    bp = shape.find('.//' + q('a:bodyPr'))
    if trust_box:
        block = max(inner, lh * EMU_PT)
    elif bp is not None and bp.find(q('a:spAutoFit')) is not None and inner > 0.5 * lh * EMU_PT:
        # the box was sized to its text by the designer's app: trust it over our wrap count,
        # but never less than one full line as PowerPoint spaces it
        block = max(inner, lh * EMU_PT)
    return {'size': sz, 'lines': lines, 'block': int(block), 'inner_h': inner, 'top': b[1] + t, 'anchor': anchor}


def _ink_top(o, ob):
    """Where the first glyphs of a text shape really start: PowerPoint puts the extra line spacing
    above each line, so with 140% spacing the letters begin well below the box top."""
    if etree.QName(o).localname != 'sp' or o.find('.//' + q('p:txBody')) is None:
        return ob[1]
    p, st = _first_style(o)
    if st is None:
        return ob[1]
    face, sz, bold, spc, caps = st
    ls = _lnspc(p)
    lh = ls[1] if ls and ls[0] == 'pts' else sz * _line_factor(face, bold, ls)
    t = _insets(o)[1]
    return ob[1] + t + max(0.0, lh - sz) * EMU_PT


def _text_bottom(o, ob):
    """Bottom of a text shape's lines as PowerPoint lays them out (its box may be shorter)."""
    try:
        p, st = _first_style(o)
        if st is None:
            return ob[1] + ob[3]
        face, sz, bold, spc, caps = st
        ls = _lnspc(p)
        lh = ls[1] if ls and ls[0] == 'pts' else sz * _line_factor(face, bold, ls)
        return ob[1] + _insets(o)[1] + current_lines(o) * lh * EMU_PT
    except Exception:
        return ob[1] + ob[3]


def _limits(slide_x, shape, left, right, top, block, bottom, slide_size, gap):
    """Shrink the title's free region (left..right, top..bottom) so it does not run into other
    content: texts, pictures and charts in its right half narrow it, those below cut it short.
    Big pictures count only when they sit in front of the title. Small pictures placed over the
    template's sample title on purpose (stickers) are returned as overlays for the caller."""
    from .pkg import top_shapes, shape_name
    W, H = slide_size
    width = right - left
    overlays = []
    order = top_shapes(slide_x)
    me = next((i for i, o in enumerate(order) if o is shape or shape in o.iter()), -1)
    for i, o in enumerate(order):
        if i == me:
            continue
        ob = shape_box(o)
        if not ob:
            continue
        area = ob[2] * ob[3] / float(W * H)
        tag = etree.QName(o).localname
        has_text = bool(''.join(t.text or '' for t in o.iter(q('a:t'))).strip())
        if area > 0.85 or (area > 0.4 and i < me):
            continue      # backgrounds, and big art behind the title
        if tag in ('sp', 'cxnSp') and not has_text:
            continue      # lines, glows, frames: decoration
        ob_bottom = ob[1] + ob[3]
        if has_text and tag == 'sp':
            ob_bottom = max(ob_bottom, _text_bottom(o, ob))   # auto-fit boxes are often stale
        if not (ob[0] < right + gap and ob[0] + ob[2] > left - gap and ob[1] < bottom and ob_bottom > top - 2 * gap):
            continue
        ink = _ink_top(o, ob) if has_text else ob[1]
        if ob[0] >= left + 0.5 * width:
            right = min(right, ob[0] - gap)
        elif ink > top + gap and (has_text or ob[1] >= top + block - gap):
            bottom = min(bottom, ink - gap)    # content below, or a second title line
        elif not has_text and area < 0.05 and ob[2] * ob[3] < 0.35 * width * block:
            overlays.append(shape_name(o))   # a small sticker placed over the sample title
    return right, max(bottom, top + 1), overlays


def _balanced(words, n, width):
    """Split words into n lines with the smallest widest line (all break positions are tried)."""
    import itertools
    k = len(words)
    if n >= k:
        return [[w] for w in words], max(width(w) for w in words)
    best = None
    for cuts in itertools.combinations(range(1, k), n - 1):
        idx = (0,) + cuts + (k,)
        lines = [words[idx[i]:idx[i + 1]] for i in range(n)]
        ws = [width(' '.join(x)) for x in lines]
        # widest line first, then evenness, then a slightly shorter last line reads better
        key = (round(max(ws), -3), sum((max(ws) - w) ** 2 for w in ws), -ws[-1])
        if best is None or key < best[0]:
            best = (key, lines, max(ws))
    return best[1], best[2]


def fit_title(slide_x, key, slot, slide_size, max_lines=4, grow=True, min_ratio=0.45):
    """Re-flow a headline so it fills its slot: try 1..max_lines balanced lines, size each option by
    the box width and the slot height (never larger than the template size), keep the biggest, and
    prefer fewer lines when sizes are close. With grow, a top-anchored title may also use free space
    below its box (up to 1.8x the sample block), so a long title gets an extra line instead of tiny
    type. Explicit line breaks keep it from re-wrapping in PowerPoint or LibreOffice."""
    from .pkg import set_box
    shape = find_shape(slide_x, key)
    if shape is None or not slot:
        return {'shape': key, 'error': 'not found'}
    body = shape.find('.//' + q('p:txBody'))
    ps = [p for p in body.findall(q('a:p')) if para_runs(p)]
    if len(ps) != 1:
        return {'shape': key, 'skipped': 'not a one-paragraph title'}
    p = ps[0]
    run0 = para_runs(p)[0]
    rpr0 = run0.find(q('a:rPr'))
    face, _sz_now, bold, spc, caps = run_style(rpr0)
    s0 = slot['size']
    text = ' '.join(re.split(r'[ \t\n\r]+', para_text(p).strip()))   # keeps non-breaking spaces (word groups)
    words = text.split(' ')
    b = shape_box(shape)
    l, t, r, bi, anchor = _insets(shape)
    bp = body.find(q('a:bodyPr'))
    W, H = slide_size
    ls = _lnspc(p)
    factor = _line_factor(face, bold, ls)
    in_group = etree.QName(shape.getparent()).localname == 'grpSp'
    xf = shape.find(q('p:spPr') + '/' + q('a:xfrm'))
    rotated = xf is not None and int(xf.get('rot', '0')) != 0
    left = b[0] + l
    right = b[0] + b[2] - r
    top = b[1] + t
    block = slot['block']
    room = block
    overlays = []
    free = not in_group and not rotated
    if free:
        right = min(right, W * 0.97)           # some template boxes run past the slide edge
        bottom = top + (1.8 * block if grow and anchor == 't' else block)
        right, bottom, overlays = _limits(slide_x, shape, left, right, top, block, min(bottom, H * 0.95), slide_size, 0.12 * s0 * EMU_PT)
        room = bottom - top if anchor == 't' else min(block, bottom - top)
        ppr0 = p.find(q('a:pPr'))
        cut = (b[0] + b[2] - r) - right
        if cut > 0 and ppr0 is not None and ppr0.get('algn') == 'ctr' and cut < 0.3 * (right - left):
            left += cut          # centred titles stay centred: trim both sides alike
    width = right - left

    loose = (ls[1] / s0 > 1.2) if ls and ls[0] == 'pts' else factor > 1.2 * TIGHT

    def line_h(sz, n=1):
        # a title stacked over several lines reads as one block: airy single-line spacing
        # (often 120-150% in templates) is tightened to TIGHT x single
        if n > 1 and loose:
            return sz * 1.2 * TIGHT * EMU_PT
        return (ls[1] * sz / s0 if ls and ls[0] == 'pts' else sz * factor) * EMU_PT

    options = []
    for n in range(1, min(max_lines, len(words)) + 1):
        lines, wmax = _balanced(words, n, lambda x: text_width_emu(x, face, s0, bold, spc, caps))
        sz = min(s0, s0 * width * 0.97 / max(wmax, 1), room / (n * line_h(1.0, n)))
        sz = max(sz, 1.0)
        # spacing (spc) does not scale with size: step down until every line really fits
        for _ in range(40):
            if all(text_width_emu(' '.join(x), face, sz, bold, spc, caps) <= width * 0.985 for x in lines):
                break
            sz *= 0.98
        options.append((sz, n, lines))
    best_sz = max(o[0] for o in options)
    sz, n, lines = next(o for o in options if o[0] >= best_sz * 0.93)
    sz = int(sz * 100) / 100.0
    # rebuild the paragraph: run, br, run ... with the template run formatting
    ppr = p.find(q('a:pPr'))
    end = p.find(q('a:endParaRPr'))
    for e in list(p):
        if e is not ppr and e is not end:
            p.remove(e)
    insert_at = 1 if ppr is not None else 0
    for i, ln in enumerate(lines):
        if i:
            br = etree.Element(q('a:br'))
            br.append(copy.deepcopy(rpr0))
            p.insert(insert_at, br)
            insert_at += 1
        rr = etree.Element(q('a:r'))
        rr.append(copy.deepcopy(rpr0))
        tt = etree.SubElement(rr, q('a:t'))
        tt.text = ' '.join(ln)
        p.insert(insert_at, rr)
        insert_at += 1
    for e in p.iter(q('a:rPr'), q('a:endParaRPr')):
        e.set('sz', str(int(sz * 100)))
    if n > 1 and loose:
        ppr = p.find(q('a:pPr'))
        if ppr is None:
            ppr = etree.Element(q('a:pPr'))
            p.insert(0, ppr)
        old_ls = ppr.find(q('a:lnSpc'))
        if old_ls is not None:
            ppr.remove(old_ls)
        new_ls = etree.Element(q('a:lnSpc'))
        etree.SubElement(new_ls, q('a:spcPct')).set('val', str(int(TIGHT * 100000)))
        ppr.insert(0, new_ls)
    elif ls and ls[0] == 'pts':
        p.find(q('a:pPr') + '/' + q('a:lnSpc') + '/' + q('a:spcPts')).set('val', str(int(ls[1] * sz / s0 * 100)))
    na = bp.find(q('a:normAutofit')) if bp is not None else None
    if na is not None:
        for k in ('fontScale', 'lnSpcReduction'):
            na.attrib.pop(k, None)
    need = n * line_h(sz, n) + t + bi
    nb = list(b)
    if free and right < b[0] + b[2] - r - 1:
        nb[0] = int(left - l)              # narrowed: centred or right-aligned text must move too
        nb[2] = int(right + r - nb[0])
    if need > b[3] and free and anchor == 't':
        nb[3] = int(need)
    if nb != b:
        set_box(shape, nb)
    rep = {'shape': key, 'lines': n, 'size_pt': sz, 'template_pt': s0, 'scale': round(sz / s0, 3)}
    if overlays:
        rep['overlaps'] = overlays
    if sz < s0 * min_ratio:
        rep['warning'] = 'title fitted at %d%% of the template size: a shorter title would look better' % round(100 * sz / s0)
    return rep


def set_size(slide_x, key, size_pt):
    """Set every run of a shape to one size (used to give split title lines the same size)."""
    shape = find_shape(slide_x, key)
    if shape is None:
        return
    for e in shape.iter(q('a:rPr'), q('a:endParaRPr')):
        old = int(e.get('sz', '0'))
        e.set('sz', str(int(size_pt * 100)))
    for sp in shape.iter(q('a:spcPts')):
        if sp.getparent().tag == q('a:lnSpc') and old:
            sp.set('val', str(int(int(sp.get('val')) * size_pt * 100 / old)))


# ---------- typography: keep word groups together, French spacing ----------
NB = ' '
_GROUP = re.compile(r'(?i)\b(sprint|phase|step|stage|part|chapter|week|day|level|version|release|module|task|lot|figure|fig\.|table|slide|section|'
                    r'article|art\.|n°|no\.|étape|partie|chapitre|semaine|jour|niveau|tâche|tableau|annexe|appendix|v)[ ]+(\d+[a-z]?)\b')
_PERIOD = re.compile(r'\b([QHST][1-4])[ ]+(20\d\d)\b')
_UNIT = re.compile(r'(\d)[ ]+(%|‰|°C|°F|°|[µnm]?s|min|h|[kMGT]?B|[kMG]?b(?:ps|it/s)?|[kMGT]?Hz|[kMG]?Wh?|[km]?V|m?A|dB[mi]?|[kcmn]?m|kg|g|€|\$|DT|TND|USD|EUR|px|pt|x)(?=[\s,.;:!?)/]|$)')
_MONTH = re.compile(r'(?i)\b(\d{1,2})[ ]+(jan(?:uary|v\.?|vier)?|feb(?:ruary)?|févr?\.?|février|mar(?:ch|s)?|apr(?:il)?|avr\.?|avril|may|mai|'
                    r'june?|juin|july?|juil\.?|juillet|aug(?:ust)?|août|sep(?:t\.?|tember|tembre)?|oct(?:ober|obre|\.)?|nov(?:ember|embre|\.)?|'
                    r'dec(?:ember)?|déc\.?|décembre)\b')
_FR_PUNCT = re.compile(r'(?<=[\w%)\]»"’])[   ]?([?!;:])(?=\s|$|[?!])')
_FR_THOUSANDS = re.compile(r'(?<=\d)[ ](?=\d{3}\b)')


def typography(s, lang='en'):
    """Non-breaking spaces inside word groups that must stay on one line ("Sprint 1", "10 Aug",
    "5 GHz", "Q3 2026") and, for French, before ? ! ; : and inside « » (typographie française)."""
    if not isinstance(s, str) or not s.strip():
        return s
    s = _GROUP.sub(lambda m: m.group(1) + NB + m.group(2), s)
    s = _PERIOD.sub(lambda m: m.group(1) + NB + m.group(2), s)
    s = _UNIT.sub(lambda m: m.group(1) + NB + m.group(2), s)
    s = _MONTH.sub(lambda m: m.group(1) + NB + m.group(2), s)
    if (lang or 'en').lower().startswith('fr') and '://' not in s:
        s = _FR_PUNCT.sub(lambda m: NB + m.group(1), s)
        s = re.sub(r'«[  ]?', '«' + NB, s)
        s = re.sub(r'[  ]?»', NB + '»', s)
        s = _FR_THOUSANDS.sub(NB, s)
    return s


def typography_obj(obj, lang='en', skip=('src', 'merge', 'fit', 'keep', 'shapes', 'path', 'screenshot', 'cutout', 'icon', 'files', 'url', 'filename', 'number_format', 'kind', 'lang', 'name', 'kit')):
    """typography() on every string of a spec value (text slots, kit items), leaving code, paths and options alone."""
    if isinstance(obj, str):
        return typography(obj, lang)
    if isinstance(obj, list):
        return [typography_obj(v, lang, skip) for v in obj]
    if isinstance(obj, dict):
        return {k: (v if k in skip else typography_obj(v, lang, skip)) for k, v in obj.items()}
    return obj
