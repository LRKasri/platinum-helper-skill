"""Prose walkthroughs (game.json paragraph_items): split every route paragraph into entities — one checkbox per thing
the player gets / fights / reaches / talks to, titled with that thing's name (sample_ui/7.png) — after the route
translation exists.

usage: python3 -I prepare_entities.py <work> [jobs=2] [--combined]
--combined: for item-per-entity guides (Wuchang, Phantom Blade Zero) — only the checkable items whose title joins
several things ("NPC: X + Weapon: Y", "#46 & #47 – A / B").
Writes <work>/tr_in/entities-NN.json; agents answer in <work>/tr_out/entities-NN.json (brief: references/entities-brief.md).
assemble.py then replaces each paragraph by its entity items ("route" parts stay as plain non-checkable text).
"""
import glob, json, os, re, sys

args = [a for a in sys.argv[1:] if not a.startswith('--')]
W = args[0]
NJOBS = int(args[1]) if len(args) > 1 else 2
COMBINED = '--combined' in sys.argv
SEP = re.compile(r' \+ | / |\s&(amp;)?\s|#\d+\s*&(amp;)?\s*#\d+')


def J(*p):
    return json.load(open(os.path.join(W, *p), encoding='utf-8'))


def st(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or '')).strip()


cfg = J('game.json')
areas = J('data_en', 'areas.json')
bt = J('data_en', 'bytype.json') if os.path.exists(os.path.join(W, 'data_en', 'bytype.json')) else {}
TR = {}
for f in sorted(glob.glob(os.path.join(W, 'tr_out', '*.json'))):  # route jobs are named route-NN or r1, r45 …
    for k, v in (json.load(open(f, encoding='utf-8')).get('units') or {}).items():
        if isinstance(v, dict):
            TR[k] = v

nonplat = set(cfg.get('non_platinum_types', []))
types = {k: {'zh': v[0], 'en': v[1], 'counts_for_platinum': k not in nonplat} for k, v in cfg['types'].items()
         if k not in ('other', 'tip')}
types['other'] = {'zh': '其他物品 / 事项', 'en': 'any other item or task', 'counts_for_platinum': 'other' not in nonplat}
types['route'] = {'zh': '路线说明（不勾选）', 'en': 'route text, no checkbox'}
types.setdefault('warn', {'zh': '警告 / 抉择（不勾选，红框）', 'en': 'warning or choice, no checkbox'})

# by-type entries, numbered exactly like assemble.py (1-based, after dedupe) -> "ref": "<type>-<n>"
cols = []
for c in cfg.get('collections', []):
    if c.get('source', 'tag') != 'bytype':
        continue
    entries = bt.get(c['type'], {}).get('entries', [])
    if c.get('dedupe'):
        seen = set()
        entries = [e for e in entries if not (e['label_en'] in seen or seen.add(e['label_en']))]
    for n, e in enumerate(entries, 1):
        cols.append({'ref': f'{c["type"]}-{n}', 'label': e['label_en'], 'area': e.get('area_en', ''),
                     'where': st(e.get('body_en', ''))[:260]})

paras = []
for r in areas:
    for a in r['areas']:
        for s in a['sections']:
            for it in s['items']:
                if not st(it['head_en']):
                    continue
                if COMBINED and (it['kind'] != 'item' or not SEP.search(it['head_en'])):
                    continue
                tr = TR.get(it['id'], {})
                head_en, body_en, head_zh, body_zh = st(it['head_en']), it['body_en'], st(tr.get('head', '')), tr.get('body', '')
                if not st(body_en) and len(head_en) > 120:  # parser quirk: the whole paragraph landed in the title
                    head_en, body_en, head_zh, body_zh = '', it['head_en'], '', (tr.get('head', '') + ' ' + body_zh).strip()
                paras.append({'id': it['id'], 'region': r['title_en'], 'step': a['title_en'], 'tags': it['tags'],
                               'bold_names_en': head_en, 'bold_names_zh': head_zh,
                               'body_en': body_en, 'body_zh': body_zh, 'n_images': len(it['imgs'])})

total = sum(len(p['body_en']) + len(p['body_zh']) for p in paras)
os.makedirs(os.path.join(W, 'tr_in'), exist_ok=True)
jobs, cur, acc = [], [], 0
for p in paras:  # split on region boundaries near equal size
    cur.append(p)
    acc += len(p['body_en']) + len(p['body_zh'])
    if acc >= total * (len(jobs) + 1) / NJOBS and len(jobs) < NJOBS - 1:
        nxt = paras[paras.index(p) + 1] if paras.index(p) + 1 < len(paras) else None
        if nxt is None or nxt['region'] != p['region']:
            jobs.append(cur)
            cur = []
if cur:
    jobs.append(cur)
for k, ps in enumerate(jobs, 1):
    name = f'entities-{k:02d}'
    kinds = {t for p in ps for t in p['tags']}
    cj = [c for c in cols if c['ref'].rsplit('-', 1)[0] in kinds] if COMBINED else cols
    json.dump({'job': name, 'mode': 'combined' if COMBINED else 'prose', 'types': types, 'collection_entries': cj, 'paragraphs': ps},
              open(os.path.join(W, 'tr_in', name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(name, len(ps), 'paragraphs', sum(len(p['body_en']) + len(p['body_zh']) for p in ps), 'chars',
          sorted({p['region'] for p in ps}, key=lambda x: [r['title_en'] for r in areas].index(x)))
print('collection entries:', len(cols))
