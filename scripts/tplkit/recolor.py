"""Recolor a template so it fits the topic (MIT License): rotate the hue of its accent colors in
the XML (shapes, text, gradients, theme) and, optionally, of its graphic images (3D renders,
glows, abstract backgrounds). Photos of people are detected and left alone by default."""
import colorsys, io, re
import numpy as np
from PIL import Image
from lxml import etree
from .pkg import q, shape_box

HEX = re.compile(r'^[0-9A-Fa-f]{6}$')


def hex_to_hsv(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hsv(r, g, b)


def hsv_to_hex(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0, min(1, s)), max(0, min(1, v)))
    return '%02X%02X%02X' % (round(r * 255), round(g * 255), round(b * 255))


def rotate_hex(hx, dh, min_sat=0.18, sat_mul=1.0, mono_to=None):
    h, s, v = hex_to_hsv(hx)
    if s < min_sat or v < 0.08:
        return hx.upper()
    if mono_to is not None:
        return hsv_to_hex(mono_to, s * sat_mul, v)
    return hsv_to_hex(h + dh, s * sat_mul, v)


def accent_hue(pkg, slides):
    """Dominant saturated hue (0..1) used in the slides' XML colors, weighted by count."""
    hist = np.zeros(36)
    for sp in slides:
        x = etree.tostring(pkg.xml(sp)).decode('utf8')
        for hx in re.findall(r'srgbClr val="([0-9A-Fa-f]{6})"', x):
            h, s, v = hex_to_hsv(hx)
            if s > 0.35 and v > 0.25:
                hist[int(h * 36) % 36] += 1
    if hist.sum() == 0:
        return None
    k = int(hist.argmax())
    return (k + 0.5) / 36


def image_accent_hue(pkg, slides, min_area_bytes=20000):
    """Dominant saturated hue of the slides' raster images (weighted by file size)."""
    hist = np.zeros(36)
    seen = set()
    for sp in slides:
        for rid, rtype, target, mode in pkg.rel_list(sp):
            if mode == 'External' or not rtype.endswith('/image'):
                continue
            mp = pkg.resolve(sp, target)
            if mp in seen or mp.lower().endswith(('.svg', '.emf', '.wmf')):
                continue
            seen.add(mp)
            data = pkg.files.get(mp, b'')
            if len(data) < min_area_bytes:
                continue
            try:
                im = Image.open(io.BytesIO(data)); im.thumbnail((96, 96))
                a = np.asarray(im.convert('RGB').convert('HSV')).reshape(-1, 3).astype(float) / 255
            except Exception:
                continue
            sat = a[(a[:, 1] > 0.3) & (a[:, 2] > 0.2)]
            for h in sat[:, 0]:
                hist[int(h * 36) % 36] += len(data) / 1e6
    if hist.sum() == 0:
        return None
    return (int(hist.argmax()) + 0.5) / 36


def image_hue_share(data, hue, tol=0.09):
    """Share of saturated pixels within +-tol of hue, and share of skin-like pixels."""
    im = Image.open(io.BytesIO(data))
    im.thumbnail((160, 160))
    a = np.asarray(im.convert('RGB').convert('HSV')).reshape(-1, 3).astype(float) / 255
    sat = a[(a[:, 1] > 0.3) & (a[:, 2] > 0.2)]
    if len(sat) < 30:
        return 0.0, 0.0, len(sat) / max(1, len(a))
    d = np.abs(((sat[:, 0] - hue) + 0.5) % 1.0 - 0.5)
    share = float((d < tol).mean())
    skin = float(((sat[:, 0] > 0.0) & (sat[:, 0] < 0.11) & (sat[:, 1] < 0.7)).mean())
    return share, skin, len(sat) / len(a)


def rotate_image(data, dh, keep_format=True, mono_to=None):
    im = Image.open(io.BytesIO(data))
    fmt = im.format or 'PNG'
    alpha = im.getchannel('A') if im.mode in ('RGBA', 'LA') or 'transparency' in im.info else None
    hsv = np.asarray(im.convert('RGB').convert('HSV')).copy()
    shift = int(round(dh * 255)) % 256
    if mono_to is not None:
        sat = hsv[..., 1] > 40
        hsv[..., 0] = np.where(sat, int(mono_to * 255) % 256, hsv[..., 0])
    else:
        hsv[..., 0] = (hsv[..., 0].astype(int) + shift) % 256
    out = Image.fromarray(hsv, 'HSV').convert('RGB')
    if alpha is not None:
        out.putalpha(alpha)
        fmt = 'PNG'
    b = io.BytesIO()
    if fmt.upper() in ('JPEG', 'JPG'):
        out.save(b, 'JPEG', quality=92)
    else:
        out.save(b, 'PNG', optimize=True)
    return b.getvalue(), fmt


def recolor(pkg, slides, target_hex, images='auto', sat_mul=1.0, src_hue=None, theme=True, mode='rotate'):
    """Rotate the template's accent hue to target_hex's hue on the given slides (and the theme).
    images: 'auto' (graphic images dominated by the accent hue), 'all', or 'none'.
    Returns a report. Images shared with slides outside `slides` are copied, not edited in place."""
    src_h = src_hue if src_hue is not None else accent_hue(pkg, slides)
    th, ts, tv = hex_to_hsv(target_hex.lstrip('#'))
    if src_h is None:
        return {'skipped': 'no accent color found'}
    dh = th - src_h
    n_xml = 0

    def fix(el):
        nonlocal n_xml
        for c in el.iter(q('a:srgbClr')):
            v = c.get('val')
            if v and HEX.match(v):
                nv = rotate_hex(v, dh, sat_mul=sat_mul, mono_to=th if mode == 'mono' else None)
                if nv != v.upper():
                    c.set('val', nv)
                    n_xml += 1
    for sp in slides:
        fix(pkg.xml(sp))
        pkg.touch(sp)
    for th_part in ([p for p in pkg.files if p.startswith('ppt/theme/theme') and p.endswith('.xml')] if theme else []):
        fix(pkg.xml(th_part))
        pkg.touch(th_part)
    done = {}
    rotated = []
    if images != 'none':
        all_slides = set(pkg.slides())
        W, H = pkg.size()
        for sp in slides:
            # area of the largest shape on this slide that shows each picture
            area_of = {}
            x = pkg.xml(sp)
            for blip in x.iter(q('a:blip')):
                rid = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                e = blip.getparent()
                while e is not None and e.tag.split('}')[1] not in ('sp', 'pic', 'bg'):
                    e = e.getparent()
                b = shape_box(e) if e is not None and e.tag.split('}')[1] != 'bg' else [0, 0, W, H]
                a = (b[2] * b[3]) / (W * H) if b else 1.0
                area_of[rid] = max(area_of.get(rid, 0), a)
            for rid, rtype, target, mode_ in pkg.rel_list(sp):
                if mode_ == 'External' or not rtype.endswith('/image'):
                    continue
                mp = pkg.resolve(sp, target)
                if mp.lower().endswith(('.svg', '.emf', '.wmf')):
                    continue
                if mp not in done:
                    data = pkg.files[mp]
                    try:
                        share, skin, satfrac = image_hue_share(data, src_h)
                        im = Image.open(io.BytesIO(data))
                        alpha = im.mode in ('RGBA', 'LA') or 'transparency' in im.info
                    except Exception:
                        done[mp] = None
                        continue
                    area = area_of.get(rid, 0)
                    if images == 'all':
                        go = True
                    elif area >= 0.6:
                        go = satfrac > 0.03            # backgrounds
                    elif alpha:
                        go = share > 0.3 or mode == 'mono'   # cut-out decorations, glows, 3D objects
                    else:
                        go = share > 0.6 and area < 0.05     # small flat graphics; framed photos stay as they are
                    if not go:
                        done[mp] = None
                        continue
                    nd, fmt = rotate_image(data, dh, mono_to=th if mode == 'mono' else None)
                    ext = 'png' if fmt == 'PNG' else mp.rsplit('.', 1)[-1]
                    users = [s_ for s_ in all_slides if any(pkg.resolve(s_, t) == mp for _, _, t, m in pkg.rel_list(s_) if m != 'External')]
                    if set(users) <= set(slides) and ext == mp.rsplit('.', 1)[-1]:
                        pkg.files[mp] = nd
                        done[mp] = mp
                    else:
                        nn = pkg.new_name('ppt/media/recolor{}.' + ext)
                        pkg.add_part(nn, nd)
                        pkg.ensure_default(ext, 'image/png' if ext == 'png' else 'image/jpeg')
                        done[mp] = nn
                    rotated.append(mp)
                if done.get(mp) and done[mp] != mp:
                    rels = pkg.rels(sp)
                    for e in rels:
                        if e.get('Id') == rid:
                            e.set('Target', pkg.relative(sp, done[mp]))
                    pkg.touch(pkg.rels_name(sp))
    return {'from_hue': round(src_h * 360), 'to_hue': round(th * 360), 'xml_colors': n_xml, 'images': rotated}
