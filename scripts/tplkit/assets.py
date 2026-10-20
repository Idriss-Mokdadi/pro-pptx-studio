"""Where the skill's data files live (MIT License).

To stay under the skill upload limit, fonts, 3D objects and generator styles ship as one archive,
assets/bundle.tar.xz. The first script that needs them unpacks it into a cache folder
(PPS_CACHE or ~/.cache/pro-pptx-studio); a folder that already has assets/fonts is used as is.
"""
import os, tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(HERE))


def data_root():
    if os.path.isdir(os.path.join(SKILL, 'assets', 'fonts')):
        return SKILL
    bundle = os.path.join(SKILL, 'assets', 'bundle.tar.xz')
    cache = os.environ.get('PPS_CACHE') or os.path.join(os.path.expanduser('~'), '.cache', 'pro-pptx-studio')
    if not os.path.exists(bundle):
        return SKILL
    stamp = os.path.join(cache, '.unpacked-%d' % os.path.getsize(bundle))
    if not os.path.exists(stamp):
        os.makedirs(cache, exist_ok=True)
        with tarfile.open(bundle, 'r:xz') as z:
            try:
                z.extractall(cache, filter='data')
            except TypeError:          # Python < 3.12
                z.extractall(cache)
        open(stamp, 'w').write('ok')
    return cache


def fonts_dir():
    return os.path.join(data_root(), 'assets', 'fonts')


if __name__ == '__main__':
    print(data_root())
