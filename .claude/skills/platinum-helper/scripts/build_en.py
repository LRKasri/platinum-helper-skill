"""Stage 2a: parse the route (by-area) pages into data_en/areas.json, driven by <work>/game.json.

usage: python3 -I build_en.py <work_dir>

Output structure:
  [ {id, title_en, note_en, areas: [ {id, url, title_en, intro_en, reach_en,
       sections: [ {title_en, items: [ {id, kind: item|note, tags[], head_en, body_en, imgs[], videos[], red} ]} ]} ]} ]

An "area" is one numbered route step in the UI. game.json `step_mode` decides how steps are cut:
  page        one step per page (Wuchang: one page per shrine)
  checkpoint  split a page at every item tagged `checkpoint_type` (e.g. each Bell / bonfire starts a step)
  section     one step per <h2>/<h3> section of the page
In checkpoint mode a heading of level <= `split_heading_level` (default 2, 0 = never) also starts a new step, so
"Second Visit" / "After Getting Double Jump" parts don't hide inside the previous checkpoint's step.
Guides that give every item its own heading (<h3>Hydra / Box #4</h3> + paragraphs) need `item_heading_level: 3`.
Prose walkthroughs (Sekiro: sections of paragraphs with item names in bold) need `paragraph_items: true`: every
paragraph that names something in bold becomes a checkable item titled by those bold names; the others are tips.
Item ids are `<page id>-<n>` (n counts items within the page), so they stay stable whatever the step mode.
"""
import sys, os, re, json, html as H
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ppx

W = sys.argv[1]
cfg = json.load(open(os.path.join(W, 'game.json'), encoding='utf-8'))
RAW = os.path.join(W, 'raw')
OUT = os.path.join(W, 'data_en')
os.makedirs(OUT, exist_ok=True)

RULES = [(t, re.compile(rx)) for t, rx in cfg['type_rules']]
NOTE_TAGS = set(cfg.get('note_tags', ['warn', 'save', 'ending']))
SKIP_P = re.compile(cfg.get('skip_paragraph_regex',
                            r'^(NEXT:|For an overview|Collectibles Overview|Everything here can be obtained|Collectible Guide$|«|Share$)'), re.I)
REACH_P = re.compile(cfg.get('reach_paragraph_regex', r'^How to reach'), re.I)
STRIP = cfg.get('slug_strip', [])
STEP_MODE = cfg.get('step_mode', 'page')
CHECKPOINT = cfg.get('checkpoint_type', '')
ITEM_LEVEL = cfg.get('item_heading_level')
SPLIT_LEVEL = int(cfg.get('split_heading_level', 2))
PARA_ITEMS = bool(cfg.get('paragraph_items'))
NOTE_HEAD = re.compile(cfg['note_head_regex']) if cfg.get('note_head_regex') else None


def bold_names(html):
    out = []
    for m in re.findall(r'<b>(.*?)</b>', html, re.S):
        t = re.sub(r'\s+', ' ', st(m)).strip().rstrip(':.').strip()
        if 1 < len(t) <= 60 and t not in out:
            out.append(t)
    return out
CHECK_RX = [re.compile(rx) for t, rx in cfg['type_rules'] if t == CHECKPOINT]


def slug_of(u):
    return u.split('#')[0].rstrip('/').split('/')[-1]


def short_id(slug):
    s = slug
    for x in STRIP:
        s = s.replace(x, '')
    return s.strip('-') or slug


def st(s):
    return H.unescape(re.sub(r'<[^>]+>', '', s or '')).replace('\xa0', ' ').strip()


def classify(text):
    tags = [t for t, rx in RULES if rx.search(text)]
    return tags or ['other']


def load(url):
    return open(os.path.join(RAW, slug_of(url) + '.html'), encoding='utf-8').read()


def parse_page(url, anchor_titles=None):
    """-> dict(intro_en, reach_en, sections=[{title_en, items}]) ; items get ids later"""
    bl = ppx.blocks(ppx.body_of(load(url)))
    if ITEM_LEVEL:
        bl = ppx.promote_headings(bl, int(ITEM_LEVEL))
    page = {'intro_en': '', 'reach_en': '', 'sections': []}
    sec, cur = None, None

    def new_section(title, level=2):
        nonlocal sec
        sec = {'title_en': title, 'items': [], 'level': level}
        page['sections'].append(sec)

    def add(item):
        nonlocal cur
        if sec is None:
            new_section('')
        sec['items'].append(item)
        cur = item

    for b in bl:
        if b['k'] == 'h':
            if b['level'] >= 2 and not re.match(r'(Comments|Leave a Reply|Latest|Recent)', b['text']):
                new_section(b['text'], b['level'])
                cur = None
            continue
        if b['k'] == 'p':
            txt = st(b['html'])
            if not txt and not b['imgs'] and not b['videos']:
                continue
            if SKIP_P.match(txt):
                continue
            if REACH_P.match(txt):
                page['reach_en'] = b['html']
                continue
            if not page['intro_en'] and sec is None and not b.get('lead'):
                page['intro_en'] = b['html']
                continue
            if b.get('lead'):
                tags = classify(st(b['lead']))
                item = {'kind': 'item', 'tags': tags, 'head_en': b['lead'], 'body_en': b['rest'],
                        'imgs': list(b['imgs']), 'videos': list(b['videos']), 'red': b.get('red', False)}
                if (tags[0] in NOTE_TAGS and not b['rest']) or (NOTE_HEAD and NOTE_HEAD.search(st(b['lead']))):
                    item['kind'] = 'note'
                    if NOTE_HEAD and NOTE_HEAD.search(st(b['lead'])):
                        item['tags'] = ['tip']
                add(item)
                continue
            if not txt and cur is not None:  # image-only / video-only paragraph
                cur['imgs'] += b['imgs']
                cur['videos'] += b['videos']
                continue
            if PARA_ITEMS and not b.get('em_only'):
                names = bold_names(b['html'])
                if names:
                    add({'kind': 'item', 'tags': classify(' · '.join(names)), 'head_en': ' · '.join(names[:6]),
                         'body_en': b['html'], 'imgs': list(b['imgs']), 'videos': list(b['videos']), 'red': b.get('red', False)})
                else:
                    add({'kind': 'note', 'tags': ['tip'], 'head_en': '', 'body_en': b['html'],
                         'imgs': list(b['imgs']), 'videos': list(b['videos']), 'red': False})
                continue
            if b.get('em_only') or (b.get('red') and len(txt) < 400):
                add({'kind': 'note', 'tags': ['warn' if b.get('red') else 'tip'], 'head_en': '', 'body_en': b['html'],
                     'imgs': list(b['imgs']), 'videos': list(b['videos']), 'red': b.get('red', False)})
                continue
            if cur is not None:
                cur['body_en'] += ('<br>' if cur['body_en'] else '') + b['html']
                cur['imgs'] += b['imgs']
                cur['videos'] += b['videos']
            else:
                add({'kind': 'note', 'tags': ['tip'], 'head_en': '', 'body_en': b['html'],
                     'imgs': list(b['imgs']), 'videos': list(b['videos']), 'red': False})
        elif b['k'] == 'ul':
            joined = ''.join(b['items'])
            if sec is None and ('Collectible Guide' in joined or 'Collectibles Guide' in joined):
                continue
            ul = '<ul>' + ''.join(f'<li>{x}</li>' for x in b['items']) + '</ul>'
            if sec is None and cur is None:
                page['intro_en'] += ul  # stats list at page top ("Bells: 23" …)
                continue
            if cur is not None:
                cur['body_en'] += ul
                cur['imgs'] += b['imgs']
                cur['videos'] += b['videos']
            else:
                add({'kind': 'note', 'tags': ['tip'], 'head_en': '', 'body_en': ul, 'imgs': b['imgs'], 'videos': b['videos'], 'red': False})
        elif b['k'] == 'img' and cur is not None:
            cur['imgs'] += b['imgs']
        elif b['k'] == 'video' and cur is not None:
            cur['videos'].append(b['src'])
    page['sections'] = [s for s in page['sections'] if s['items']]
    return page


def checkpoint_title(item):
    h = st(item['head_en'])
    parts = [x.strip() for x in re.split(r'\s+/\s+', h)]
    if len(parts) > 1:  # "Abaddon / Weapon Core #1 / Camp #4" -> the part that is the checkpoint
        h = next((x for x in parts if any(rx.search(x) for rx in CHECK_RX)), parts[-1])
    h = re.sub(r'^#\s*\d+\s*[–-]\s*', '', h)
    m = re.search(r'\(([^)]+)\)', h)  # "Bell (The Beginning)" -> "The Beginning"
    return m.group(1) if m else re.sub(r'^[\w ]+:\s*', '', h)


regions_out = []
seen_pages = {}
for ri, r in enumerate(cfg['regions']):
    reg = {'id': r.get('id', f'r{ri + 1}'), 'title_en': r['title_en'], 'note_en': r.get('note_en', ''), 'areas': []}
    for pg in r['pages']:
        url = pg['url'] if isinstance(pg, dict) else pg
        title = pg.get('title_en', '') if isinstance(pg, dict) else ''
        slug = slug_of(url)
        if slug in seen_pages:  # same page listed twice (anchor) -> just extend its title
            if title:
                seen_pages[slug]['title_en'] += ' & ' + title
            continue
        page = parse_page(url)
        pid = short_id(slug)
        n = 0
        for s in page['sections']:
            for it in s['items']:
                n += 1
                it['id'] = f'{pid}-{n}'
        title = title or st(re.sub(r'\s*Collectible Locations.*$', '', slug.replace('-', ' ').title()))
        if STEP_MODE == 'page':
            secs = [{'title_en': x['title_en'], 'items': x['items']} for x in page['sections']]
            area = {'id': pid, 'url': url, 'title_en': title, 'intro_en': page['intro_en'], 'reach_en': page['reach_en'], 'sections': secs}
            reg['areas'].append(area)
            seen_pages[slug] = area
            continue
        # checkpoint / section modes: cut the page into several steps
        steps, cur = [], None
        k = 0
        for s in page['sections']:
            heading_split = (STEP_MODE == 'checkpoint' and SPLIT_LEVEL and s['title_en'] and s.get('level', 2) <= SPLIT_LEVEL
                             and cur is not None and any(x['items'] for x in cur['sections']))
            if STEP_MODE == 'section' or cur is None or heading_split:
                k += 1
                cur = {'id': f'{pid}-s{k}', 'url': url, 'title_en': s['title_en'] or title, 'intro_en': page['intro_en'] if k == 1 else '',
                       'reach_en': page['reach_en'] if k == 1 else '', 'sections': [{'title_en': s['title_en'], 'items': []}]}
                steps.append(cur)
            elif s['title_en']:
                cur['sections'].append({'title_en': s['title_en'], 'items': []})
            for it in s['items']:
                if STEP_MODE == 'checkpoint' and CHECKPOINT in it['tags'] and any(x['items'] for x in cur['sections']):
                    k += 1
                    cur = {'id': f'{pid}-s{k}', 'url': url, 'title_en': checkpoint_title(it), 'intro_en': '', 'reach_en': '',
                           'sections': [{'title_en': '', 'items': []}]}
                    steps.append(cur)
                elif STEP_MODE == 'checkpoint' and CHECKPOINT in it['tags'] and not any(x['items'] for x in cur['sections']):
                    cp = checkpoint_title(it)  # step opened by a heading and its first item is a checkpoint
                    cur['title_en'] = cp if cur['title_en'] in (title, '') or len(steps) == 1 else f"{cur['title_en']} · {cp}"
                cur['sections'][-1]['items'].append(it)
        for stp in steps:
            stp['sections'] = [{'title_en': x['title_en'], 'items': x['items']} for x in stp['sections'] if x['items']]
        reg['areas'] += [x for x in steps if x['sections']]
        seen_pages[slug] = steps[0] if steps else {}
    regions_out.append(reg)

json.dump(regions_out, open(os.path.join(OUT, 'areas.json'), 'w'), ensure_ascii=False, indent=1)
tot = Counter()
for reg in regions_out:
    c = Counter(t for a in reg['areas'] for s in a['sections'] for it in s['items'] for t in it['tags'])
    tot.update(c)
    n = sum(len(s['items']) for a in reg['areas'] for s in a['sections'])
    print(f'{reg["id"]} {reg["title_en"]}: {len(reg["areas"])} steps, {n} items, {dict(c.most_common(12))}')
print('TOTAL tags:', dict(tot.most_common()))
