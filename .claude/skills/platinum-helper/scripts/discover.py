"""Stage 1: download the two hub pages and print their outline so you can write game.json.

usage: python3 -I discover.py <work_dir> <trophy_guide_url> <collectibles_guide_url>

Writes:
  <work>/raw/<slug>.html            the two hub pages
  <work>/hub_outline.json           headings + list items (text, url) of both hubs, in page order
  <work>/urls_all.txt               every same-game PowerPyx link found in either hub body (deduped, no anchors)
Then run:  bash fetch.sh <work>/urls_all.txt <work>/raw   to download all sub-pages.
"""
import sys, os, re, json, subprocess, html as H

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ppx

W, TURL, CURL = sys.argv[1], sys.argv[2], sys.argv[3]
RAW = os.path.join(W, 'raw')
os.makedirs(RAW, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))


def slug_of(u):
    return u.split('#')[0].rstrip('/').split('/')[-1]


tmp = os.path.join(W, 'hub_urls.txt')
open(tmp, 'w').write(TURL + '\n' + CURL + '\n')
subprocess.run(['bash', os.path.join(HERE, 'fetch.sh'), tmp, RAW], check=True)

# game slug prefix = common prefix of the two hub slugs up to a dash
a, b = slug_of(TURL), slug_of(CURL)
pre = os.path.commonprefix([a, b])
pre = pre[:pre.rfind('-') + 1] if '-' in pre else pre
outline = {'game_prefix': pre, 'hubs': {}}
allurls = []
for name, url in (('trophy_guide', TURL), ('collectibles_guide', CURL)):
    raw = open(os.path.join(RAW, slug_of(url) + '.html'), encoding='utf-8').read()
    body = ppx.body_of(raw)
    items = []
    for m in re.finditer(r'<(h[1-4])[^>]*>(.*?)</\1>|<li>(.*?)</li>', body, re.S):
        if m.group(1):
            items.append({'h': m.group(1), 'text': H.unescape(re.sub(r'<[^>]+>', '', m.group(2))).strip()})
        else:
            li = m.group(3)
            link = re.search(r'href="([^"]+)"', li)
            items.append({'li': H.unescape(re.sub(r'<[^>]+>', '', li)).replace('\xa0', ' ').strip()[:120],
                          'url': link.group(1) if link else ''})
    outline['hubs'][name] = {'url': url, 'items': items}
    for u in re.findall(r'href="(https://www\.powerpyx\.com/[^"#]+)', body):
        if '/wp-content/' in u or re.search(r'\.(jpe?g|png|gif|webp|pdf)$', u, re.I):
            continue  # images and uploads, not guide pages
        if slug_of(u).startswith(pre) and u not in allurls and slug_of(u) not in (a, b):
            allurls.append(u)
json.dump(outline, open(os.path.join(W, 'hub_outline.json'), 'w'), ensure_ascii=False, indent=1)
open(os.path.join(W, 'urls_all.txt'), 'w').write('\n'.join(allurls) + '\n')

for name, hub in outline['hubs'].items():
    print(f'===== {name}: {hub["url"]}')
    for it in hub['items']:
        if 'h' in it:
            print(f'  [{it["h"]}] {it["text"]}')
        elif it['url'] and slug_of(it['url']).startswith(pre):
            print(f'      - {it["li"][:70]}  ->  {slug_of(it["url"])}{"#" + it["url"].split("#")[1] if "#" in it["url"] else ""}')
print(f'\n{len(allurls)} sub-page URLs -> {os.path.join(W, "urls_all.txt")}  (game prefix "{pre}")')
