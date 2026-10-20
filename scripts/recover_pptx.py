#!/usr/bin/env python3
"""Recover a truncated .pptx (an interrupted download): read every complete entry from the local
file headers and write a new, valid package. Missing pictures are replaced by nothing; the
report lists what was lost. MIT License.

usage: python3 recover_pptx.py broken.pptx fixed.pptx
"""
import struct, sys, zipfile, zlib


def recover(src, dst):
    data = open(src, 'rb').read()
    pos, entries, lost = 0, {}, []
    while True:
        i = data.find(b'PK\x03\x04', pos)
        if i < 0 or i + 30 > len(data):
            break
        ver, flag, method, mt, md, crc, csize, usize, nlen, xlen = struct.unpack('<HHHHHIIIHH', data[i + 4:i + 30])
        name = data[i + 30:i + 30 + nlen].decode('utf8', 'replace')
        start = i + 30 + nlen + xlen
        try:
            if method == 8:
                d = zlib.decompressobj(-15)
                out = d.decompress(data[start:start + (csize if csize and not flag & 8 else len(data) - start)])
                if not d.eof:
                    raise ValueError('truncated')
                consumed = len(data[start:]) - len(d.unused_data) if (flag & 8 or not csize) else csize
            elif method == 0:
                if flag & 8 and not csize:
                    raise ValueError('stored entry with descriptor')
                out = data[start:start + csize]
                if len(out) < csize:
                    raise ValueError('truncated')
                consumed = csize
            else:
                raise ValueError('method %d' % method)
            entries[name] = out
            pos = start + consumed
        except Exception as e:
            lost.append(name)
            pos = start
    # lost pictures become a transparent pixel so the package stays valid
    import base64
    px = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
    for n in lost:
        if n.startswith('ppt/media/'):
            entries[n] = px
    import posixpath, re
    for n in list(entries):
        if n.endswith('.rels'):
            base = posixpath.dirname(posixpath.dirname(n))
            for t in re.findall(rb'Target="([^"]+)"', entries[n]):
                t = t.decode()
                if t.startswith('http') or 'TargetMode' in t:
                    continue
                p = posixpath.normpath(posixpath.join(base, t)) if not t.startswith('/') else t[1:]
                if p.startswith('ppt/media/') and p not in entries:
                    entries[p] = px
                    lost.append(p + ' (missing)')
    if '[Content_Types].xml' not in entries:
        ov = {
            'ppt/presentation.xml': 'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml',
            'ppt/slides/': 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml',
            'ppt/slideLayouts/': 'application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml',
            'ppt/slideMasters/': 'application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml',
            'ppt/notesSlides/': 'application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml',
            'ppt/notesMasters/': 'application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml',
            'ppt/theme/': 'application/vnd.openxmlformats-officedocument.theme+xml',
            'ppt/presProps.xml': 'application/vnd.openxmlformats-officedocument.presentationml.presProps+xml',
            'ppt/viewProps.xml': 'application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml',
            'ppt/tableStyles.xml': 'application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml',
            'ppt/charts/chart': 'application/vnd.openxmlformats-officedocument.drawingml.chart+xml',
            'docProps/core.xml': 'application/vnd.openxmlformats-package.core-properties+xml',
            'docProps/app.xml': 'application/vnd.openxmlformats-officedocument.extended-properties+xml',
        }
        defaults = {'rels': 'application/vnd.openxmlformats-package.relationships+xml', 'xml': 'application/xml',
                    'png': 'image/png', 'jpeg': 'image/jpeg', 'jpg': 'image/jpeg', 'gif': 'image/gif', 'svg': 'image/svg+xml',
                    'fntdata': 'application/x-fontdata', 'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'mp4': 'video/mp4', 'emf': 'image/x-emf', 'wmf': 'image/x-wmf', 'tiff': 'image/tiff'}
        exts = {n.rsplit('.', 1)[-1].lower() for n in entries if '.' in n}
        x = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        x += ''.join('<Default Extension="%s" ContentType="%s"/>' % (e, defaults[e]) for e in sorted(exts) if e in defaults)
        for n in sorted(entries):
            if not n.endswith('.xml') or '/_rels/' in n:
                continue
            for k, ct in ov.items():
                if n == k or (k.endswith('/') and n.startswith(k)) or (k.endswith('chart') and n.startswith(k)):
                    x += '<Override PartName="/%s" ContentType="%s"/>' % (n, ct)
                    break
        x += '</Types>'
        entries['[Content_Types].xml'] = x.encode('utf8')
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as z:
        if '[Content_Types].xml' in entries:
            z.writestr('[Content_Types].xml', entries.pop('[Content_Types].xml'))
        for n, b in entries.items():
            z.writestr(n, b)
    return len(entries), lost


if __name__ == '__main__':
    n, lost = recover(sys.argv[1], sys.argv[2])
    print({'recovered_entries': n, 'lost': lost})
