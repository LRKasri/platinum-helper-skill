"""Stage 3a: collect every English proper noun the page will show -> glossary/terms_en.json

usage: python3 -I make_terms.py <work_dir>

Categories (each entry {"en", "ctx"} where ctx is a snippet of where it appears):
  regions, steps, trophies, bosses, questlines, endings, type:<tag> (item names per route type),
  collection:<type> (names from by-type pages), dialogue (quoted strings that look like menu/dialogue options),
  misc (frequent capitalised phrases not covered above)
Hand the categories to glossary-research subagents (see references/glossary-research.md).
"""
import sys, os, re, json, html as H
from collections import Counter, OrderedDict

W = sys.argv[1]
cfg = json.load(open(os.path.join(W, 'game.json'), encoding='utf-8'))


def J(*p, default=None):
    path = os.path.join(W, *p)
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else default


def st(s):
    return H.unescape(re.sub(r'<[^>]+>', ' ', s or '')).replace('\xa0', ' ').strip()


areas = J('data_en', 'areas.json')
bt = J('data_en', 'bytype.json', default={})
trophies = J('data_en', 'trophies.json', default=[])
bosses = J('data_en', 'bosses.json', default=[])
qls = J('data_en', 'questlines.json', default={'questlines': []})
endings = J('data_en', 'endings_blocks.json', default=[])

items = [(a['title_en'], it) for r in areas for a in r['areas'] for s in a['sections'] for it in s['items']]
corpus = [(a, st(it['head_en']) + '. ' + st(it['body_en'])) for a, it in items]


def ctx(term):
    for a, t in corpus:
        i = t.find(term)
        if i >= 0:
            return f'[{a}] ' + t[max(0, i - 100):i + 140]
    return ''


T = OrderedDict()
T['regions'] = [{'en': r['title_en'], 'ctx': r.get('note_en', '')[:160]} for r in areas]
T['steps'] = [{'en': a['title_en'], 'ctx': st(a.get('reach_en', ''))[:160]} for r in areas for a in r['areas']]
T['trophies'] = [{'en': t['name_en'], 'ctx': t['desc_en']} for t in trophies]
T['bosses'] = [{'en': b['name_en'], 'ctx': ''} for b in bosses]
T['questlines'] = [{'en': q['name_en'], 'ctx': q.get('group_en', '')} for q in qls.get('questlines', [])]
T['endings'] = [{'en': b['text'], 'ctx': ''} for b in endings if b['k'] == 'h' and b['level'] == 2]

SKIP_TYPES = {'tip', 'warn', 'save', 'ending', 'other'}
TYPE_PREFIX = re.compile(r'^(?:#[\d &#]+[–-]\s*)?(?:[A-Z][\w ]{1,25}?:\s*)?')


def names_from_head(h):
    h = st(h)
    h = re.sub(r'^#[\d &#]+[–-]\s*', '', h)
    h = re.sub(r'\s*[–-]\s*MISSABLE.*$', '', h, flags=re.I)
    parts = re.split(r'\s+\+\s+|\s+/\s+|,\s+(?=[A-Z])', h)
    out = []
    for p in parts:
        p = re.sub(r'^[A-Z][\w ]{1,25}?:\s*', '', p.strip())       # "Weapon: X" -> "X"
        p = re.sub(r'\s*\((?:[^()]*)\)\s*$', '', p).strip()        # trailing "(Type)"
        if 2 < len(p) < 60:
            out.append(p)
    return out


for tag in sorted({t for _, it in items for t in it['tags']} - SKIP_TYPES):
    seen = OrderedDict()
    for a, it in items:
        if tag in it['tags']:
            for n in names_from_head(it['head_en']):
                seen.setdefault(n, f'[{a}] ' + st(it['body_en'])[:160])
    T[f'type:{tag}'] = [{'en': k, 'ctx': v} for k, v in seen.items()]
for key, v in bt.items():
    T[f'collection:{key}'] = [{'en': e['label_en'], 'ctx': (e['area_en'] + ' | ' + st(e['body_en'])[:140])} for e in v.get('entries', [])]

alltext = ' \n '.join(t for _, t in corpus) + ' \n ' + ' '.join(st(b.get('html', '')) for b in endings if b['k'] == 'p')
dlg = Counter(m.group(1).strip() for m in re.finditer(r'[“"]([^”"\n]{2,45})[”"]', alltext))
T['dialogue'] = [{'en': k, 'ctx': ctx(k)} for k, n in dlg.most_common() if not re.match(r'^[a-z]', k) or n > 1][:150]

known = {e['en'] for cat in T.values() for e in cat}
cap = Counter()
STOP = set('The From After Then Go In At On To If This Can Use Take Follow You It He She They Must Before When Directly Defeat Once Keep '
           'Inside Turn Note Climb Enter Talk Backtrack Return Exhaust Pick Head Continue Next Region Step Look Make Drop Open Interact'.split())
for m in re.finditer(r"\b([A-Z][a-z’'\-]+(?:\s+(?:of|the|in|and|–|&)?\s*[A-Z][a-z’'\-]+)+)", alltext):
    p = m.group(1).strip()
    if p.split()[0] not in STOP and p not in known:
        cap[p] += 1
T['misc'] = [{'en': k, 'ctx': ctx(k)} for k, n in cap.most_common(200) if n >= 2]

os.makedirs(os.path.join(W, 'glossary'), exist_ok=True)
json.dump(T, open(os.path.join(W, 'glossary', 'terms_en.json'), 'w'), ensure_ascii=False, indent=1)
for k, v in T.items():
    print(f'{k:28s} {len(v)}')
print('total', sum(len(v) for v in T.values()))
