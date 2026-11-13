"""Stage 7a: automatic checks on the assembled page -> <work>/qa_report.json (+ printed summary)

usage: python3 -I qa_check.py <work_dir> <html>

Checks: missing translations, untranslated English left in Chinese fields, unbalanced tags,
empty Chinese titles, glossary consistency (an official term appears in English but its Chinese
name is absent from the Chinese text of the same item), collection sizes vs trophy counts, page size.
"""
import sys, os, re, json, html as H
from collections import Counter

W, HTML = sys.argv[1], sys.argv[2]
raw = open(HTML, encoding='utf-8').read()
D = json.loads(re.search(r'<script id="appdata" type="application/json">(.*?)</script>', raw, re.S).group(1).replace('<\\/', '</'))
rep = json.load(open(os.path.join(W, 'assemble_report.json'), encoding='utf-8')) if os.path.exists(os.path.join(W, 'assemble_report.json')) else {}
gpath = os.path.join(W, 'glossary', 'glossary_merged.json')
GM = json.load(open(gpath, encoding='utf-8')) if os.path.exists(gpath) else {'flat': {}, 'conf': {}}


def st(s):
    return H.unescape(re.sub(r'<[^>]+>', ' ', s or '')).replace('\xa0', ' ')


ENG = re.compile(r"[A-Za-z][A-Za-z’'\-]*(?:[ ,.:;!?–-]+[A-Za-z][A-Za-z’'\-]*){5,}")
issues = {'english_left': [], 'tag_mismatch': [], 'empty_zh_head': [], 'glossary_miss': []}
official = sorted(((en, zh) for en, zh in GM.get('flat', {}).items()
                   if GM.get('conf', {}).get(en) == 'official' and len(en) > 4 and zh and not re.search(r'[A-Za-z]', zh)), key=lambda x: -len(x[0]))
n_items = 0
EN_ONLY = (D.get('lang') or {}).get('bilingual') is False  # English-only page: no Chinese to check
for r in ([] if EN_ONLY else D['regions']):
    for a in r['areas']:
        for s in a['sections']:
            for it in s['items']:
                n_items += 1
                zh = st(it['head']['zh']) + ' ' + st(it['body']['zh'])
                en = st(it['head']['en']) + ' ' + st(it['body']['en'])
                if zh.strip() == en.strip() and en.strip():
                    continue  # untranslated entirely: reported via missing_unit
                for m in ENG.finditer(re.sub(r'[（(][^）)]*[）)]', '', zh)):
                    issues['english_left'].append((it['id'], m.group(0)[:70]))
                    break
                for tag in ('<b>', '<li>', '<span', '<t '):
                    a1 = (it['head']['en'] + it['body']['en']).count(tag)
                    b1 = (it['head']['zh'] + it['body']['zh']).count(tag)
                    if abs(a1 - b1) > 1:
                        issues['tag_mismatch'].append((it['id'], tag, a1, b1))
                        break
                if st(it['head']['en']).strip() and not st(it['head']['zh']).strip():
                    issues['empty_zh_head'].append(it['id'])
                masked = en
                for e, z in official:  # longest first; mask matches so 'Coral Bracelet' inside 'Black Coral Bracelet' is not re-checked
                    if ' ' not in e:
                        continue
                    rx = re.compile(r'(?<![\w])' + re.escape(e) + r'(?![\w])')
                    if not rx.search(masked):
                        continue
                    masked = rx.sub('\u2588', masked)
                    core = re.split(r'[·”」]', z)[-1].strip('“”「」 ')
                    if core and core not in zh:
                        issues['glossary_miss'].append((it['id'], e, z))
cols = {t['name']['en']: len(t.get('col', [])) for t in D['trophies'] if t.get('col')}
nums = {}
for t in D['trophies']:
    m = re.search(r'\b(\d+)\b', t['desc']['en'])
    if t.get('col') and m:
        nums[t['name']['en']] = (int(m.group(1)), len(t['col']))
summary = {
    'html_kb': len(raw) // 1024, 'items': n_items, 'trophies': len(D['trophies']), 'questlines': len(D['questlines']),
    'missing_translations': len(rep.get('missing_unit', [])), 'unlinked_collection_entries': len(rep.get('unlinked', [])),
    'english_left': len(issues['english_left']), 'tag_mismatch': len(issues['tag_mismatch']),
    'empty_zh_head': len(issues['empty_zh_head']), 'glossary_miss': len(issues['glossary_miss']),
    'collection_sizes': cols, 'trophy_count_vs_collection': {k: v for k, v in nums.items() if v[0] != v[1]},
    'trophy_categories': {c: sum(1 for t in D['trophies'] if t.get('cat') == c) for c in ('col', 'boss', 'ending', 'other', None)},
    'boss_trophies_without_items': [t['name']['en'] for t in D['trophies'] if t.get('cat') == 'boss' and not t.get('items')],
    'platinum_mode': D.get('mode'), 'optional_items': sum(1 for r in D['regions'] for a in r['areas'] for s in a['sections'] for it in s['items'] if it.get('opt')),
    'partial_collections': {t['name']['en']: f"need {t.get('need')} of {len(t['col'])}" for t in D['trophies'] if t.get('col') and (t.get('need') or 0) < len(t['col'])},
}
json.dump({'summary': summary, 'issues': issues, 'missing_unit': rep.get('missing_unit', [])[:200]},
          open(os.path.join(W, 'qa_report.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))
for k in ('english_left', 'tag_mismatch', 'glossary_miss'):
    for x in issues[k][:8]:
        print(f'  {k}: {x}')
print('details ->', os.path.join(W, 'qa_report.json'))
