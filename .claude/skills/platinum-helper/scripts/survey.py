"""Stage 2 helper: look at how items are written on the route pages, so you can write game.json.

usage: python3 -I survey.py <work_dir> [url-substring-filter]   survey titles (default filter "collectible-locations")
       python3 -I survey.py <work_dir> --dump <slug> [N]         print the first N (default 80) parsed blocks of one page

The survey prints the most common title shapes of bold-lead items — "Type:" prefixes (Wuchang "Weapon: Halberd"),
trailing "(Type)" (Phantom Blade Zero "#4 – Hunter's Insight (Accessory)"), first words after "#N –" — and the
heading shapes per level. If headings far outnumber bold leads, every item is its own heading (Stellar Blade
"<h3>Hydra / Box #4</h3>"): set "item_heading_level" in game.json and re-run the survey with it set.
"""
import sys, os, re, glob, json, html as H
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ppx

W = sys.argv[1]
cfg = json.load(open(os.path.join(W, 'game.json'))) if os.path.exists(os.path.join(W, 'game.json')) else {}


def st(s):
    return H.unescape(re.sub(r'<[^>]+>', '', s or '')).replace('\xa0', ' ').strip()


if '--dump' in sys.argv:
    slug = sys.argv[sys.argv.index('--dump') + 1]
    n = int(sys.argv[sys.argv.index('--dump') + 2]) if len(sys.argv) > sys.argv.index('--dump') + 2 else 80
    path = os.path.join(W, 'raw', slug.rstrip('/').split('/')[-1] + ('' if slug.endswith('.html') else '.html'))
    for i, b in enumerate(ppx.blocks(ppx.body_of(open(path, encoding='utf-8').read()))[:n]):
        if b['k'] == 'h':
            print(f'{i:3d} H{b["level"]}  {b["text"][:110]}')
        elif b['k'] == 'p':
            tag = 'LEAD' if b.get('lead') else ('RED ' if b.get('red') else 'P   ')
            print(f'{i:3d} {tag} {st(b["lead"] or "")[:60] + " | " if b.get("lead") else ""}{st(b["rest"] if b.get("lead") else b["html"])[:110]}'
                  + (f'  [+{len(b["imgs"])} img]' if b['imgs'] else ''))
        elif b['k'] == 'ul':
            print(f'{i:3d} UL   ' + ' ; '.join(st(x)[:40] for x in b['items'][:4]))
        else:
            print(f'{i:3d} {b["k"].upper():4s} {b.get("src", "") or b.get("imgs", "")}')
    sys.exit()

flt = next((a for a in sys.argv[2:] if not a.startswith('--')), 'collectible-locations')
hubs = {u.split('#')[0].rstrip('/').split('/')[-1] for u in cfg.get('sources', {}).values()}
outline = os.path.join(W, 'hub_outline.json')
if os.path.exists(outline):
    hubs |= {h['url'].rstrip('/').split('/')[-1] for h in json.load(open(outline))['hubs'].values()}
files = [f for f in sorted(glob.glob(os.path.join(W, 'raw', '*.html')))
         if flt in f and os.path.basename(f)[:-5] not in hubs]
pre, paren, word, nonum, heads, ex = Counter(), Counter(), Counter(), Counter(), Counter(), {}
n_lead = 0
lvl = cfg.get('item_heading_level')
for f in files:
    bl = ppx.blocks(ppx.body_of(open(f, encoding='utf-8').read()))
    if lvl:
        bl = ppx.promote_headings(bl, int(lvl))
    for b in bl:
        if b['k'] == 'h' and not ppx.SKIP_HEADINGS.match(b['text']):
            k = f'h{b["level"]}: ' + re.sub(r'\d+', 'N', b['text'])[:36]
            heads[k] += 1
            ex.setdefault('head:' + k, b['text'])
        if b['k'] != 'p' or not b.get('lead'):
            continue
        n_lead += 1
        h = st(b['lead'])
        m = re.match(r'#[\d &#]+[–-]\s*(.*)', h)
        core = m.group(1) if m else h
        p = re.match(r'([A-Z][\w’\' ]{1,30}?):', core)
        if p:
            pre[p.group(1)] += 1
            ex.setdefault('pre:' + p.group(1), h)
        t = re.findall(r'\(([^)]{2,40})\)', core)
        if t:
            k = re.sub(r'\s*[–-]\s*MISSABLE', '', t[-1])
            paren[k] += 1
            ex.setdefault('paren:' + k, h)
        if m:
            w = ' '.join(core.split()[:2])
            word[w] += 1
            ex.setdefault('word:' + w, h)
        else:
            k = re.sub(r'\d+', 'N', core)[:40]
            nonum[k] += 1
            ex.setdefault('nonum:' + k, h)
print(f'{len(files)} route pages, {n_lead} bold-lead items, {sum(heads.values())} headings'
      + (f' (item_heading_level={lvl})' if lvl else ''))
if sum(heads.values()) > 3 * max(n_lead, 1):
    print('!! headings far outnumber bold-lead items: items are probably headings -> set "item_heading_level" (usually 3)')
for title, c, pfx in (('"Type:" prefixes', pre, 'pre:'), ('trailing "(…)"', paren, 'paren:'),
                      ('first words after "#N –"', word, 'word:'), ('un-numbered titles', nonum, 'nonum:'),
                      ('heading shapes', heads, 'head:')):
    if not c:
        continue
    print(f'\n== {title}')
    for k, v in c.most_common(40):
        print(f'{v:5d}  {k:40s} e.g. {ex[pfx + k][:80]}')
