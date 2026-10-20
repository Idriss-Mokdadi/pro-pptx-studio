"""Slide transitions (Morph with Fade fallback, Fade, Push) and entrance animations for template
decks (MIT License). Animations run automatically after the slide appears ('auto') or one step per
click ('click'); titles are never animated by the planner."""
from lxml import etree
from .pkg import q, find_shape, shape_id, top_shapes, shape_box, shape_text

DUR = {'fade': 450, 'rise': 550, 'pop': 450, 'wipe': 600, 'zoom': 500}
PRESET = {'fade': (10, 0), 'rise': (42, 0), 'pop': (53, 16), 'wipe': (22, 8), 'zoom': (53, 16)}


class Ids:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return self.n


def _tgt(spid):
    return '<p:tgtEl><p:spTgt spid="%s"/></p:tgtEl>' % spid


def _anim(ids, spid, attr, a, b, dur):
    return ('<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="%d" dur="%d" fill="hold"/>%s'
            '<p:attrNameLst><p:attrName>%s</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst>'
            '<p:tav tm="0"><p:val><p:strVal val="%s"/></p:val></p:tav>'
            '<p:tav tm="100000"><p:val><p:strVal val="%s"/></p:val></p:tav></p:tavLst></p:anim>') % (ids(), dur, _tgt(spid), attr, a, b)


def _effect(ids, spid, effect, delay, node):
    pid, sub = PRESET.get(effect, PRESET['fade'])
    dur = DUR.get(effect, 450)
    body = ('<p:set><p:cBhvr><p:cTn id="%d" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>%s'
            '<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>') % (ids(), _tgt(spid))
    filt = 'wipe(left)' if effect == 'wipe' else 'fade'
    body += '<p:animEffect transition="in" filter="%s"><p:cBhvr><p:cTn id="%d" dur="%d"/>%s</p:cBhvr></p:animEffect>' % (filt, ids(), dur, _tgt(spid))
    if effect == 'rise':
        body += _anim(ids, spid, 'ppt_x', '#ppt_x', '#ppt_x', dur) + _anim(ids, spid, 'ppt_y', '#ppt_y+.05', '#ppt_y', dur)
    elif effect in ('pop', 'zoom'):
        body += _anim(ids, spid, 'ppt_w', '#ppt_w*0.70', '#ppt_w', dur) + _anim(ids, spid, 'ppt_h', '#ppt_h*0.70', '#ppt_h', dur)
    return ('<p:par><p:cTn id="%d" presetID="%d" presetClass="entr" presetSubtype="%d" fill="hold" grpId="0" nodeType="%s">'
            '<p:stCondLst><p:cond delay="%d"/></p:stCondLst><p:childTnLst>%s</p:childTnLst></p:cTn></p:par>') % (ids(), pid, sub, node, delay, body)


def timing_xml(steps, mode='auto', kinds=None, stagger=380):
    ids = Ids()
    root, seq = ids(), ids()
    groups = ''
    if mode == 'click':
        for st in steps:
            outer, inner = ids(), ids()
            fx = ''.join(_effect(ids, s, st['effect'], i * 60, 'clickEffect' if i == 0 else 'withEffect') for i, s in enumerate(st['spids']))
            groups += ('<p:par><p:cTn id="%d" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>'
                       '<p:par><p:cTn id="%d" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>%s</p:childTnLst></p:cTn></p:par>'
                       '</p:childTnLst></p:cTn></p:par>') % (outer, inner, fx)
    else:
        outer, inner = ids(), ids()
        fx = ''
        for si, st in enumerate(steps):
            for i, s in enumerate(st['spids']):
                fx += _effect(ids, s, st['effect'], si * stagger + i * 40, 'withEffect')
        groups = ('<p:par><p:cTn id="%d" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="%d"/></p:cond></p:stCondLst><p:childTnLst>'
                  '<p:par><p:cTn id="%d" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>%s</p:childTnLst></p:cTn></p:par>'
                  '</p:childTnLst></p:cTn></p:par>') % (outer, seq, inner, fx)
    bld = ''
    for s in dict.fromkeys(x for st in steps for x in st['spids']):
        if (kinds or {}).get(s) == 'sp':
            bld += '<p:bldP spid="%s" grpId="0" animBg="1"/>' % s
    return ('<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:tnLst><p:par><p:cTn id="%d" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
            '<p:seq concurrent="1" nextAc="seek"><p:cTn id="%d" dur="indefinite" nodeType="mainSeq"><p:childTnLst>%s</p:childTnLst></p:cTn>'
            '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
            '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
            '</p:childTnLst></p:cTn></p:par></p:tnLst>%s</p:timing>') % (root, seq, groups, ('<p:bldLst>%s</p:bldLst>' % bld) if bld else '')


def transition_xml(kind='morph', speed='slow'):
    spd = speed if speed in ('fast', 'med', 'slow') else 'med'
    P = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    if kind == 'fade':
        return '<p:transition %s spd="%s"><p:fade/></p:transition>' % (P, spd)
    if kind == 'push':
        return '<p:transition %s spd="%s"><p:push dir="u"/></p:transition>' % (P, spd)
    if kind == 'morph':
        return ('<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" %s>'
                '<mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">'
                '<p:transition spd="%s"><p159:morph option="byObject"/></p:transition></mc:Choice>'
                '<mc:Fallback><p:transition spd="%s"><p:fade/></p:transition></mc:Fallback></mc:AlternateContent>') % (P, spd, spd)
    return ''


def strip_motion(x):
    for e in list(x):
        ln = etree.QName(e).localname
        if ln in ('transition', 'timing'):
            x.remove(e)
        elif ln == 'AlternateContent' and e.find('.//' + q('p:transition')) is not None:
            x.remove(e)


def apply(slide_x, steps=None, transition='morph', speed='slow', mode='auto', stagger=380):
    """steps: [{'shapes': [names or '#id'], 'effect': 'rise'}]. Unknown shapes are reported."""
    strip_motion(slide_x)
    missing = []
    st2 = []
    kinds = {}
    for st in steps or []:
        ids_ = []
        for k in st['shapes']:
            sh = find_shape(slide_x, k)
            if sh is None:
                missing.append(k)
                continue
            sid = shape_id(sh)
            kinds[sid] = etree.QName(sh).localname
            ids_.append(sid)
        if ids_:
            st2.append({'spids': ids_, 'effect': st.get('effect', 'fade')})
    xml = transition_xml(transition, speed)
    if st2 and mode != 'none':
        xml += timing_xml(st2, mode, kinds, stagger)
    # CT_Slide order: cSld, clrMapOvr?, transition?, timing?, extLst?
    clr = slide_x.find(q('p:clrMapOvr'))
    anchor = clr if clr is not None else slide_x.find(q('p:cSld'))
    frag = etree.fromstring('<w xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">%s</w>' % xml)
    for e in reversed(list(frag)):
        anchor.addnext(e)
    return missing


def auto_steps(slide_x, title_names=(), skip_background=True, slide_size=None):
    """A sensible default: reveal non-title content left-to-right, top-to-bottom, in rows."""
    W, H = slide_size or (12192000, 6858000)
    items = []
    for sh in top_shapes(slide_x):
        b = shape_box(sh)
        if not b:
            continue
        name = sh.find('.//' + q('p:cNvPr')).get('name')
        if name in title_names:
            continue
        if skip_background and b[2] * b[3] > 0.5 * W * H:
            continue
        if b[2] < W * 0.01 and b[3] < H * 0.01:
            continue
        items.append((b, '#' + shape_id(sh), bool(shape_text(sh).strip())))
    items.sort(key=lambda t: (round(t[0][1] / (H * 0.12)), t[0][0]))
    steps = []
    for b, key, has_text in items:
        steps.append({'shapes': [key], 'effect': 'rise' if has_text else 'fade'})
    return steps
