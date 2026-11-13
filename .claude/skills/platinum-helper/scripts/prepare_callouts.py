"""Trophy-guide steps into the route (sample_ui/8.png): save backups / reloads, ending branches, points of no return,
"do X before Y" warnings and story trophies, placed where they happen.

usage: python3 -I prepare_callouts.py <work> <built html>
Writes <work>/tr_in/callouts.json (roadmap, endings guide and trophy notes in English + the page's Chinese) and
<work>/tr_in/callouts_route.tsv (the route in order: every item with its id, step, kind and a text excerpt).
An agent with references/callouts-brief.md writes <work>/tr_out/callouts.json; assemble.py inserts it.
"""
import json, os, re, sys

W, HTML = sys.argv[1], sys.argv[2]


def st(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or '')).strip()


def paras(h):  # html -> text with paragraph breaks kept
    h = re.sub(r'</(p|li|h\d|div)>|<br\s*/?>', '\n', h or '')
    return '\n'.join(x for x in (st(l) for l in h.split('\n')) if x)


h = open(HTML, encoding='utf-8').read()
D = json.loads(re.search(r'<script id="appdata" type="application/json">(.*?)</script>', h, re.S).group(1).replace('<\\/', '</'))
cfg = json.load(open(os.path.join(W, 'game.json'), encoding='utf-8'))

route = ['n\tid\tregion\tstep\tkind\ttype\tname_zh\tname_en\ttext_en']
n = 0
for r in D['regions']:
    for a in r['areas']:
        for s in a['sections']:
            for it in s['items']:
                kind = 'check' if it['check'] else (it.get('style') or 'note')
                if it.get('style') in ('warn', 'save') and it['check']:
                    kind = it['style'] + '+check'
                route.append('\t'.join(str(x) for x in (n, it['id'], st(r['short']['en']), st(a['title']['en']), kind, it['type'],
                                                       st(it['head']['zh']), st(it['head']['en']), st(it['body']['en'])[:220])))
                n += 1

endings = [{'title_en': st(e['title']['en']), 'title_zh': st(e['title']['zh']), 'text_en': paras(e['html']['en']),
            'text_zh': paras(e['html']['zh'])} for e in D.get('endings', [])]
if D.get('endingsAll'):
    endings.insert(0, {'title_en': st(D['endingsAll']['title']['en']), 'title_zh': st(D['endingsAll']['title']['zh']),
                       'text_en': paras(D['endingsAll']['html']['en']), 'text_zh': paras(D['endingsAll']['html']['zh'])})
trophies = [{'name_en': t['name']['en'], 'name_zh': t['name']['zh'], 'desc_en': t['desc']['en'], 'cat': t.get('cat'),
             'missable': bool(t.get('miss')), 'linked_items': t.get('items', []), 'collection': bool(t.get('col')),
             'note_en': st(t['detail']['en']), 'note_zh': st(t['detail']['zh'])} for t in D['trophies']]
eb = os.path.join(W, 'data_en', 'endings_blocks.json')  # the whole endings guide too: intro notices ("2 playthroughs …")
guide = '\n'.join(x for x in ((b.get('text') or '') + ' ' + st(b.get('html', '')) + ' ' + ' '.join(st(i) for i in b.get('items', []))
                              for b in (json.load(open(eb, encoding='utf-8')) if os.path.exists(eb) else [])) if x.strip())
out = {'game': cfg['game'], 'roadmap_en': paras(D['roadmap']['html']['en']), 'roadmap_zh': paras(D['roadmap']['html']['zh']),
       'endings': endings, 'endings_guide_en': guide, 'trophies': trophies}
os.makedirs(os.path.join(W, 'tr_in'), exist_ok=True)
json.dump(out, open(os.path.join(W, 'tr_in', 'callouts.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(os.path.join(W, 'tr_in', 'callouts_route.tsv'), 'w', encoding='utf-8').write('\n'.join(route) + '\n')
print('route items', n, '| endings sections', len(endings), '| trophies', len(trophies),
      '| tr_in/callouts.json', os.path.getsize(os.path.join(W, 'tr_in', 'callouts.json')) // 1024, 'KB')
