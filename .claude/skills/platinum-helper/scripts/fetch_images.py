"""Stage 5: decide how screenshots are delivered, download them if needed -> data_en/images.json

usage: python3 -I fetch_images.py <work_dir> [--mode auto|embed|folder|remote|none]

Modes (game.json "images": {"mode": "auto", "embed_limit_mb": 8}):
  embed   download (resized to <=768 px wide when Pillow is available) and inline as base64 -> one self-contained HTML
  folder  download into images/ next to the HTML (HTML stays small; ship the folder with it)
  remote  keep the PowerPyx image URLs; the page loads them only when the reader taps the screenshot button
  none    no screenshots
  auto    embed if the estimated total is <= embed_limit_mb, otherwise remote   (the user's stated preference)
"""
import sys, os, re, json, subprocess, hashlib

W = sys.argv[1]
cfg = json.load(open(os.path.join(W, 'game.json'), encoding='utf-8'))
icfg = cfg.get('images', {})
mode = sys.argv[sys.argv.index('--mode') + 1] if '--mode' in sys.argv else icfg.get('mode', 'auto')
limit = float(icfg.get('embed_limit_mb', 8))
EST_KB = 60  # typical 768-px PowerPyx jpg

areas = json.load(open(os.path.join(W, 'data_en', 'areas.json'), encoding='utf-8'))
bt_path = os.path.join(W, 'data_en', 'bytype.json')
bt = json.load(open(bt_path, encoding='utf-8')) if os.path.exists(bt_path) else {}
urls = []
for r in areas:
    for a in r['areas']:
        for s in a['sections']:
            for it in s['items']:
                urls += it.get('imgs', [])
for v in bt.values():
    for e in v.get('entries', []):
        urls += e.get('imgs', [])
urls = list(dict.fromkeys(u for u in urls if u))
est_mb = len(urls) * EST_KB / 1024
if mode == 'auto':
    mode = 'embed' if est_mb <= limit else 'remote'
print(f'{len(urls)} screenshots, ~{est_mb:.1f} MB at 768px -> mode: {mode}')


def key_of(u):
    base = re.sub(r'\.(jpe?g|png|webp)$', '', u.rstrip('/').split('/')[-1], flags=re.I)
    base = re.sub(r'-\d+x\d+$', '', base)
    return re.sub(r'[^A-Za-z0-9_-]', '_', base)[-60:] + '-' + hashlib.md5(u.encode()).hexdigest()[:6]


out = {'mode': mode, 'map': {}}
idir = os.path.join(W, 'images')
if mode in ('embed', 'folder'):
    os.makedirs(idir, exist_ok=True)
    try:
        from PIL import Image
    except Exception:
        Image = None
    for i, u in enumerate(urls):
        k = key_of(u)
        f = os.path.join(idir, k + '.jpg')
        if not os.path.exists(f):
            src = 'https:' + u if u.startswith('//') else u
            subprocess.run(['curl', '-sL', '-A', 'Mozilla/5.0', '-o', f, src], check=False)
            subprocess.run(['sleep', '0.3'])
            if Image is not None and os.path.exists(f):
                try:
                    im = Image.open(f)
                    if im.width > 768:
                        im = im.convert('RGB').resize((768, round(im.height * 768 / im.width)))
                        im.save(f, 'JPEG', quality=80)
                except Exception as e:
                    print('  resize failed', u, e)
        ok = os.path.exists(f) and os.path.getsize(f) > 1000
        out['map'][u] = {'key': k, 'file': os.path.relpath(f, W) if ok else None, 'remote': u}
        if (i + 1) % 50 == 0:
            print(f'  {i + 1}/{len(urls)}')
    total = sum(os.path.getsize(os.path.join(W, v['file'])) for v in out['map'].values() if v['file'])
    print(f'downloaded {sum(1 for v in out["map"].values() if v["file"])} files, {total / 1048576:.1f} MB')
else:
    for u in urls:
        out['map'][u] = {'key': key_of(u), 'remote': 'https:' + u if u.startswith('//') else u}
json.dump(out, open(os.path.join(W, 'data_en', 'images.json'), 'w'), indent=1)
print('wrote data_en/images.json')
