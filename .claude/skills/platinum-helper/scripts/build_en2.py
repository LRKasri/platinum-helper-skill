"""Stage 2b: parse trophy guide, by-type collectible lists and optional boss / questline / endings guides.

usage: python3 -I build_en2.py <work_dir>

Writes data_en/: trophies.json, roadmap_blocks.json, hub_intro_blocks.json, bytype.json,
                 bosses.json (if pages.bosses), questlines.json (if pages.questlines), endings_blocks.json (if pages.endings)
"""
import sys, os, re, json, html as H

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ppx

W = sys.argv[1]
cfg = json.load(open(os.path.join(W, 'game.json'), encoding='utf-8'))
RAW = os.path.join(W, 'raw')
OUT = os.path.join(W, 'data_en')
os.makedirs(OUT, exist_ok=True)
REGION_HEAD = re.compile(cfg.get('region_heading_regex', r'^(Region \d+|Chapter \d+|Act \d+)\b'))


def slug_of(u):
    return u.split('#')[0].rstrip('/').split('/')[-1]


def load(url):
    return open(os.path.join(RAW, slug_of(url) + '.html'), encoding='utf-8').read()


def st(s):
    return H.unescape(re.sub(r'<[^>]+>', '', s or '')).replace('\xa0', ' ').strip()


def dump(name, obj):
    json.dump(obj, open(os.path.join(OUT, name), 'w'), ensure_ascii=False, indent=1)


# ---------------- trophies ----------------
raw = load(cfg['sources']['trophy_guide'])
body = ppx.body_of(raw)
cut = body.find('Trophy Guide</h2>')
if cut < 0:
    cut = body.find('<table')
bl = ppx.blocks(body[cut:])


def grade_of(attrs_list):
    for a in attrs_list:
        for k in ('alt', 'title'):
            v = (a.get(k) or '').lower()
            for g in ('platinum', 'gold', 'silver', 'bronze'):
                if v.startswith(g):
                    return g
        src = a.get('src', '').lower()
        for g in ('platinum', 'gold', 'silver', 'bronze'):
            if f'-{g}.' in src or f'_{g}.' in src or f'/{g}.' in src:
                return g
    return ''


trophies = []
for b in bl:
    if b['k'] != 'table':
        continue
    rows, k = b['rows'], 0
    while k < len(rows):
        r = rows[k]
        if len(r) >= 3:
            parts = re.split(r'<br>', r[1]['html'], 1)
            detail = rows[k + 1][0] if k + 1 < len(rows) and len(rows[k + 1]) == 1 else None
            trophies.append({'name_en': st(parts[0]), 'desc_en': st(parts[1]) if len(parts) > 1 else '',
                             'grade': grade_of(r[2]['raw_imgs']) or 'bronze',
                             'detail_en': detail['html'] if detail else '', 'videos': detail['videos'] if detail else []})
            k += 2 if detail else 1
        else:
            k += 1
dump('trophies.json', trophies)
dump('roadmap_blocks.json', ppx.blocks(body[:cut]))
print('trophies', len(trophies), {g: sum(1 for t in trophies if t['grade'] == g) for g in ('platinum', 'gold', 'silver', 'bronze')})

# ---------------- hub intro (collectibles guide text before the first heading) ----------------
hub = ppx.blocks(ppx.body_of(load(cfg['sources']['collectibles_guide'])))
intro = []
for b in hub:
    if b['k'] == 'h':
        break
    intro.append(b)
dump('hub_intro_blocks.json', intro)


# ---------------- by-type lists ----------------
def parse_bytype(url):
    """Three layouts are handled:
    numbered  <p><b>Label #N: Name</b><br>location…</p> under area headings   (most PowerPyx 'All X Locations' pages)
    dashlist  list items / paragraphs 'Name – how to reach' under 'Region N' headings (e.g. All Shrine Locations)
    headed    <h2>Riddle #N</h2> + paragraphs (one heading per entry; a following non-numbered sub-heading
              such as <h3>Eidos 7</h3> becomes the entry's area). Other layouts (one h2 per entry without '#N',
              a list repeated per location) give 0 or duplicate entries: use source: tag or dedupe instead.
    """
    bl = ppx.blocks(ppx.body_of(load(url)))
    entries, area, intro, cur = [], '', [], None
    for b in bl:  # "Prayer Bead #1: Area<br>text" without bold -> treat the first line as the lead
        if b['k'] == 'p' and not b.get('lead') and '<br>' in b['html']:
            first, rest = b['html'].split('<br>', 1)
            if re.search(r'#\s*\d+', st(first)) and len(st(first)) < 120:
                b['lead'], b['rest'] = first, rest.strip()
    numbered = [b for b in bl if b['k'] == 'p' and b.get('lead') and re.search(r'#\s*\d+', st(b['lead']))]
    if numbered:
        for b in bl:
            if b['k'] == 'h':
                area, cur = b['text'], None
                continue
            if b['k'] == 'p' and b.get('lead') and re.search(r'#\s*\d+', st(b['lead'])):
                cur = {'label_en': st(b['lead']), 'area_en': area, 'body_en': b['rest'], 'imgs': list(b['imgs']), 'videos': list(b['videos'])}
                entries.append(cur)
            elif b['k'] == 'p' and not entries:
                intro.append(b['html'])
            elif cur is not None and b['k'] in ('p', 'ul'):
                add = b['html'] if b['k'] == 'p' else '<ul>' + ''.join(f'<li>{x}</li>' for x in b['items']) + '</ul>'
                cur['body_en'] += ('<br>' if b['k'] == 'p' and cur['body_en'] else '') + add
                cur['imgs'] += b.get('imgs', [])
                cur['videos'] += b.get('videos', [])
            elif cur is not None and b['k'] == 'img':
                cur['imgs'] += b['imgs']
            elif cur is not None and b['k'] == 'video':
                cur['videos'].append(b['src'])
        return 'numbered', intro, entries
    NUMH = re.compile(r'#\s*\d+|^[A-Z][\w’\' ]{0,30}?\s\d+\s*[–-]\s')  # "Boss #3 – X", "Ninjutsu 2 – Puppeteer"
    headed = [b for b in bl if b['k'] == 'h' and NUMH.search(b['text'])]
    if headed:
        for b in bl:
            if b['k'] == 'h':
                if NUMH.search(b['text']):
                    cur = {'label_en': b['text'], 'area_en': '', 'body_en': '', 'imgs': [], 'videos': []}
                    entries.append(cur)
                elif cur is not None and not cur['area_en'] and not cur['body_en'] and b['level'] > 2:
                    cur['area_en'] = b['text']  # <h2>Can #1 – X</h2><h3>Eidos 7</h3>
                else:
                    cur = None
                continue
            if cur is not None and b['k'] in ('img', 'video'):
                if b['k'] == 'img':
                    cur['imgs'] += b['imgs']
                else:
                    cur['videos'].append(b['src'])
                continue
            if cur is None:
                if b['k'] == 'p' and not entries:
                    intro.append(b['html'])
                continue
            if b['k'] == 'p':
                cur['imgs'] += b.get('imgs', [])
                cur['videos'] += b.get('videos', [])
                if not st(b['html']):
                    continue
                if not cur['area_en'] and re.match(r'^[A-Z][\w’\' .]+\s+[–-]\s+[A-Z]', st(b['html'])) and len(st(b['html'])) < 80:
                    cur['area_en'] = st(b['html'])
                else:
                    cur['body_en'] += ('<br>' if cur['body_en'] else '') + b['html']
            elif b['k'] == 'ul':
                cur['body_en'] += '<ul>' + ''.join(f'<li>{x}</li>' for x in b['items']) + '</ul>'
        return 'headed', intro, entries
    for b in bl:  # dashlist
        if b['k'] == 'h':
            area = b['text']
            continue
        items = b['items'] if b['k'] == 'ul' else ([b['html']] if b['k'] == 'p' else [])
        for x in items:
            m = re.match(r'^(?:\d+\.\s*)?([A-Z][^–]{1,50}?)\s+–\s+(.*)', st(x))
            if m and (REGION_HEAD.match(area) or area):
                entries.append({'label_en': m.group(1).strip(), 'area_en': area, 'body_en': H.escape(m.group(2)), 'imgs': [], 'videos': []})
            elif not entries and b['k'] == 'p':
                intro.append(b['html'])
    return 'dashlist', intro, entries


bytype = {}
for c in cfg.get('collections', []):
    if c.get('source') != 'bytype':
        continue
    fmt, intro, entries = parse_bytype(c['url'])
    bytype[c['type']] = {'url': c['url'], 'format': fmt, 'intro_en': intro, 'entries': entries}
    print(f'bytype {c["type"]}: {fmt}, {len(entries)} entries', [e['label_en'][:30] for e in entries[:2]])
dump('bytype.json', bytype)


# ---------------- optional guides ----------------
def sections_by_h2(url):
    bl = ppx.blocks(ppx.body_of(load(url)))
    intro, secs, cur = [], [], None
    for b in bl:
        if b['k'] == 'h' and b['level'] == 2:
            cur = {'name_en': b['text'], 'id': b.get('id', ''), 'blocks': []}
            secs.append(cur)
        elif cur is not None:
            cur['blocks'].append(b)
        else:
            intro.append(b)
    return intro, secs


pages = cfg.get('pages', {})
if pages.get('bosses'):
    _, bosses = sections_by_h2(pages['bosses'])
    dump('bosses.json', bosses)
    print('bosses', len(bosses))
if pages.get('questlines'):
    intro, secs = sections_by_h2(pages['questlines'])
    qls, group = [], ''
    for s in secs:
        if re.search(r'(Questlines?|Quests|Tales).*(needed|Trophy|Trophies|Optional|Required|Missable)', s['name_en'], re.I):
            group = s['name_en']  # a group heading such as "NPC Questlines needed for Trophies"
            continue
        s['group_en'] = group
        qls.append(s)
    dump('questlines.json', {'intro': intro, 'questlines': qls})
    print('questlines', len(qls), [q['name_en'][:24] for q in qls][:20])
if pages.get('endings'):
    dump('endings_blocks.json', ppx.blocks(ppx.body_of(load(pages['endings']))))
    print('endings blocks saved')
