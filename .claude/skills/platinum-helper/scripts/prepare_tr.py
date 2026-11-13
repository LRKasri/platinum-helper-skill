"""Stage 4a: split everything that needs translating into job files -> tr_in/<job>.json

usage: python3 -I prepare_tr.py <work_dir> [--chunk 30000]

Jobs:
  route-NN  route steps (areas) + items; a region's summary/leave block is produced by the job holding its first step
  meta      roadmap, trophy descriptions + notes, collectible-guide intro, questline intros   (split meta-a/meta-b if large)
  endings   endings guide (only if pages.endings)
  boss      boss facts: difficulty / recommended weapon / rewards (only if pages.bosses)
Unit ids here are exactly the ids assemble.py looks up — don't rename them.
Prints a size table; give each job to one translation subagent (references/translation-brief.md).
"""
import sys, os, re, json, html as H

W = sys.argv[1]
CHUNK = int(sys.argv[sys.argv.index('--chunk') + 1]) if '--chunk' in sys.argv else 30000
OUT = os.path.join(W, 'tr_in')
os.makedirs(OUT, exist_ok=True)


def J(*p, default=None):
    path = os.path.join(W, *p)
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else default


def st(s):
    return H.unescape(re.sub(r'<[^>]+>', '', s or '')).replace('\xa0', ' ').strip()


areas = J('data_en', 'areas.json')
cfg_step_mode = (J('game.json', default={}) or {}).get('step_mode', 'page')
trophies = J('data_en', 'trophies.json', default=[])
ql = J('data_en', 'questlines.json', default={'intro': [], 'questlines': []})
endings = J('data_en', 'endings_blocks.json', default=[])
bosses = J('data_en', 'bosses.json', default=[])
road = J('data_en', 'roadmap_blocks.json', default=[])
hub = J('data_en', 'hub_intro_blocks.json', default=[])
sizes = []


def save(job, obj, n):
    json.dump(obj, open(os.path.join(OUT, job + '.json'), 'w'), ensure_ascii=False, indent=1)
    sizes.append((job, len(obj.get('units', [])), n))


# ---- route jobs ----
jobs, cur, size = [], None, 0
for r in areas:
    for ai, a in enumerate(r['areas']):
        asz = sum(len(it['head_en']) + len(it['body_en']) for s in a['sections'] for it in s['items']) + len(a.get('reach_en', ''))
        if cur is None or size + asz > CHUNK * 1.15:
            cur = {'regions': [], 'areas': [], 'units': []}
            jobs.append(cur)
            size = 0
        if ai == 0:
            cur['regions'].append({'id': r['id'], 'title': r['title_en'], 'note': r.get('note_en', ''),
                                   'all_steps': [x['title_en'] for x in r['areas']]})
        show_intro = cfg_step_mode != 'page' and ai == 0  # region intro (counts list) is shown only for one-page regions
        cur['areas'].append({'id': a['id'], 'region': r['id'], 'title': a['title_en'], 'intro': a.get('intro_en', '') if show_intro else '',
                             'reach': a.get('reach_en', ''), 'sections': [s['title_en'] for s in a['sections']]})
        for s in a['sections']:
            for it in s['items']:
                cur['units'].append({'id': it['id'], 'step': a['title_en'], 'kind': it['kind'], 'tags': it['tags'],
                                     'head': it['head_en'], 'body': it['body_en']})
        size += asz
for i, j in enumerate(jobs, 1):
    j['job'] = f'route-{i:02d}'
    save(j['job'], j, sum(len(u['head']) + len(u['body']) for u in j['units']))


# ---- meta ----
units = []


def add(uid, html, ctx):
    if html and st(html):
        units.append({'id': uid, 'ctx': ctx, 'text': html})


def add_blocks(blocks, prefix, ctx):
    for i, b in enumerate(blocks):
        if b['k'] == 'h':
            add(f'{prefix}-h{i}', H.escape(b['text']), ctx + ' heading')
        elif b['k'] == 'p':
            add(f'{prefix}-p{i}', b['html'], ctx)
        elif b['k'] == 'ul':
            for j, x in enumerate(b['items']):
                add(f'{prefix}-ul{i}-{j}', x, ctx + ' list item')


add_blocks(road, 'road', 'trophy roadmap')
for i, t in enumerate(trophies):
    add(f'trophy-{i}-desc', H.escape(t['desc_en']), f'trophy "{t["name_en"]}" in-game description')
    add(f'trophy-{i}-detail', t['detail_en'], f'trophy "{t["name_en"]}" guide notes')
add_blocks(hub, 'hub', 'collectible guide intro')
for qi, q in enumerate(ql.get('questlines', [])):
    for bi, b in enumerate(q['blocks']):
        if b['k'] == 'p' and b.get('lead'):
            break
        if b['k'] == 'p':
            add(f'ql{qi}-p{bi}', b['html'], f'questline "{q["name_en"]}" intro')
        elif b['k'] == 'ul':
            for j, x in enumerate(b['items']):
                add(f'ql{qi}-ul{bi}-{j}', x, f'questline "{q["name_en"]}" intro list')
for bi, b in enumerate(ql.get('intro', [])):
    if b['k'] == 'p':
        add(f'qlintro-p{bi}', b['html'], 'questlines guide intro')
total = sum(len(u['text']) for u in units)
if total > CHUNK * 1.5:
    half, acc, a_units = total / 2, 0, []
    for u in units:
        if acc < half:
            a_units.append(u)
            acc += len(u['text'])
    b_units = units[len(a_units):]
    save('meta-a', {'job': 'meta-a', 'units': a_units}, acc)
    save('meta-b', {'job': 'meta-b', 'units': b_units}, total - acc)
else:
    save('meta', {'job': 'meta', 'units': units}, total)

# ---- collection entry descriptions (collections with "desc": true) ----
cfg = J('game.json', default={}) or {}
bt = J('data_en', 'bytype.json', default={}) or {}
units = []
for c in cfg.get('collections', []):
    if c.get('desc') and c.get('source') == 'bytype':
        for n, e in enumerate(bt.get(c['type'], {}).get('entries', []), 1):
            add(f'col-{c["type"]}-{n}-desc', e['body_en'], f'how to find "{e["label_en"]}" ({e["area_en"]})')
if units:
    total = sum(len(u['text']) for u in units)
    if total > CHUNK * 1.3:
        half, acc, a_units = total / 2, 0, []
        for u in units:
            if acc < half:
                a_units.append(u)
                acc += len(u['text'])
        save('collections-a', {'job': 'collections-a', 'units': a_units}, acc)
        save('collections-b', {'job': 'collections-b', 'units': units[len(a_units):]}, total - acc)
    else:
        save('collections', {'job': 'collections', 'units': units}, total)

# ---- endings ----
if endings:
    units = []
    add_blocks(endings, 'end', 'endings guide')
    save('endings', {'job': 'endings', 'units': units}, sum(len(u['text']) for u in units))

# ---- boss facts ----
if bosses:
    units = []
    for i, b in enumerate(bosses):
        for k, blk in enumerate(b['blocks']):
            if blk['k'] == 'p' and re.match(r'<b>(Difficulty|Recommended Weapon|Reward|Rewards)', blk['html']):
                add(f'boss-{i}-p{k}', blk['html'], f'boss "{b["name_en"]}"')
    save('boss', {'job': 'boss', 'units': units}, sum(len(u['text']) for u in units))

print(f'{"job":12s} {"units":>6s} {"chars":>8s}')
for j, n, c in sizes:
    print(f'{j:12s} {n:6d} {c:8d}')
print('total chars', sum(c for _, _, c in sizes))
