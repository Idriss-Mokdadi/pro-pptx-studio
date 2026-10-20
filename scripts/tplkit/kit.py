"""Kit components drawn on top of template slides with python-pptx (MIT License).

Every component takes a box (fractions of the slide, [x, y, w, h], or EMU when any value > 1)
and a theme derived from the template (fonts, colors), so generated parts look like the
designer's own. Components: chart, kpi, table, code, bullets, text, image (with glow),
depth (cut-out object in front of the title), mockup (phone / laptop / browser), timeline,
icons, credit."""
import io, math, os, re
from lxml import etree
from PIL import Image, ImageDraw, ImageFilter
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt as _Pt

SCALE = 1.0  # set to slide_width / 12192000 so sizes are relative to a 13.33in slide


def Pt(v):
    return _Pt(v * SCALE)

ACOL = qn('a:srgbClr')


def rgb(h):
    h = h.lstrip('#')
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def mix(h1, h2, t):
    a = [int(h1.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(h2.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    return '%02X%02X%02X' % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


class Theme:
    def __init__(self, display='Inter', body='Inter', mono='JetBrains Mono', text='FFFFFF', muted='A9B4C8',
                 accent='2D8CFF', accent2='04DAFF', surface='FFFFFF', surface_alpha=8, border_alpha=22, dark=True,
                 display_bold=False, radius=0.12):
        self.display, self.body, self.mono = display, body, mono
        self.text, self.muted, self.accent, self.accent2 = text, muted, accent, accent2
        self.surface, self.surface_alpha, self.border_alpha, self.dark = surface, surface_alpha, border_alpha, dark
        self.display_bold, self.radius = display_bold, radius

    @classmethod
    def from_dict(cls, d):
        t = cls()
        for k, v in (d or {}).items():
            setattr(t, k, v.lstrip('#') if isinstance(v, str) and re.match(r'^#?[0-9A-Fa-f]{6}$', v) else v)
        return t


def box_emu(prs, box):
    W, H = prs.slide_width, prs.slide_height
    if all(0 <= v <= 1.0001 for v in box):
        return [int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)]
    return [int(v) for v in box]


def set_alpha(fill_fore_color_el_parent, alpha_pct):
    pass


def solid(shape_fill, hexcol, alpha=None):
    shape_fill.solid()
    shape_fill.fore_color.rgb = rgb(hexcol)
    if alpha is not None:
        clr = shape_fill._xPr.find(qn('a:solidFill')).find(ACOL)
        for a in clr.findall(qn('a:alpha')):
            clr.remove(a)
        e = etree.SubElement(clr, qn('a:alpha'))
        e.set('val', str(int(alpha * 1000)))


def line(shape, hexcol=None, width_pt=1.0, alpha=None):
    if hexcol is None:
        shape.line.fill.background()
        return
    shape.line.color.rgb = rgb(hexcol)
    shape.line.width = Pt(width_pt)
    if alpha is not None:
        ln = shape.line._get_or_add_ln()
        clr = ln.find(qn('a:solidFill')).find(ACOL)
        e = etree.SubElement(clr, qn('a:alpha'))
        e.set('val', str(int(alpha * 1000)))


def panel(slide, th, x, y, w, h, name=None, alpha=None, border=True, radius=None, fill=None):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(x), Emu(y), Emu(w), Emu(h))
    r = th.radius if radius is None else radius
    s.adjustments[0] = max(0.0, min(0.5, r * min(w, h) / min(w, h) if r < 0.5 else 0.5)) if r else 0.0
    solid(s.fill, fill or th.surface, th.surface_alpha if alpha is None else alpha)
    if border:
        line(s, th.accent if fill else th.surface, 1.0, th.border_alpha)
    else:
        line(s, None)
    s.shadow.inherit = False
    if name:
        s.name = name
    return s


def textbox(slide, x, y, w, h, paras, font, size, color, bold=False, align='l', anchor='t', name=None,
            spacing=1.1, italic=False, autoshrink=True, caps=False):
    tb = slide.shapes.add_textbox(Emu(x), Emu(y), Emu(w), Emu(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {'t': MSO_ANCHOR.TOP, 'm': MSO_ANCHOR.MIDDLE, 'b': MSO_ANCHOR.BOTTOM}[anchor]
    if isinstance(paras, str):
        paras = [paras]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = {'l': PP_ALIGN.LEFT, 'c': PP_ALIGN.CENTER, 'r': PP_ALIGN.RIGHT}[align]
        para.line_spacing = spacing
        runs = p if isinstance(p, list) else [p]
        for rr in runs:
            if isinstance(rr, dict):
                t, c, b, f, s_ = rr['text'], rr.get('color', color), rr.get('b', bold), rr.get('font', font), rr.get('size', size)
            else:
                t, c, b, f, s_ = rr, color, bold, font, size
            r = para.add_run()
            r.text = t.upper() if caps else t
            r.font.name = f
            r.font.size = Pt(s_)
            r.font.bold = b
            r.font.italic = italic
            r.font.color.rgb = rgb(c)
    if name:
        tb.name = name
    if autoshrink:
        fit_textbox(tb, w, h, font, size, paras)
    return tb


def fit_textbox(tb, w, h, font, size, paras):
    """Shrink font until the measured text fits the box height."""
    try:
        from .text import wrap_count
    except Exception:
        return
    flat = []
    for p in paras:
        runs = p if isinstance(p, list) else [p]
        flat.append(''.join(r['text'] if isinstance(r, dict) else r for r in runs))
    s = size
    while s > size * 0.55:
        lines = sum(wrap_count(t or ' ', font, s * SCALE, w) for t in flat)
        if lines * s * SCALE * 1.25 * 12700 <= h:
            break
        s -= max(0.5, size * 0.04)
    if s < size:
        for para in tb.text_frame.paragraphs:
            for r in para.runs:
                if r.font.size:
                    r.font.size = _Pt(max(8, r.font.size.pt * s / size))


# ---------------------------------------------------------------------------
def kpi(prs, slide, th, box, items, name='kpi', style='panel'):
    """items: [{value, label, note?, highlight?}] in a row of tiles."""
    x, y, w, h = box_emu(prs, box)
    n = len(items)
    gap = int(w * 0.03)
    tw = (w - gap * (n - 1)) // n
    names = []
    for i, it in enumerate(items):
        tx = x + i * (tw + gap)
        hl = it.get('highlight')
        if style == 'panel':
            panel(slide, th, tx, y, tw, h, name='%s-tile-%d' % (name, i + 1), alpha=(th.surface_alpha * 2 if hl else None),
                  fill=th.accent if hl else None)
        pad = int(tw * 0.08)
        vs = min(72, max(28, h / 12700 * 0.36 / SCALE))
        textbox(slide, tx + pad, y + int(h * 0.12), tw - 2 * pad, int(h * 0.42), it['value'], th.display, vs,
                th.accent2 if hl else th.accent, bold=th.display_bold, name='%s-value-%d' % (name, i + 1))
        lab = [it['label']] + ([{'text': it['note'], 'color': th.muted, 'size': max(11, vs * 0.26)}] if it.get('note') else [])
        textbox(slide, tx + pad, y + int(h * 0.56), tw - 2 * pad, int(h * 0.38), [it['label']] + ([[{'text': it['note'], 'color': th.muted, 'size': max(11, vs * 0.26)}]] if it.get('note') else []),
                th.body, max(12, vs * 0.32), th.text, bold=True, name='%s-label-%d' % (name, i + 1))
        names += ['%s-tile-%d' % (name, i + 1)] if style == 'panel' else []
    return names


def chart(prs, slide, th, box, kind='column', categories=(), series=(), highlight=None, number_format='General',
          labels=True, legend=None, name='chart', title=None, unit=''):
    x, y, w, h = box_emu(prs, box)
    ct = {'column': XL_CHART_TYPE.COLUMN_CLUSTERED, 'bar': XL_CHART_TYPE.BAR_CLUSTERED, 'line': XL_CHART_TYPE.LINE_MARKERS,
          'area': XL_CHART_TYPE.AREA, 'donut': XL_CHART_TYPE.DOUGHNUT, 'pie': XL_CHART_TYPE.PIE,
          'stacked': XL_CHART_TYPE.COLUMN_STACKED}[kind]
    cd = CategoryChartData()
    cd.categories = list(categories)
    for s in series:
        cd.add_series(s['name'], list(s['values']), number_format=number_format)
    gf = slide.shapes.add_chart(ct, Emu(x), Emu(y), Emu(w), Emu(h), cd)
    gf.name = name
    ch = gf.chart
    ch.font.name = th.body
    ch.font.size = Pt(12)
    ch.font.color.rgb = rgb(th.muted)
    ch.has_title = bool(title)
    if title:
        ch.chart_title.text_frame.text = title
    multi = len(series) > 1
    ch.has_legend = bool(legend if legend is not None else (multi or kind in ('donut', 'pie')))
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.BOTTOM
        ch.legend.include_in_layout = False
        ch.legend.font.color.rgb = rgb(th.text)
        ch.legend.font.size = Pt(12)
    pal = [th.accent, th.accent2, mix(th.accent, th.text, 0.45), mix(th.accent2, th.text, 0.5), mix(th.accent, '000000', 0.35), mix(th.accent2, '000000', 0.35)]
    plot = ch.plots[0]
    if kind in ('donut', 'pie'):
        pts = plot.series[0].points
        for i in range(len(categories)):
            solid(pts[i].format.fill, pal[i % len(pal)])
            pts[i].format.line.fill.background()
        if kind == 'donut':
            hole = ch._chartSpace.find('.//' + qn('c:holeSize'))
            if hole is not None:
                hole.set('val', '62')
    else:
        for i, s in enumerate(plot.series):
            col = pal[i % len(pal)] if multi else mix(th.accent, th.text, 0.55) if highlight is not None else th.accent
            if kind in ('line',):
                s.format.line.color.rgb = rgb(pal[i % len(pal)])
                s.format.line.width = Pt(3)
                s.smooth = True
            else:
                solid(s.format.fill, col)
                s.format.line.fill.background()
            if highlight is not None and not multi and kind != 'line':
                solid(s.points[highlight].format.fill, th.accent)
        if kind in ('column', 'bar', 'stacked'):
            plot.gap_width = 70
            if multi:
                plot.overlap = -10 if kind != 'stacked' else 100
        va, ca = ch.value_axis, ch.category_axis
        va.has_major_gridlines = True
        va.major_gridlines.format.line.color.rgb = rgb(th.muted)
        va.major_gridlines.format.line.width = Pt(0.5)
        gl = va.major_gridlines.format.line._get_or_add_ln().find(qn('a:solidFill')).find(ACOL)
        etree.SubElement(gl, qn('a:alpha')).set('val', '25000')
        va.format.line.fill.background()
        va.tick_labels.font.color.rgb = rgb(th.muted)
        va.tick_labels.font.size = Pt(11)
        ca.format.line.color.rgb = rgb(th.muted)
        ca.tick_labels.font.color.rgb = rgb(th.text)
        ca.tick_labels.font.size = Pt(12)
    if labels:
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.font.size = Pt(13)
        dl.font.bold = True
        dl.font.color.rgb = rgb(th.text)
        dl.number_format = number_format + (('"' + unit + '"') if unit and number_format == 'General' else '')
        dl.number_format_is_linked = False
        if kind in ('column', 'bar'):
            dl.position = XL_LABEL_POSITION.OUTSIDE_END
        if kind in ('donut', 'pie'):
            dl.show_percentage = number_format == 'percent'
    return gf


def table(prs, slide, th, box, rows, header=True, name='table', col_widths=None, highlight_row=None):
    x, y, w, h = box_emu(prs, box)
    nr, nc = len(rows), max(len(r) for r in rows)
    gf = slide.shapes.add_table(nr, nc, Emu(x), Emu(y), Emu(w), Emu(h))
    gf.name = name
    tbl = gf.table
    tblpr = gf._element.find('.//' + qn('a:tblPr'))
    for k in ('firstRow', 'bandRow'):
        tblpr.set(k, '0')
    sid = tblpr.find(qn('a:tableStyleId'))
    if sid is not None:
        sid.text = '{2D5ABB26-0587-4C30-8999-92F81FD0307C}'  # "No Style, No Grid"
    if col_widths:
        tot = sum(col_widths)
        for i, cw in enumerate(col_widths):
            tbl.columns[i].width = Emu(int(w * cw / tot))
    rh = h // nr
    for r in range(nr):
        tbl.rows[r].height = Emu(rh)
        for c in range(nc):
            cell = tbl.cell(r, c)
            txt = rows[r][c] if c < len(rows[r]) else ''
            is_h = header and r == 0
            hl = highlight_row is not None and r == highlight_row
            if is_h:
                solid(cell.fill, th.accent)
            elif hl:
                solid(cell.fill, th.accent, 22)
            else:
                solid(cell.fill, th.surface, th.surface_alpha if r % 2 else max(2, th.surface_alpha // 2))
            cell.margin_left = cell.margin_right = Emu(int(w * 0.012))
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.text = ''
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = str(txt)
            run.font.name = th.display if is_h else th.body
            run.font.size = Pt(14 if is_h else 13)
            run.font.bold = is_h or hl or c == 0
            run.font.color.rgb = rgb('FFFFFF' if is_h else th.text)
    return gf


KW = {
    'python': r'\b(?:def|class|return|if|elif|else|for|while|in|import|from|as|with|try|except|finally|raise|lambda|yield|not|and|or|is|None|True|False|async|await|pass|break|continue)\b',
    'js': r'\b(?:function|const|let|var|return|if|else|for|while|import|from|export|class|new|async|await|try|catch|throw|null|true|false|this)\b',
    'c': r'\b(?:int|void|char|float|double|return|if|else|for|while|struct|include|define|static|const|unsigned|uint8_t|uint16_t|uint32_t|bool|true|false)\b',
}


def code(prs, slide, th, box, src, lang='python', filename='main.py', highlight=(), name='code', font=None, size=None):
    x, y, w, h = box_emu(prs, box)
    win = panel(slide, th, x, y, w, h, name=name + '-window', alpha=th.surface_alpha + 6 if th.dark else 85, fill=('0B0F17' if th.dark else 'FFFFFF'))
    bar_h = int(h * 0.09)
    for i, c in enumerate(('FF5F57', 'FEBC2E', '28C840')):
        d = slide.shapes.add_shape(MSO_SHAPE.OVAL, Emu(x + int(bar_h * (0.45 + i * 0.6))), Emu(y + int(bar_h * 0.33)), Emu(int(bar_h * 0.34)), Emu(int(bar_h * 0.34)))
        solid(d.fill, c)
        line(d, None)
    mono = font or th.mono
    textbox(slide, x + int(bar_h * 2.4), y + int(bar_h * 0.22), w - int(bar_h * 3), int(bar_h * 0.6), filename, mono, 12, th.muted, name=name + '-file', autoshrink=False)
    lines = src.split('\n')
    longest = max(len(l) for l in lines) or 1
    pad = int(w * 0.04)
    avail_w, avail_h = w - 2 * pad, h - bar_h - 2 * pad
    sz = size or min(24, avail_w / 12700 / (longest * 0.62) / SCALE, avail_h / 12700 / (len(lines) * 1.45) / SCALE)
    kw = re.compile(KW.get(lang, KW['python']))
    paras = []
    for i, l in enumerate(lines, 1):
        runs = []
        hl = i in highlight
        toks = re.split(r'(#.*$|//.*$|"[^"]*"|\'[^\']*\'|\b\d+\b|' + KW.get(lang, KW['python']) + r')', l)
        for t in toks:
            if not t:
                continue
            if t.startswith('#') or t.startswith('//'):
                c = th.muted
            elif t[0] in '"\'':
                c = 'F2C46D'
            elif re.fullmatch(r'\d+', t):
                c = 'F78C6C'
            elif kw.fullmatch(t):
                c = th.accent2
            else:
                c = 'E6EDF3' if th.dark else '1F2328'
            runs.append({'text': t, 'color': c, 'b': hl})
        paras.append(runs or [{'text': ' ', 'color': th.text}])
    # highlighted lines get a band behind them
    line_pt = sz * 1.32
    lh = line_pt * SCALE * 12700
    for i in highlight:
        band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(x + int(pad * 0.5)), Emu(int(y + bar_h + pad + (i - 1) * lh - lh * 0.12)), Emu(w - pad), Emu(int(lh)))
        solid(band.fill, th.accent, 22)
        line(band, None)
        band.name = '%s-hl-%d' % (name, i)
    textbox(slide, x + pad, y + bar_h + pad, avail_w, avail_h, paras, mono, sz, th.text, name=name + '-text', spacing=Pt(line_pt), autoshrink=False)
    return win


def bullets(prs, slide, th, box, items, name='bullets', size=20, marker='accent-bar', numbered=False):
    """items: [str | {head, text}] stacked vertically, each with a small accent marker."""
    x, y, w, h = box_emu(prs, box)
    n = len(items)
    gap = int(h * 0.05)
    ih = (h - gap * (n - 1)) // n
    for i, it in enumerate(items):
        iy = y + i * (ih + gap)
        head = it.get('head') if isinstance(it, dict) else None
        text = it.get('text') if isinstance(it, dict) else it
        mw = int(min(ih * 0.5, w * 0.06))
        if numbered:
            textbox(slide, x, iy, int(mw * 1.6), ih, '%02d' % (i + 1), th.display, size * 1.3, th.accent, bold=th.display_bold, name='%s-num-%d' % (name, i + 1), autoshrink=False)
            tx = x + int(mw * 1.9)
        else:
            m = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(x), Emu(iy + int(ih * 0.12)), Emu(int(mw * 0.18)), Emu(int(ih * 0.7)))
            solid(m.fill, th.accent)
            line(m, None)
            m.name = '%s-mark-%d' % (name, i + 1)
            tx = x + int(mw * 0.6)
        paras = ([[{'text': head, 'b': True, 'color': th.text, 'font': th.display if th.display_bold else th.body}]] if head else []) + ([[{'text': text, 'color': th.muted if head else th.text}]] if text else [])
        textbox(slide, tx, iy, x + w - tx, ih, paras, th.body, size, th.text, name='%s-item-%d' % (name, i + 1), anchor='m')


def text(prs, slide, th, box, paras, role='body', name='text', align='l', size=None, color=None, anchor='t'):
    x, y, w, h = box_emu(prs, box)
    font = th.display if role in ('title', 'display') else th.mono if role == 'mono' else th.body
    sz = size or {'title': 44, 'display': 80, 'body': 18, 'label': 14, 'mono': 16}.get(role, 18)
    col = color or (th.text if role != 'label' else th.muted)
    return textbox(slide, x, y, w, h, paras, font, sz, col, bold=(role in ('title', 'display') and th.display_bold), align=align, name=name, anchor=anchor)


def glow_png(path, hexcol, size=900, strength=0.75):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (0, 2, 4))
    d.ellipse([size * 0.2, size * 0.2, size * 0.8, size * 0.8], fill=(r, g, b, int(255 * strength)))
    im = im.filter(ImageFilter.GaussianBlur(size * 0.12))
    im.save(path)
    return path


def rounded_png(src, dst, radius_frac=0.08, w=None, h=None):
    im = Image.open(src).convert('RGBA')
    if w and h:
        ar = w / h
        iw, ih = im.size
        if iw / ih > ar:
            nw = int(ih * ar); im = im.crop(((iw - nw) // 2, 0, (iw - nw) // 2 + nw, ih))
        else:
            nh = int(iw / ar); im = im.crop((0, (ih - nh) // 2, iw, (ih - nh) // 2 + nh))
    m = Image.new('L', im.size, 0)
    rr = int(min(im.size) * radius_frac)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], rr, fill=255)
    im.putalpha(m)
    im.save(dst)
    return dst


def image(prs, slide, th, box, path, name='image', rounded=0.06, glow=False, tmpdir='/tmp', fit='cover'):
    x, y, w, h = box_emu(prs, box)
    if glow:
        gp = glow_png(os.path.join(tmpdir, '%s-glow.png' % name), th.accent)
        gw, gh = int(w * 1.7), int(h * 1.7)
        g = slide.shapes.add_picture(gp, Emu(x - (gw - w) // 2), Emu(y - (gh - h) // 2), Emu(gw), Emu(gh))
        g.name = name + '-glow'
    if fit == 'contain':
        im = Image.open(path)
        ar = im.width / im.height
        if w / h > ar:
            nw = int(h * ar); x += (w - nw) // 2; w = nw
        else:
            nh = int(w / ar); y += (h - nh) // 2; h = nh
        p = path
        if rounded:
            p = rounded_png(path, os.path.join(tmpdir, '%s-r.png' % name), rounded)
    else:
        p = rounded_png(path, os.path.join(tmpdir, '%s-r.png' % name), rounded, w, h) if rounded else path
    pic = slide.shapes.add_picture(p, Emu(x), Emu(y), Emu(w), Emu(h))
    pic.name = name
    return pic


def depth(prs, slide, th, box, cutout, name='depth', glow=True, tmpdir='/tmp', shadow=True):
    """Place a transparent PNG object so it overlaps the title (added after the title, so it sits in
    front of the letters). Use a PNG with a real alpha channel."""
    x, y, w, h = box_emu(prs, box)
    im = Image.open(cutout)
    ar = im.width / im.height
    if w / h > ar:
        nw = int(h * ar); x += (w - nw) // 2; w = nw
    else:
        nh = int(w / ar); y += (h - nh); h = nh
    if glow:
        gp = glow_png(os.path.join(tmpdir, '%s-glow.png' % name), th.accent, strength=0.55)
        gw, gh = int(w * 1.5), int(h * 1.2)
        g = slide.shapes.add_picture(gp, Emu(x - (gw - w) // 2), Emu(y - (gh - h) // 3), Emu(gw), Emu(gh))
        g.name = name + '-glow'
    if shadow:
        sp = os.path.join(tmpdir, '%s-shadow.png' % name)
        sh = Image.new('RGBA', (600, 120), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([60, 30, 540, 90], fill=(0, 0, 0, 150))
        sh.filter(ImageFilter.GaussianBlur(18)).save(sp)
        s = slide.shapes.add_picture(sp, Emu(x + int(w * 0.1)), Emu(y + h - int(h * 0.08)), Emu(int(w * 0.8)), Emu(int(h * 0.16)))
        s.name = name + '-shadow'
    pic = slide.shapes.add_picture(cutout, Emu(x), Emu(y), Emu(w), Emu(h))
    pic.name = name
    return pic


def mockup(prs, slide, th, box, screenshot, device='laptop', name='mockup', tmpdir='/tmp', glow=True):
    x, y, w, h = box_emu(prs, box)
    if glow:
        gp = glow_png(os.path.join(tmpdir, '%s-glow.png' % name), th.accent, strength=0.5)
        g = slide.shapes.add_picture(gp, Emu(x - w // 4), Emu(y - h // 4), Emu(int(w * 1.5)), Emu(int(h * 1.5)))
        g.name = name + '-glow'
    bez = '1B1F27'
    if device == 'phone':
        ph_w = min(w, int(h * 0.49))
        px = x + (w - ph_w) // 2
        body = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(px), Emu(y), Emu(ph_w), Emu(h))
        body.adjustments[0] = 0.14
        solid(body.fill, bez); line(body, '3A4150', 1.5)
        body.name = name + '-body'
        m = int(ph_w * 0.045)
        image(prs, slide, th, [px + m, y + m, ph_w - 2 * m, h - 2 * m], screenshot, name=name + '-screen', rounded=0.1, tmpdir=tmpdir)
        notch = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(px + ph_w * 3 // 8), Emu(y + int(m * 1.6)), Emu(ph_w // 4), Emu(int(m * 1.1)))
        notch.adjustments[0] = 0.5; solid(notch.fill, '000000'); line(notch, None)
        return body
    if device == 'browser':
        win = panel(slide, th, x, y, w, h, name=name + '-body', alpha=100, fill='F4F6FA' if not th.dark else '161B26', radius=0.03)
        bh = int(h * 0.07)
        for i, c in enumerate(('FF5F57', 'FEBC2E', '28C840')):
            d = slide.shapes.add_shape(MSO_SHAPE.OVAL, Emu(x + int(bh * (0.5 + i * 0.6))), Emu(y + int(bh * 0.32)), Emu(int(bh * 0.36)), Emu(int(bh * 0.36)))
            solid(d.fill, c); line(d, None)
        image(prs, slide, th, [x + int(w * 0.01), y + bh, w - int(w * 0.02), h - bh - int(w * 0.01)], screenshot, name=name + '-screen', rounded=0.01, tmpdir=tmpdir)
        return win
    # laptop
    sh = int(h * 0.9)
    sw = min(w, int(sh * 1.6))
    sx = x + (w - sw) // 2
    lid = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(sx), Emu(y), Emu(sw), Emu(sh))
    lid.adjustments[0] = 0.04; solid(lid.fill, bez); line(lid, '3A4150', 1.2); lid.name = name + '-body'
    m = int(sw * 0.025)
    image(prs, slide, th, [sx + m, y + m, sw - 2 * m, sh - 2 * m], screenshot, name=name + '-screen', rounded=0.01, tmpdir=tmpdir)
    base = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(sx - int(sw * 0.08)), Emu(y + sh), Emu(int(sw * 1.16)), Emu(int(h * 0.06)))
    base.adjustments[0] = 0.5; solid(base.fill, 'C9CED8'); line(base, None); base.name = name + '-base'
    return lid


def timeline(prs, slide, th, box, items, name='timeline'):
    """items: [{date, head, text?, highlight?}] on a horizontal line with nodes; labels alternate."""
    x, y, w, h = box_emu(prs, box)
    n = len(items)
    cy = y + h // 2
    ln = slide.shapes.add_connector(1, Emu(x), Emu(cy), Emu(x + w), Emu(cy))
    ln.line.color.rgb = rgb(th.muted); ln.line.width = Pt(2); ln.name = name + '-line'
    step = w // n
    for i, it in enumerate(items):
        nx = x + step * i + step // 2
        r = int(min(step, h) * 0.09)
        dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Emu(nx - r), Emu(cy - r), Emu(2 * r), Emu(2 * r))
        solid(dot.fill, th.accent if it.get('highlight') else (th.surface if th.dark else 'FFFFFF'), None if it.get('highlight') else 100)
        line(dot, th.accent, 2.5)
        dot.name = '%s-node-%d' % (name, i + 1)
        up = i % 2 == 0
        ty = cy - int(h * 0.46) if up else cy + int(h * 0.1)
        textbox(slide, nx - step // 2 + int(step * 0.04), ty, step - int(step * 0.08), int(h * 0.36),
                [[{'text': it.get('date', ''), 'color': th.accent, 'font': th.display, 'b': th.display_bold, 'size': 20}],
                 [{'text': it.get('head', ''), 'b': True}]] + ([[{'text': it['text'], 'color': th.muted, 'size': 12}]] if it.get('text') else []),
                th.body, 15, th.text, align='c', anchor='b' if up else 't', name='%s-label-%d' % (name, i + 1))


def credit(prs, slide, th, text, name='credit'):
    W, H = prs.slide_width, prs.slide_height
    return textbox(slide, int(W * 0.03), int(H * 0.955), int(W * 0.6), int(H * 0.035), text, th.body, 9, th.muted, name=name, autoshrink=False)
