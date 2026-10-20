"""Low-level .pptx package editing for template-first decks (MIT License).

A Pkg holds every part of a .pptx in memory. It can reorder, duplicate and delete slides, copy a
slide or a single shape from another template (images, charts and embedded fonts come along, and
geometry is rescaled when the two templates have different slide sizes), and save the result.
"""
import copy, hashlib, io, os, posixpath, re, zipfile
from lxml import etree

NS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'pr': 'http://schemas.openxmlformats.org/package/2006/relationships',
    'ct': 'http://schemas.openxmlformats.org/package/2006/content-types',
}
R = NS['r']
RT = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
REL_SLIDE, REL_LAYOUT, REL_NOTES = RT + 'slide', RT + 'slideLayout', RT + 'notesSlide'
REL_FONT = RT + 'font'
CT_SLIDE = 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml'
MEDIA_REL = ('image', 'media', 'video', 'audio', 'hdphoto')
TREE_REL = ('chart', 'diagramData', 'diagramLayout', 'diagramQuickStyle', 'diagramColors', 'diagramDrawing', 'package', 'oleObject')


def q(tag):
    p, t = tag.split(':')
    return '{%s}%s' % (NS[p], t)


def parse(b):
    return etree.fromstring(b, etree.XMLParser(remove_blank_text=False, huge_tree=True))


def ser(el):
    return etree.tostring(el, xml_declaration=True, encoding='UTF-8', standalone=True)


class Pkg:
    def __init__(self, path=None, data=None):
        self.path = path
        z = zipfile.ZipFile(path if path else io.BytesIO(data))
        self.files = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
        z.close()
        self._xml = {}

    # ---------- xml cache ----------
    def xml(self, part):
        if part not in self._xml:
            self._xml[part] = parse(self.files[part])
        return self._xml[part]

    def touch(self, part, el=None):
        if el is not None:
            self._xml[part] = el
        self.files[part] = ser(self._xml[part])

    def flush(self):
        for part, el in self._xml.items():
            if part in self.files or part.endswith('.xml') or part.endswith('.rels'):
                self.files[part] = ser(el)

    # ---------- content types ----------
    def ctypes(self):
        return self.xml('[Content_Types].xml')

    def add_ctype(self, part, ctype):
        ct = self.ctypes()
        ext = part.rsplit('.', 1)[-1].lower()
        if any(e.get('Extension', '').lower() == ext for e in ct.findall(q('ct:Default'))) and not ext == 'xml':
            return
        pn = '/' + part
        for e in ct.findall(q('ct:Override')):
            if e.get('PartName') == pn:
                return
        if ctype is None:
            return
        o = etree.SubElement(ct, q('ct:Override'))
        o.set('PartName', pn)
        o.set('ContentType', ctype)

    def ctype_of(self, part):
        ct = self.ctypes()
        pn = '/' + part
        for e in ct.findall(q('ct:Override')):
            if e.get('PartName') == pn:
                return e.get('ContentType')
        ext = part.rsplit('.', 1)[-1].lower()
        for e in ct.findall(q('ct:Default')):
            if e.get('Extension', '').lower() == ext:
                return e.get('ContentType')
        return None

    def ensure_default(self, ext, ctype):
        ct = self.ctypes()
        if not any(e.get('Extension', '').lower() == ext.lower() for e in ct.findall(q('ct:Default'))):
            d = etree.Element(q('ct:Default'))
            d.set('Extension', ext)
            d.set('ContentType', ctype)
            ct.insert(0, d)

    # ---------- relationships ----------
    @staticmethod
    def rels_name(part):
        d, f = posixpath.split(part)
        return posixpath.join(d, '_rels', f + '.rels')

    def rels(self, part):
        rn = self.rels_name(part)
        if rn not in self.files and rn not in self._xml:
            self._xml[rn] = etree.Element(q('pr:Relationships'), nsmap={None: NS['pr']})
            self.files[rn] = ser(self._xml[rn])
        return self.xml(rn)

    def rel_list(self, part):
        return [(e.get('Id'), e.get('Type'), e.get('Target'), e.get('TargetMode')) for e in self.rels(part)]

    def resolve(self, part, target):
        if target.startswith('/'):
            return target[1:]
        return posixpath.normpath(posixpath.join(posixpath.dirname(part), target))

    def relative(self, from_part, to_part):
        return posixpath.relpath(to_part, posixpath.dirname(from_part))

    def add_rel(self, part, rtype, target_part=None, external=None):
        rels = self.rels(part)
        used = {e.get('Id') for e in rels}
        n = 1
        while 'rId%d' % n in used:
            n += 1
        e = etree.SubElement(rels, q('pr:Relationship'))
        e.set('Id', 'rId%d' % n)
        e.set('Type', rtype)
        if external:
            e.set('Target', external)
            e.set('TargetMode', 'External')
        else:
            e.set('Target', self.relative(part, target_part))
        self.touch(self.rels_name(part))
        return 'rId%d' % n

    def targets(self, part, rtype_suffix):
        return [self.resolve(part, t) for _, ty, t, m in self.rel_list(part) if ty.endswith('/' + rtype_suffix) and m != 'External']

    # ---------- names ----------
    def new_name(self, pattern):
        n = 1
        while pattern.format(n) in self.files:
            n += 1
        return pattern.format(n)

    def add_part(self, name, data, ctype=None):
        self.files[name] = data
        self._xml.pop(name, None)
        if ctype:
            self.add_ctype(name, ctype)
        return name

    # ---------- presentation ----------
    PRES = 'ppt/presentation.xml'

    def size(self):
        s = self.xml(self.PRES).find(q('p:sldSz'))
        return int(s.get('cx')), int(s.get('cy'))

    def slides(self):
        pres = self.xml(self.PRES)
        lst = pres.find(q('p:sldIdLst'))
        rmap = {i: self.resolve(self.PRES, t) for i, _, t, _ in self.rel_list(self.PRES)}
        return [rmap[s.get('{%s}id' % R)] for s in (lst if lst is not None else [])]

    def set_slides(self, parts):
        """Make the deck show exactly these slide parts, in this order. Unlisted slides are dropped on save()."""
        pres = self.xml(self.PRES)
        lst = pres.find(q('p:sldIdLst'))
        if lst is None:
            lst = etree.Element(q('p:sldIdLst'))
            pres.find(q('p:sldMasterIdLst')).addnext(lst)
        rels = self.rels(self.PRES)
        rmap = {self.resolve(self.PRES, e.get('Target')): e.get('Id') for e in rels if e.get('Type') == REL_SLIDE}
        for e in list(lst):
            lst.remove(e)
        nid = 256
        for part in parts:
            rid = rmap.get(part) or self.add_rel(self.PRES, REL_SLIDE, part)
            rmap[part] = rid
            s = etree.SubElement(lst, q('p:sldId'))
            s.set('id', str(nid))
            s.set('{%s}id' % R, rid)
            nid += 1
        # drop rels to slides no longer listed
        keep = set(parts)
        for e in list(rels):
            if e.get('Type') == REL_SLIDE and self.resolve(self.PRES, e.get('Target')) not in keep:
                rels.remove(e)
        self.touch(self.rels_name(self.PRES))
        self.touch(self.PRES)

    # ---------- duplicating inside one package ----------
    def duplicate_slide(self, part):
        name = self.new_name('ppt/slides/slide{}.xml')
        x = copy.deepcopy(self.xml(part))
        src_rels = self.rels(part)
        strip_slide_links(x, [e.get('Id') for e in src_rels if e.get('Type') == REL_SLIDE])
        self.add_part(name, ser(x), CT_SLIDE)
        self._xml[name] = x
        new = etree.Element(q('pr:Relationships'), nsmap={None: NS['pr']})
        for e in src_rels:
            if e.get('Type') in (REL_NOTES, REL_SLIDE):
                continue   # notes are rebuilt; links to other template slides would keep them alive
            ne = copy.deepcopy(e)
            if e.get('TargetMode') != 'External':
                tp = self.resolve(part, e.get('Target'))
                ne.set('Target', self.relative(name, tp))
            new.append(ne)
        rn = self.rels_name(name)
        self._xml[rn] = new
        self.files[rn] = ser(new)
        return name

    # ---------- garbage collection ----------
    def reachable(self):
        listed = set(self.slides())
        seen, stack = set(), ['_rels/.rels']
        root_rels = self.xml('_rels/.rels')
        for e in root_rels:
            if e.get('TargetMode') != 'External':
                stack.append(e.get('Target').lstrip('/'))
        while stack:
            p = stack.pop()
            if p in seen or p not in self.files:
                continue
            if re.match(r'ppt/slides/slide\d+\.xml$', p) and p not in listed:
                continue   # a slide dropped from the deck stays dropped even if a notes page points at it
            if re.match(r'ppt/notesSlides/', p):
                owners = [self.resolve(p, e.get('Target')) for e in self.xml(self.rels_name(p)) if e.get('Type') == REL_SLIDE] if self.rels_name(p) in self.files else []
                if owners and not any(o in listed for o in owners):
                    continue
            seen.add(p)
            rn = self.rels_name(p)
            if rn in self.files:
                seen.add(rn)
                for e in self.xml(rn):
                    if e.get('TargetMode') == 'External':
                        continue
                    stack.append(self.resolve(p, e.get('Target')))
        seen.update({'[Content_Types].xml', '_rels/.rels'})
        return seen

    def cleanup(self):
        self.flush()
        keep = self.reachable()
        for n in list(self.files):
            if n not in keep:
                del self.files[n]
                self._xml.pop(n, None)
        ct = self.ctypes()
        for e in list(ct.findall(q('ct:Override'))):
            if e.get('PartName')[1:] not in self.files:
                ct.remove(e)

    def save(self, path):
        self.cleanup()
        self.flush()
        tmp = path + '.tmp'
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('[Content_Types].xml', self.files['[Content_Types].xml'])
            z.writestr('_rels/.rels', self.files['_rels/.rels'])
            for n, b in self.files.items():
                if n in ('[Content_Types].xml', '_rels/.rels'):
                    continue
                ct = zipfile.ZIP_STORED if n.rsplit('.', 1)[-1].lower() in ('jpg', 'jpeg', 'png', 'gif', 'mp4', 'fntdata') else zipfile.ZIP_DEFLATED
                z.writestr(zipfile.ZipInfo(n, date_time=(2026, 1, 1, 0, 0, 0)), b, compress_type=ct)
        os.replace(tmp, path)

    # ---------- embedded fonts ----------
    def embedded_fonts(self):
        """{typeface: [(style, part)]}"""
        out = {}
        pres = self.xml(self.PRES)
        lst = pres.find(q('p:embeddedFontLst'))
        if lst is None:
            return out
        rmap = {i: self.resolve(self.PRES, t) for i, _, t, _ in self.rel_list(self.PRES)}
        for ef in lst:
            f = ef.find(q('p:font'))
            face = f.get('typeface')
            for ch in ef:
                if ch.tag == q('p:font'):
                    continue
                rid = ch.get('{%s}id' % R)
                if rid in rmap:
                    out.setdefault(face, []).append((etree.QName(ch).localname, rmap[rid], copy.deepcopy(f)))
        return out

    def add_embedded_font(self, face, styles, font_el=None):
        """styles: [(style, bytes)] of EOT data. Skips faces already embedded."""
        if face in self.embedded_fonts():
            return False
        pres = self.xml(self.PRES)
        lst = pres.find(q('p:embeddedFontLst'))
        if lst is None:
            lst = etree.Element(q('p:embeddedFontLst'))
            notes = pres.find(q('p:notesSz'))
            notes.addnext(lst)
        ef = etree.SubElement(lst, q('p:embeddedFont'))
        if font_el is None:
            font_el = etree.Element(q('p:font'))
            font_el.set('typeface', face)
            font_el.set('charset', '1')
        ef.append(font_el)
        order = {'regular': 0, 'bold': 1, 'italic': 2, 'boldItalic': 3}
        for sty, data in sorted(styles, key=lambda s: order.get(s[0], 9)):
            name = self.new_name('ppt/fonts/font{}.fntdata')
            self.add_part(name, data)
            self.ensure_default('fntdata', 'application/x-fontdata')
            rid = self.add_rel(self.PRES, REL_FONT, name)
            e = etree.SubElement(ef, q('p:' + sty))
            e.set('{%s}id' % R, rid)
        for k, v in (('embedTrueTypeFonts', '1'), ('saveSubsetFonts', '1')):
            if pres.get(k) is None:
                pres.set(k, v)
        self.touch(self.PRES)
        return True


# ---------------------------------------------------------------------------
# geometry scaling
# ---------------------------------------------------------------------------
GEOM_ATTR = {
    q('a:off'): ('x', 'y'), q('a:ext'): ('cx', 'cy'), q('a:chOff'): ('x', 'y'), q('a:chExt'): ('cx', 'cy'),
}
SIZE_ATTR = {q('a:rPr'): 'sz', q('a:defRPr'): 'sz', q('a:endParaRPr'): 'sz'}


def scale_tree(el, s, dx=0, dy=0, top=True):
    """Scale every coordinate and size under el by s; shift top-level offsets by (dx, dy)."""
    for e in el.iter():
        t = e.tag
        if t in GEOM_ATTR:
            for a in GEOM_ATTR[t]:
                v = e.get(a)
                if v is not None:
                    e.set(a, str(int(round(int(v) * s))))
        elif t in SIZE_ATTR:
            v = e.get('sz')
            if v is not None:
                e.set('sz', str(max(100, int(round(int(v) * s)))))
        elif t == q('a:spcPts'):
            v = e.get('val')
            if v is not None:
                e.set('val', str(int(round(int(v) * s))))
        elif t == q('a:ln'):
            v = e.get('w')
            if v is not None:
                e.set('w', str(int(round(int(v) * s))))
        elif t == q('a:bodyPr'):
            for a in ('lIns', 'tIns', 'rIns', 'bIns'):
                v = e.get(a)
                if v is not None:
                    e.set(a, str(int(round(int(v) * s))))
        elif t in (q('a:outerShdw'), q('a:innerShdw'), q('a:glow'), q('a:softEdge'), q('a:blur')):
            for a in ('blurRad', 'dist', 'rad'):
                v = e.get(a)
                if v is not None:
                    e.set(a, str(int(round(int(v) * s))))
    if dx or dy:
        # shift only the outermost xfrm offsets of top-level shapes
        for shp in el.iterchildren() if not top else [el]:
            pass


def shift_shape(shape, dx, dy):
    xf = shape_xfrm(shape)
    if xf is not None:
        off = xf.find(q('a:off'))
        if off is not None:
            off.set('x', str(int(off.get('x')) + int(dx)))
            off.set('y', str(int(off.get('y')) + int(dy)))


def shape_xfrm(shape):
    tag = etree.QName(shape).localname
    if tag == 'grpSp':
        return shape.find(q('p:grpSpPr') + '/' + q('a:xfrm'))
    if tag == 'graphicFrame':
        return shape.find(q('p:xfrm'))
    sppr = shape.find(q('p:spPr'))
    return sppr.find(q('a:xfrm')) if sppr is not None else None


def shape_box(shape):
    xf = shape_xfrm(shape)
    if xf is None:
        return None
    off, ext = xf.find(q('a:off')), xf.find(q('a:ext'))
    if off is None or ext is None:
        return None
    return [int(off.get('x')), int(off.get('y')), int(ext.get('cx')), int(ext.get('cy'))]


def set_box(shape, box):
    """Move/resize a shape; for groups the children follow (chOff/chExt untouched)."""
    xf = shape_xfrm(shape)
    off, ext = xf.find(q('a:off')), xf.find(q('a:ext'))
    off.set('x', str(int(box[0]))); off.set('y', str(int(box[1])))
    ext.set('cx', str(int(box[2]))); ext.set('cy', str(int(box[3])))


def fit_transform(src_size, dst_size):
    sw, sh = src_size
    dw, dh = dst_size
    s = min(dw / sw, dh / sh)
    return s, (dw - sw * s) / 2, (dh - sh * s) / 2


# ---------------------------------------------------------------------------
# copying parts between packages
# ---------------------------------------------------------------------------
class Copier:
    """Copies parts from src into dst, de-duplicating media by content hash."""

    def __init__(self, src, dst):
        self.src, self.dst = src, dst
        self.map = {}
        self.hashes = {}
        for n, b in dst.files.items():
            if n.startswith('ppt/media/'):
                self.hashes[hashlib.sha1(b).hexdigest()] = n

    def media(self, sp):
        if sp in self.map:
            return self.map[sp]
        b = self.src.files[sp]
        h = hashlib.sha1(b).hexdigest()
        if h in self.hashes:
            self.map[sp] = self.hashes[h]
            return self.map[sp]
        ext = sp.rsplit('.', 1)[-1].lower()
        name = self.dst.new_name('ppt/media/image{}.' + ext) if not sp.startswith('ppt/media/media') else self.dst.new_name('ppt/media/media{}.' + ext)
        self.dst.add_part(name, b)
        ctype = self.src.ctype_of(sp)
        if ctype:
            self.dst.ensure_default(ext, ctype)
        self.hashes[h] = name
        self.map[sp] = name
        return name

    def tree(self, sp, folder_pattern):
        """Deep-copy a part (chart, diagram…) with its own relationships."""
        if sp in self.map:
            return self.map[sp]
        ext = sp.rsplit('.', 1)[-1]
        name = self.dst.new_name(folder_pattern + '.' + ext)
        self.map[sp] = name
        self.dst.add_part(name, self.src.files[sp], self.src.ctype_of(sp))
        if not self.dst.ctype_of(name):
            self.dst.ensure_default(ext, self.src.ctype_of(sp) or 'application/octet-stream')
        srn = self.src.rels_name(sp)
        if srn in self.src.files:
            new = etree.Element(q('pr:Relationships'), nsmap={None: NS['pr']})
            for e in self.src.xml(srn):
                ne = copy.deepcopy(e)
                if e.get('TargetMode') != 'External':
                    tp = self.src.resolve(sp, e.get('Target'))
                    kind = e.get('Type').rsplit('/', 1)[-1]
                    if kind in MEDIA_REL:
                        np_ = self.media(tp)
                    else:
                        base = posixpath.dirname(tp) + '/' + re.sub(r'\d*\.\w+$', '', posixpath.basename(tp)) + '{}'
                        np_ = self.tree(tp, base)
                    ne.set('Target', self.dst.relative(name, np_))
                new.append(ne)
            rn = self.dst.rels_name(name)
            self.dst._xml[rn] = new
            self.dst.files[rn] = ser(new)
        return name


def strip_slide_links(x, rids):
    """Remove click/hover actions that jump to other slides of the template (navigation bars)."""
    rids = set(rids)
    if not rids:
        return
    for tag in ('a:hlinkClick', 'a:hlinkMouseOver'):
        for e in list(x.iter(q(tag))):
            if e.get('{%s}id' % R) in rids:
                e.getparent().remove(e)


def rel_ids_in(el):
    ids = set()
    for e in el.iter():
        for k, v in e.attrib.items():
            if k.startswith('{%s}' % R):
                ids.add(v)
    return ids


def remap_rel_ids(el, mapping):
    for e in el.iter():
        for k, v in list(e.attrib.items()):
            if k.startswith('{%s}' % R) and v in mapping:
                e.set(k, mapping[v])


def blank_layout(pkg):
    """A layout of the first master with no visible shapes (prefer type=blank)."""
    master = pkg.targets(pkg.PRES, 'slideMaster')[0]
    layouts = pkg.targets(master, 'slideLayout')
    best, score = layouts[0], -1
    for lp in layouts:
        x = pkg.xml(lp)
        n_sp = len(x.findall('.//' + q('p:sp')))
        sc = (100 if x.get('type') == 'blank' else 0) - n_sp
        if sc > score:
            best, score = lp, sc
    return best


def copy_slide(src, src_part, dst, layout=None, after=None):
    """Copy one slide from src into dst. Returns the new slide part (not yet in the slide list)."""
    cp = Copier(src, dst)
    x = copy.deepcopy(src.xml(src_part))
    name = dst.new_name('ppt/slides/slide{}.xml')
    s, dx, dy = fit_transform(src.size(), dst.size())
    rels_out = etree.Element(q('pr:Relationships'), nsmap={None: NS['pr']})
    mapping = {}
    for rid, rtype, target, mode in src.rel_list(src_part):
        kind = rtype.rsplit('/', 1)[-1]
        e = etree.SubElement(rels_out, q('pr:Relationship'))
        e.set('Id', rid)
        e.set('Type', rtype)
        if mode == 'External':
            e.set('Target', target); e.set('TargetMode', 'External')
            continue
        tp = src.resolve(src_part, target)
        if kind == 'slideLayout':
            e.set('Target', dst.relative(name, layout or blank_layout(dst)))
        elif kind == 'notesSlide':
            rels_out.remove(e)
        elif kind in MEDIA_REL or tp.startswith('ppt/media/'):
            e.set('Target', dst.relative(name, cp.media(tp)))
        elif kind in TREE_REL or kind.startswith('diagram'):
            base = posixpath.dirname(tp) + '/' + re.sub(r'\d*\.\w+$', '', posixpath.basename(tp)) + '{}'
            e.set('Target', dst.relative(name, cp.tree(tp, base)))
        elif kind == 'slide':
            rels_out.remove(e)  # internal slide links are dropped
            strip_slide_links(x, [rid])
        else:
            e.set('Target', dst.relative(name, cp.tree(tp, posixpath.dirname(tp) + '/part{}')))
    # flatten visible layout/master art if the source layout carries any
    lay = src.targets(src_part, 'slideLayout')
    if lay:
        flatten_layout_art(src, src_part, lay[0], x, rels_out, cp, dst, name)
    if abs(s - 1) > 1e-6 or dx or dy:
        tree = x.find(q('p:cSld') + '/' + q('p:spTree'))
        for shp in tree:
            if etree.QName(shp).localname in ('sp', 'pic', 'grpSp', 'graphicFrame', 'cxnSp'):
                scale_tree(shp, s)
                shift_shape(shp, dx, dy)
        # also scale text in charts? left as is (chart fonts are in their own part)
    dst.add_part(name, ser(x), CT_SLIDE)
    dst._xml[name] = x
    rn = dst.rels_name(name)
    dst._xml[rn] = rels_out
    dst.files[rn] = ser(rels_out)
    copy_fonts_for(src, dst, x)
    return name


def flatten_layout_art(src, slide_part, layout_part, slide_x, rels_out, cp, dst, new_name):
    """If the slide inherits a background or decorative shapes from its layout/master, bring them
    into the slide itself so it survives being moved to another template."""
    csld = slide_x.find(q('p:cSld'))
    has_bg = csld.find(q('p:bg')) is not None
    tree = csld.find(q('p:spTree'))
    show_master = slide_x.get('showMasterSp') != '0'
    sources = [layout_part]
    lay_x = src.xml(layout_part)
    if lay_x.get('showMasterSp') != '0' and show_master:
        sources += src.targets(layout_part, 'slideMaster')
    insert_at = 2  # after nvGrpSpPr and grpSpPr
    for sp in sources:
        sx = src.xml(sp)
        scsld = sx.find(q('p:cSld'))
        if not has_bg and scsld.find(q('p:bg')) is not None:
            bg = copy.deepcopy(scsld.find(q('p:bg')))
            _bring_rels(src, sp, bg, rels_out, cp, dst, new_name)
            csld.insert(0, bg)
            has_bg = True
        for shp in scsld.find(q('p:spTree')):
            ln = etree.QName(shp).localname
            if ln not in ('sp', 'pic', 'grpSp', 'cxnSp'):
                continue
            if shp.find('.//' + q('p:ph')) is not None:
                continue  # placeholders are resolved separately
            c = copy.deepcopy(shp)
            _bring_rels(src, sp, c, rels_out, cp, dst, new_name)
            tree.insert(insert_at, c)
            insert_at += 1
    resolve_placeholders(src, slide_part, layout_part, slide_x)
    renumber_ids(slide_x)


def _bring_rels(src, from_part, el, rels_out, cp, dst, new_name):
    mapping = {}
    used = {e.get('Id') for e in rels_out}
    for rid in rel_ids_in(el):
        for i, ty, t, m in src.rel_list(from_part):
            if i != rid:
                continue
            n = 1
            while 'rId%d' % n in used:
                n += 1
            nid = 'rId%d' % n
            used.add(nid)
            e = etree.SubElement(rels_out, q('pr:Relationship'))
            e.set('Id', nid); e.set('Type', ty)
            if m == 'External':
                e.set('Target', t); e.set('TargetMode', 'External')
            else:
                e.set('Target', dst.relative(new_name, cp.media(src.resolve(from_part, t))))
            mapping[rid] = nid
    remap_rel_ids(el, mapping)


def _find_ph(x, ph):
    t, idx = ph.get('type', 'body'), ph.get('idx')
    for sp in x.iter(q('p:sp')):
        p2 = sp.find('.//' + q('p:ph'))
        if p2 is None:
            continue
        if idx is not None and p2.get('idx') == idx:
            return sp
    for sp in x.iter(q('p:sp')):
        p2 = sp.find('.//' + q('p:ph'))
        if p2 is not None and p2.get('type', 'body') == t:
            return sp
    alias = {'ctrTitle': 'title', 'subTitle': 'body'}
    if t in alias:
        for sp in x.iter(q('p:sp')):
            p2 = sp.find('.//' + q('p:ph'))
            if p2 is not None and p2.get('type', 'body') == alias[t]:
                return sp
    return None


def resolve_placeholders(src, slide_part, layout_part, slide_x):
    """Turn placeholders into ordinary text boxes with explicit geometry and first-level text style."""
    masters = src.targets(layout_part, 'slideMaster')
    lay_x = src.xml(layout_part)
    mas_x = src.xml(masters[0]) if masters else None
    for sp in list(slide_x.iter(q('p:sp'))):
        ph = sp.find('.//' + q('p:ph'))
        if ph is None:
            continue
        chain = [c for c in (_find_ph(lay_x, ph), _find_ph(mas_x, ph) if mas_x is not None else None) if c is not None]
        sppr = sp.find(q('p:spPr'))
        if sppr.find(q('a:xfrm')) is None:
            for c in chain:
                xf = c.find(q('p:spPr') + '/' + q('a:xfrm'))
                if xf is not None:
                    sppr.insert(0, copy.deepcopy(xf))
                    break
        # merge lvl1 defaults: layout lstStyle > master lstStyle > master txStyles
        defaults = {}
        ph_type = ph.get('type', 'body')
        style_lists = []
        for c in chain:
            ls = c.find('.//' + q('a:lstStyle'))
            if ls is not None:
                style_lists.append(ls.find(q('a:lvl1pPr')))
        if mas_x is not None:
            tx = mas_x.find(q('p:txStyles'))
            if tx is not None:
                key = 'p:titleStyle' if ph_type in ('title', 'ctrTitle') else 'p:bodyStyle'
                st = tx.find(q(key))
                if st is not None:
                    style_lists.append(st.find(q('a:lvl1pPr')))
        body = sp.find(q('p:txBody'))
        if body is not None:
            for p in body.findall(q('a:p')):
                ppr = p.find(q('a:pPr'))
                for r in p.findall(q('a:r')) + p.findall(q('a:endParaRPr')):
                    rpr = r if r.tag == q('a:endParaRPr') else r.find(q('a:rPr'))
                    if rpr is None:
                        rpr = etree.Element(q('a:rPr'))
                        r.insert(0, rpr)
                    for lvl in style_lists:
                        if lvl is None:
                            continue
                        d = lvl.find(q('a:defRPr'))
                        if d is None:
                            continue
                        for k in ('sz', 'b', 'i', 'spc', 'cap'):
                            if rpr.get(k) is None and d.get(k) is not None:
                                rpr.set(k, d.get(k))
                        for child in d:
                            ln = etree.QName(child).localname
                            if rpr.find(child.tag) is None and ln in ('solidFill', 'gradFill', 'latin', 'ea', 'cs'):
                                # keep schema order roughly: fills before fonts
                                rpr.append(copy.deepcopy(child))
                if ppr is None and style_lists and style_lists[0] is not None and style_lists[0].get('algn'):
                    ppr = etree.Element(q('a:pPr'))
                    ppr.set('algn', style_lists[0].get('algn'))
                    p.insert(0, ppr)
            bp = body.find(q('a:bodyPr'))
            for c in chain:
                cb = c.find(q('p:txBody') + '/' + q('a:bodyPr'))
                if cb is not None and bp is not None:
                    for k, v in cb.attrib.items():
                        if bp.get(k) is None:
                            bp.set(k, v)
                    for ch in cb:
                        if bp.find(ch.tag) is None:
                            bp.append(copy.deepcopy(ch))
        ph.getparent().remove(ph)


def renumber_ids(slide_x):
    n = 1
    for e in slide_x.iter(q('p:cNvPr')):
        n += 1
        e.set('id', str(n))


def copy_fonts_for(src, dst, slide_x):
    faces = set(re.findall(r'typeface="([^"+][^"]*)"', etree.tostring(slide_x).decode('utf8')))
    have = dst.embedded_fonts()
    for face, items in src.embedded_fonts().items():
        if face in faces and face not in have:
            dst.add_embedded_font(face, [(sty, src.files[part]) for sty, part, _ in items], items[0][2])


def copy_shape(src, src_part, shape, dst, dst_part, box=None, scale=None, place=None):
    """Copy one shape element (sp/pic/grpSp/graphicFrame) from a src slide onto a dst slide.
    box: [x,y,cx,cy] target box in EMU (aspect kept, centred); scale: factor if no box."""
    cp = Copier(src, dst)
    el = copy.deepcopy(shape)
    mapping = {}
    for rid in rel_ids_in(el):
        for i, ty, t, m in src.rel_list(src_part):
            if i != rid:
                continue
            kind = ty.rsplit('/', 1)[-1]
            if m == 'External':
                mapping[rid] = dst.add_rel(dst_part, ty, external=t)
                continue
            tp = src.resolve(src_part, t)
            if kind in MEDIA_REL or tp.startswith('ppt/media/'):
                np_ = cp.media(tp)
            else:
                np_ = cp.tree(tp, posixpath.dirname(tp) + '/' + re.sub(r'\d*\.\w+$', '', posixpath.basename(tp)) + '{}')
            mapping[rid] = dst.add_rel(dst_part, ty, np_)
    remap_rel_ids(el, mapping)
    b = shape_box(el)
    if place and b:
        s_, nx, ny = place
        scale_tree(el, s_)
        nb = shape_box(el)
        shift_shape(el, nx - nb[0], ny - nb[1])
    elif box and b:
        s = min(box[2] / b[2], box[3] / b[3]) if b[2] and b[3] else 1
        scale_tree(el, s)
        nb = shape_box(el)
        shift_shape(el, box[0] + (box[2] - nb[2]) / 2 - nb[0], box[1] + (box[3] - nb[3]) / 2 - nb[1])
    elif scale:
        s0, _, _ = fit_transform(src.size(), dst.size())
        scale_tree(el, scale * s0)
    else:
        s0, dx, dy = fit_transform(src.size(), dst.size())
        if abs(s0 - 1) > 1e-6:
            scale_tree(el, s0)
            shift_shape(el, dx, dy)
    dx_ = dst.xml(dst_part)
    tree = dx_.find(q('p:cSld') + '/' + q('p:spTree'))
    tree.append(el)
    # unique ids
    used = {int(e.get('id')) for e in dx_.iter(q('p:cNvPr')) if e.get('id', '').isdigit()}
    nxt = max(used | {1}) + 1
    for e in el.iter(q('p:cNvPr')):
        e.set('id', str(nxt)); nxt += 1
    dst.touch(dst_part)
    copy_fonts_for(src, dst, el)
    return el


# ---------------------------------------------------------------------------
# shape lookup helpers
# ---------------------------------------------------------------------------
def sp_tree(slide_x):
    return slide_x.find(q('p:cSld') + '/' + q('p:spTree'))


def top_shapes(slide_x):
    return [e for e in sp_tree(slide_x) if etree.QName(e).localname in ('sp', 'pic', 'grpSp', 'graphicFrame', 'cxnSp')]


def shape_name(shape):
    c = shape.find('.//' + q('p:cNvPr'))
    return c.get('name') if c is not None else ''


def shape_id(shape):
    c = shape.find('.//' + q('p:cNvPr'))
    return c.get('id') if c is not None else ''


def find_shape(slide_x, key):
    """key: shape name, '#id', or a shape element."""
    if not isinstance(key, str):
        return key
    for c in slide_x.iter(q('p:cNvPr')):
        if (key.startswith('#') and c.get('id') == key[1:]) or c.get('name') == key:
            # climb to the shape element
            e = c.getparent()
            while etree.QName(e).localname not in ('sp', 'pic', 'grpSp', 'graphicFrame', 'cxnSp'):
                e = e.getparent()
            return e
    return None


def remove_shape(slide_x, key):
    e = find_shape(slide_x, key)
    if e is not None:
        e.getparent().remove(e)
        return True
    return False


def shape_text(shape):
    return '\n'.join(''.join(t.text or '' for t in p.iter(q('a:t'))) for p in shape.iter(q('a:p')))


def copy_region(src, src_part, region, dst, dst_part, box, prefix='', skip_background=True):
    """Copy every top-level shape whose centre lies in `region` (EMU [x,y,w,h] of the source slide)
    into `box` (EMU) on the destination slide, keeping their layout. Names get `prefix`."""
    sx = src.xml(src_part)
    rx, ry, rw, rh = region
    s = min(box[2] / rw, box[3] / rh)
    ox = box[0] + (box[2] - rw * s) / 2
    oy = box[1] + (box[3] - rh * s) / 2
    SW, SH = src.size()
    out = []
    for sh in top_shapes(sx):
        b = shape_box(sh)
        if not b:
            continue
        if skip_background and b[2] * b[3] > 0.6 * SW * SH:
            continue
        cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
        if not (rx <= cx <= rx + rw and ry <= cy <= ry + rh):
            continue
        el = copy_shape(src, src_part, sh, dst, dst_part, place=(s, ox + (b[0] - rx) * s, oy + (b[1] - ry) * s))
        if prefix:
            for c in el.iter(q('p:cNvPr')):
                c.set('name', prefix + c.get('name', ''))
        out.append(el)
    dst.touch(dst_part)
    return out


def adapt_text(elements, on='dark', light='FFFFFF', muted='B8C2D6', dark='161A22', muted_dark='4A5262'):
    """Make copied text readable on a dark (or light) slide: recolor text that has too little contrast."""
    import colorsys
    n = 0
    for el in elements:
        for rpr in list(el.iter(q('a:rPr'))) + list(el.iter(q('a:endParaRPr'))) + list(el.iter(q('a:defRPr'))):
            sf = rpr.find(q('a:solidFill'))
            clr = sf.find(q('a:srgbClr')) if sf is not None else None
            if clr is None:
                if sf is None and rpr.tag == q('a:rPr'):
                    sf = etree.Element(q('a:solidFill'))
                    clr = etree.SubElement(sf, q('a:srgbClr'))
                    clr.set('val', '000000')
                    ln = rpr.find(q('a:ln'))
                    (ln.addnext(sf) if ln is not None else rpr.insert(0, sf))
                else:
                    continue
            v = clr.get('val', '000000')
            r, g, b = (int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))
            h, s_, val = colorsys.rgb_to_hsv(r, g, b)
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            sz = int(rpr.get('sz', '1800'))
            if on == 'dark' and lum < 0.45 and s_ < 0.5:
                clr.set('val', light if (rpr.get('b') in ('1', 'true') or sz >= 2000) else muted)
                n += 1
            elif on == 'light' and lum > 0.6 and s_ < 0.5:
                clr.set('val', dark if (rpr.get('b') in ('1', 'true') or sz >= 2000) else muted_dark)
                n += 1
    return n
