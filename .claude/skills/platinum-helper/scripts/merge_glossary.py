"""Merge glossary/seed_zh.json + glossary/zh_*.json -> glossary/glossary_merged.json"""
import sys, os, json, glob, re
S = sys.argv[1]
G = os.path.join(S, 'glossary')
seed = json.load(open(os.path.join(G, 'seed_zh.json')))
flat, conf, bycat = {}, {}, {}
RANK = {'official': 3, 'likely': 2, 'guess': 1}
def put(cat, en, zh, c):
    if not zh: return
    bycat.setdefault(cat, {})[en] = zh
    if en not in flat or RANK.get(c, 0) > RANK.get(conf.get(en), 0):
        flat[en] = zh; conf[en] = c
for en, zh in seed['trophies'].items():
    put('trophies', en, zh, 'official')
for en, zh in seed.get('known_terms', {}).items():
    put('known', en, re.sub(r'\s*\(likely\)', '', zh), 'likely' if 'likely' in zh else 'official')
for f in sorted(glob.glob(os.path.join(G, 'zh_*.json'))):
    d = json.load(open(f))
    for cat, m in d.items():
        if not isinstance(m, dict): continue
        for en, v in m.items():
            if isinstance(v, dict):
                put(cat, en, v.get('zh', ''), v.get('conf', 'guess'))
                if v.get('unlocks_zh'): bycat.setdefault('unlocks', {})[en] = v['unlocks_zh']
            elif isinstance(v, str):
                put(cat, en, v, 'guess')
# normalized aliases: strip trailing '(…)' and ' / NPC…'
for en in list(flat):
    base = re.split(r'\s+/\s+', en)[0]
    base = re.sub(r'\s*\([^)]*\)\s*$', '', base).strip()
    if base and base != en and base not in flat:
        flat[base] = re.sub(r'（[^）]*）$', '', flat[en]); conf[base] = conf[en]
json.dump({'flat': flat, 'conf': conf, 'by_category': bycat}, open(os.path.join(G, 'glossary_merged.json'), 'w'), ensure_ascii=False, indent=1)
from collections import Counter
print(len(flat), 'terms', Counter(conf.values()))
