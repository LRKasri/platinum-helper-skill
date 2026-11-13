"""奖杯前置 (trophy prerequisites): collect the guide text that can say "you need X to get Y" and the page's checkboxes,
so an agent (references/gates-brief.md) can list skippable prerequisites with the quoting sentence.

usage: python3 -I prepare_gates.py <work> <built html>
Writes <work>/tr_in/gates.json (sources) and <work>/tr_in/gates_items.tsv (every checkbox: id, type, names, place,
trophy chips). The agent writes <work>/tr_out/gates.json + <work>/gates_review.md; re-run assemble.py (items get a
「前置 · 《奖杯》」 chip, count as 奖杯相关 and are listed on the trophy card; "level": "self" entries get the gold chip).
"""
import json, os, re, sys

W, HTML = sys.argv[1], sys.argv[2]


def J(*p, default=None):
    f = os.path.join(W, *p)
    return json.load(open(f, encoding='utf-8')) if os.path.exists(f) else default


def st(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or '')).strip()


h = open(HTML, encoding='utf-8').read()
D = json.loads(re.search(r'<script id="appdata" type="application/json">(.*?)</script>', h, re.S).group(1).replace('<\\/', '</'))
TRO = {t['id']: t for t in D['trophies']}
cfg = J('game.json')
nonplat = set(cfg.get('non_platinum_types', []))

rows, trophy_items = [], []
for r in D['regions']:
    for a in r['areas']:
        for s in a['sections']:
            for it in s['items']:
                if not it['check']:
                    continue
                tn = [TRO[t]['name']['en'] for t in it.get('tro', []) if t in TRO]
                rows.append('\t'.join([it['id'], it['type'], st(it['head']['en']), st(it['head']['zh']),
                                       st(r['short']['en']) + ' / ' + st(a['title']['en']), '; '.join(tn),
                                       'optional' if it.get('opt') else '']))
                if tn:
                    trophy_items.append({'id': it['id'], 'trophies': tn, 'name_en': st(it['head']['en']), 'text_en': st(it['body']['en'])})

trophies = [{'name_en': t['name_en'], 'name_zh': next((x['name']['zh'] for x in D['trophies'] if x['name']['en'] == t['name_en']), ''),
             'desc_en': t['desc_en'], 'note_en': st(t['detail_en'])} for t in J('data_en', 'trophies.json', default=[])]
col_trophy = {c['type']: c.get('trophy') for c in cfg.get('collections', [])}
bytype = []
for k, v in (J('data_en', 'bytype.json', default={}) or {}).items():
    for n, e in enumerate(v.get('entries', []), 1):
        bytype.append({'src': f'bytype:{k}-{n}', 'trophy': col_trophy.get(k), 'label_en': e['label_en'], 'text_en': st(e.get('body_en', ''))})
road = ' '.join(st(b.get('html', '')) + ' ' + ' '.join(st(x) for x in b.get('items', [])) for b in J('data_en', 'roadmap_blocks.json', default=[]))
ql = J('data_en', 'questlines.json', default={}) or {}
quests = []
for q in ql.get('questlines', []):
    quests.append({'name_en': q.get('name_en', ''), 'text_en': ' '.join(st(b.get('html', '')) + ' ' + ' '.join(st(x) for x in b.get('items', []))
                                                                    for b in q.get("blocks", []))})

os.makedirs(os.path.join(W, 'tr_in'), exist_ok=True)
json.dump({'game': cfg['game'], 'non_platinum_types': sorted(nonplat), 'trophies': trophies, 'roadmap_en': road,
           'bytype_entries': bytype, 'trophy_items': trophy_items, 'questlines': quests},
          open(os.path.join(W, 'tr_in', 'gates.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(os.path.join(W, 'tr_in', 'gates_items.tsv'), 'w', encoding='utf-8').write(
    'id\ttype\tname_en\tname_zh\tregion / step\ttrophies already linked\toptional\n' + '\n'.join(rows) + '\n')
print('checkboxes', len(rows), '| trophy items', len(trophy_items), '| by-type entries', len(bytype), '| questlines', len(quests),
      '| tr_in/gates.json', os.path.getsize(os.path.join(W, 'tr_in', 'gates.json')) // 1024, 'KB')
