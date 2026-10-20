#!/usr/bin/env python3
"""Render a .pptx to slide images and a contact sheet for visual QA. MIT License.

usage: python3 render.py deck.pptx [outdir] [--dpi 80] [--cols 4] [--label "text"]
- Uses the skill's fonts and the fonts embedded in the deck itself (template fonts), so previews
  show the real typefaces even when they are not installed.
- Writes <outdir>/slide-NN.jpg and <outdir>/sheet.jpg, prints their paths.
LibreOffice shows the final state of every slide; animations and Morph only play in PowerPoint.
"""
import glob, os, shutil, subprocess, sys, tempfile

def skill_fonts():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from tplkit.assets import fonts_dir
    return fonts_dir()

def extra_font_dirs():
    """Fonts of the template library (LIB/_fonts and every LIB/<id>/fonts) when PPS_LIB is set."""
    lib = os.environ.get('PPS_LIB')
    if not lib or not os.path.isdir(lib):
        return []
    return [d for d in [os.path.join(lib, '_fonts')] + glob.glob(os.path.join(lib, '*', 'fonts')) if os.path.isdir(d)]

def font_env(pptx):
    """A private fontconfig with the skill fonts plus the deck's embedded fonts."""
    here = os.path.dirname(os.path.abspath(__file__))
    tmp = tempfile.mkdtemp(prefix='fonts-')
    emb = os.path.join(tmp, 'embedded')
    try:
        sys.path.insert(0, here)
        from tplkit.pkg import Pkg
        from tplkit.fonts import extract_fonts
        extract_fonts(Pkg(pptx), emb)
    except Exception as e:
        print('note: could not extract embedded fonts:', e, file=sys.stderr)
    conf = os.path.join(tmp, 'fonts.conf')
    open(conf, 'w').write('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig>'
                          '<include ignore_missing="yes">/etc/fonts/fonts.conf</include>'
                          f'<dir>{emb}</dir><dir>{skill_fonts()}</dir>'
                          + ''.join(f'<dir>{d}</dir>' for d in extra_font_dirs())
                          + f'<cachedir>{tmp}/cache</cachedir></fontconfig>')
    return dict(os.environ, FONTCONFIG_FILE=conf), tmp

def soffice_pdf(pptx, outdir, env=None):
    exe = shutil.which('soffice') or shutil.which('libreoffice')
    if not exe: raise SystemExit('LibreOffice (soffice) not found')
    prof = tempfile.mkdtemp(prefix='lo-')
    subprocess.run([exe, f'-env:UserInstallation=file://{prof}', '--headless', '--convert-to', 'pdf', '--outdir', outdir, pptx], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600, env=env)
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(pptx))[0] + '.pdf')
    if not os.path.exists(pdf): raise SystemExit('conversion failed')
    return pdf

def main():
    a = sys.argv[1:]; pptx = a[0]; outdir = a[1] if len(a) > 1 and not a[1].startswith('--') else os.path.splitext(pptx)[0] + '-render'
    dpi = int(a[a.index('--dpi') + 1]) if '--dpi' in a else 80
    cols = int(a[a.index('--cols') + 1]) if '--cols' in a else 4
    fmt = 'png' if '--png' in a else 'jpeg'; ext = 'png' if fmt == 'png' else 'jpg'
    os.makedirs(outdir, exist_ok=True)
    for f in glob.glob(os.path.join(outdir, 'slide-*.*')): os.remove(f)
    env, ftmp = font_env(os.path.abspath(pptx))
    pdf = soffice_pdf(os.path.abspath(pptx), outdir, env)
    shutil.rmtree(ftmp, ignore_errors=True)
    subprocess.run(['pdftoppm', '-' + fmt, '-r', str(dpi), pdf, os.path.join(outdir, 'slide')], check=True)
    files = sorted(glob.glob(os.path.join(outdir, 'slide-*.' + ext)))
    try:
        from PIL import Image
        ims = [Image.open(f) for f in files]; w, h = ims[0].size; g = 8
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * w + (cols + 1) * g, rows * h + (rows + 1) * g), (110, 110, 110))
        for i, im in enumerate(ims): sheet.paste(im, (g + (i % cols) * (w + g), g + (i // cols) * (h + g)))
        sp = os.path.join(outdir, 'sheet.jpg'); sheet.save(sp, quality=85); print(sp)
    except ImportError:
        pass
    for f in files: print(f)

if __name__ == '__main__':
    main()
