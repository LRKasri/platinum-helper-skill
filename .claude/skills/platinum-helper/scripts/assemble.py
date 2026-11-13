"""Stage 6: assemble the final single-file HTML.

usage: python3 -I assemble.py <work_dir> <out_html> [--template <path>]

Reads  <work>/game.json, data_en/*, glossary/glossary_merged.json (optional), tr_out/*.json (optional),
       data_en/images.json (optional, from fetch_images.py), the template (default: ../assets/template.html)
Writes <out_html> and <work>/assemble_report.json (missing translations, unlinked collection entries, warnings).
Works with zero translations too (Chinese fields fall back to English) — handy for an early English preview.
"""
import sys, os, re, json, glob, base64, html as H

W, OUT_HTML = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = sys.argv[sys.argv.index('--template') + 1] if '--template' in sys.argv else os.path.join(HERE, '..', 'assets', 'template.html')
cfg = json.load(open(os.path.join(W, 'game.json'), encoding='utf-8'))


def J(*p, default=None):
    path = os.path.join(W, *p)
    if not os.path.exists(path):
        return default
    return json.load(open(path, encoding='utf-8'))


areas_en = J('data_en', 'areas.json')
bt = J('data_en', 'bytype.json', default={})
trophies_en = J('data_en', 'trophies.json', default=[])
ql_en = J('data_en', 'questlines.json', default={'intro': [], 'questlines': []})
bosses_en = J('data_en', 'bosses.json', default=[])
endings_en = J('data_en', 'endings_blocks.json', default=[])
road_en = J('data_en', 'roadmap_blocks.json', default=[])
hub_en = J('data_en', 'hub_intro_blocks.json', default=[])
images = J('data_en', 'images.json', default={'mode': 'none', 'map': {}})
GM = J('glossary', 'glossary_merged.json', default={'flat': {}, 'by_category': {}})
G, FLAT = GM.get('by_category', {}), GM.get('flat', {})
TRZH = G.get('trophies', {})
report = {'missing_unit': [], 'unlinked': [], 'warn': []}
LANG = cfg.get('lang', 'zh')  # "en": English-only page — no glossary research / translation; zh fields fall back to English
EN_ONLY = LANG == 'en'


def st(s):
    return H.unescape(re.sub(r'<[^>]+>', '', s or '')).replace('\xa0', ' ').strip()


def balance(h):
    """drop unmatched closing tags, close unclosed b/i/u/span"""
    out, stack = [], []
    for tok in re.split(r'(<[^>]+>)', h or ''):
        m = re.match(r'<(/?)(b|i|u|span)\b[^>]*>', tok)
        if not m:
            out.append(tok)
            continue
        if m.group(1):
            if m.group(2) in stack:
                while stack:
                    t = stack.pop()
                    out.append(f'</{t}>')
                    if t == m.group(2):
                        break
        else:
            stack.append(m.group(2))
            out.append(tok)
    while stack:
        out.append(f'</{stack.pop()}>')
    return re.sub(r'<(b|i|u|span)[^>]*>\s*</\1>', '', ''.join(out)).strip()


def split_head(head, body):
    """A head that swallowed text after a <br> (bold run containing the line break) -> (head, body)."""
    if '<br>' not in (head or ''):
        return head, body
    i = head.index('<br>')
    h, b = head[:i], head[i + 4:]
    if (body or '').strip():
        b = b + '<br>' + body
    opens = []
    for m in re.finditer(r'<(/?)(b|i|u|span)\b([^>]*)>', h):
        if m.group(1):
            if opens and opens[-1][0] == m.group(2):
                opens.pop()
        else:
            opens.append((m.group(2), m.group(0)))
    b = ''.join(o[1] for o in opens) + b
    return balance(h), balance(b)


def gz(en, *cats, default=None):
    """glossary lookup: exact (flat) -> category keys starting with en -> default/en (’ and ' treated alike)"""
    for v in (en, en.replace('’', "'"), en.replace("'", '’')):
        if v in FLAT:
            return FLAT[v]
    for c in cats:
        for k, v in G.get(c, {}).items():
            if k == en or k.startswith(en + ' ') or k.startswith(en + ':') or k.split(' (')[0] == en:
                return re.sub(r'（[^）]*）$', '', v)
    return default if default is not None else en


TR, TRA, TRR, TRM, TRT, ENT = {}, {}, {}, {}, {}, {}
MISSING_TXT = {}
for f in sorted(glob.glob(os.path.join(W, 'tr_out', '*.json'))):
    try:
        o = json.load(open(f, encoding='utf-8'))
    except Exception as e:
        report['warn'].append(f'tr_out {f}: {e}')
        continue
    for k, v in (o.get('units') or {}).items():
        (TR if isinstance(v, dict) else TRM)[k] = v
        if isinstance(v, dict) and v.get('title'):  # prose walkthroughs: short action title written with the route job
            TRT.setdefault(k, {'zh': v['title'], 'en': v.get('title_en', '')})
    TRA.update(o.get('areas') or {})
    TRT.update(o.get('titles') or {})  # short action titles for prose items: {item id: {zh, en}}
    ENT.update(o.get('entities') or {})  # prose paragraphs split into entities (prepare_entities.py)
    TRR.update(o.get('regions') or {})


def tm(uid, en):
    v = TRM.get(uid)
    if v is None and EN_ONLY:
        return en
    if v is None:
        report['missing_unit'].append(uid)
        MISSING_TXT[uid] = en
        return en
    return v


# ---------------- types ----------------
TYPES = {k: {'zh': v[0], 'en': v[1], 'badge': {'zh': v[2], 'en': v[3]}, 'stat': bool(v[4])} for k, v in cfg['types'].items()}
for k in ('other', 'tip', 'warn'):
    TYPES.setdefault(k, {'zh': {'other': '其他', 'tip': '提示', 'warn': '警告'}[k], 'en': k.title(), 'badge': {'zh': '', 'en': ''}, 'stat': False})
STAT_ORDER = [k for k, v in TYPES.items() if v['stat']]
PRIORITY = cfg.get('type_priority') or [t for t, _ in cfg['type_rules']] + ['other', 'tip']
MISS_TYPES = set(cfg.get('miss_types', []))
MISS_RULE = cfg.get('miss_rule', 'source')
MISS_RX = re.compile(r"(?<!not )(?<!n’t )(?<!n't )\bmissable\b|point of no return|\b(will|would) (fail|be lost|disappear|despawn)"
                     r"|\bfails? (if|after|once|when)|no longer (be )?(available|obtainable|possible)|becomes? (unavailable|unobtainable)"
                     r"|can(not|’t|'t) (be )?(obtain|get|return|reach)\w* (it |this |them |there )?(later|again|afterwards)"
                     r"|only (get )?(1|one) (try|chance|attempt)|locks? you out|permanently (missed|lost|locked)", re.I)
COLS = cfg.get('collections', [])
TAG_TROPHY = {c['type']: c['trophy'] for c in COLS if c.get('trophy')}
TROPHY_ID = {t['name_en']: f't{i}' for i, t in enumerate(trophies_en)}

# ---------------- images ----------------
IMG = {}
IMGKEY = {}
for url, ent in images.get('map', {}).items():
    k = ent['key']
    IMGKEY[url] = k
    if images.get('mode') == 'embed' and ent.get('file') and os.path.exists(os.path.join(W, ent['file'])):
        IMG[k] = 'data:image/jpeg;base64,' + base64.b64encode(open(os.path.join(W, ent['file']), 'rb').read()).decode()
    elif images.get('mode') == 'folder' and ent.get('file'):
        IMG[k] = 'images/' + os.path.basename(ent['file'])
    else:
        IMG[k] = ent.get('remote', url)

# ---------------- regions / areas / items ----------------
NUM = '一二三四五六七八九十'


def zh_num(n):
    if n <= 10:
        return NUM[n - 1]
    if n < 20:
        return '十' + NUM[n - 11]
    return str(n)


BOSS_TYPES_ALL = set(cfg.get('boss_types', ['boss', 'elite', 'miniboss']))
COL_REF = {}  # "bead-6" -> entity item id (the agent said this entity is that checklist entry)


def expand_entities(item, parts):
    """one prose paragraph -> one checkable item per entity (title = its name, body = how to get it) and plain
    non-checkable route text in between; the paragraph's screenshots go to its first collectible (else first entity),
    its videos to its first boss / elite"""
    out, ents = [], [p for p in parts if p.get('type') not in ('route', 'warn')]
    first = ents[0] if ents else (parts[0] if parts else None)  # no entity: the route text keeps the media
    img_to = next((p for p in ents if p.get('type') in TAG_TROPHY or p.get('col')), first)
    vid_to = next((p for p in ents if p.get('type') in BOSS_TYPES_ALL), first)
    for k, p in enumerate(parts, 1):
        t = p.get('type') or 'other'
        base = {'id': f"{item['id']}-{k}", 'miss': False, 'tro': [], 'stags': [], 'imgs': [], 'videos': [],
                '_area_en': item['_area_en'], '_region': item['_region'], '_entity': True}
        if t == 'route':
            if p is img_to:
                base['imgs'] = [IMGKEY[u] for u in dict.fromkeys(item['_imgs_en'])]
            if p is vid_to:
                base['videos'] = list(item['videos'])
            out.append(dict(base, type='tip', check=False, style='', head={'zh': '', 'en': ''},
                            body={'zh': p.get('body_zh', ''), 'en': p.get('body_en', '')}, _tags=['tip'], _txt=st(p.get('body_en', ''))))
            continue
        t = t if t in TYPES else 'other'
        col = (p.get('col') or '').rsplit('-', 1)[0]
        tags = list(dict.fromkeys([t] + ([col] if col else [])))
        check = t != 'warn'
        txt = (p.get('name_en') or '') + ' ' + st(p.get('body_en', ''))
        if ents and p is ents[0]:
            base['id'] = item['id']  # the first entity keeps the paragraph's id: saved progress and links survive
            base['_para'] = (item['type'], item['_txt'])  # … and the whole item's ending link (the choice sits in a red note)
        x = dict(base, type=t, check=check, style={'warn': 'warn', 'save': 'save'}.get(t, ''),
                 head={'zh': H.escape(p.get('name_zh') or p.get('name_en') or ''), 'en': H.escape(p.get('name_en') or '')},
                 body={'zh': p.get('body_zh', ''), 'en': p.get('body_en', '')},
                 miss=check and (t in MISS_TYPES or bool(MISS_RX.search(txt))),
                 tro=[TROPHY_ID[TAG_TROPHY[g]] for g in tags if g in TAG_TROPHY and TAG_TROPHY[g] in TROPHY_ID],
                 stags=[g for g in tags if g in TYPES and TYPES[g]['stat'] and not (g != t and g in BOSS_TYPES_ALL and t in BOSS_TYPES_ALL)] if check else [],
                 imgs=[IMGKEY[u] for u in dict.fromkeys(item['_imgs_en'])] if p is img_to else [],
                 videos=list(item['videos']) if p is vid_to else [], _tags=tags, _txt=txt)
        if p.get('col'):
            COL_REF[p['col']] = x['id']
        out.append(x)
    return out


regions, all_items = [], []
for ri, r in enumerate(areas_en):
    rid = r['id']
    trr = TRR.get(rid, {})
    rz = gz(r['title_en'], 'regions', default='')
    if not rz or rz == r['title_en']:
        rz = re.sub(r'^(区域|第.区域)\s*\d*\s*[：:]\s*', '', trr.get('title', '')) or r['title_en']
    reg = {'id': rid, 'no': {'zh': f'第{zh_num(ri + 1)}区域', 'en': f'Region {ri + 1}'}, 'short': {'zh': rz, 'en': r['title_en']},
           'summary': {'zh': trr.get('summary_zh', ''), 'en': trr.get('summary_en', '')},
           'leave': [{'zh': x.get('zh', ''), 'en': x.get('en', '')} for x in trr.get('leave', [])],
           'colInfo': {'zh': '', 'en': ''}, 'areas': []}
    for a in r['areas']:
        tra = TRA.get(a['id'], {})
        tz = tra.get('title') or ' & '.join(gz(x.strip().split(' (')[0]) for x in a['title_en'].split(' & '))
        reach_en = re.sub(r'^How to reach[^:]*:\s*', '', st(a.get('reach_en', '')) and a['reach_en'])
        area = {'id': a['id'], 'url': a['url'], 'title': {'zh': tz, 'en': a['title_en']},
                'tagline': {'zh': tra.get('tagline', ''), 'en': tra.get('tagline_en', '')},
                'reach': {'zh': tra.get('reach') or reach_en, 'en': reach_en}, 'sections': []}
        sec_tr = tra.get('sections', [])
        for si, s in enumerate(a['sections']):
            sec = {'title': {'zh': sec_tr[si] if si < len(sec_tr) and sec_tr[si] else s['title_en'], 'en': s['title_en']}, 'items': []}
            for it in s['items']:
                tags = it['tags']
                prim = next((p for p in PRIORITY if p in tags), 'other')
                style, check = '', it['kind'] == 'item'
                if 'warn' in tags:
                    style = 'warn'
                    rest = [p for p in PRIORITY if p in tags and p != 'warn']
                    prim = rest[0] if rest else 'other'
                if st(it['head_en']).startswith('Boss') and 'boss' in tags:
                    prim = 'boss'
                h0, b0 = split_head(it['head_en'], it['body_en'])
                if h0 != it['head_en']:
                    it['head_en'], it['body_en'] = h0, b0
                    if prim in ('save', 'ending', 'boss') or (it['kind'] == 'note' and 'warn' not in tags):
                        check = True
                if prim == 'save':
                    style, check = 'save', True
                if prim == 'tip':
                    check = False
                tr = TR.get(it['id'])
                if tr is None:
                    if not EN_ONLY:
                        report['missing_unit'].append(it['id'])
                    tr = {}
                head_en = balance(re.sub(r'^<b>|</b>$', '', it['head_en']).strip())
                head_en = re.sub(r'\s*\((?:<a[^>]*>)?Boss Guide(?:</a>)?\)', '', head_en)
                txt_head = st(it['head_en'])
                txt_all = txt_head + ' ' + st(it['body_en'])
                # 易错过 = the guide itself says so: explicit wording on this item, or a whole type the guide declares
                # missable (game.json miss_types, e.g. Wuchang "all NPC interactions are immediately missable").
                # Translator judgment is only used with miss_rule: "translator".
                if MISS_RULE == 'translator' and tr.get('missable') is not None:
                    miss = tr['missable']
                else:
                    miss = prim in MISS_TYPES or bool(MISS_RX.search(txt_all))
                tro = []
                for tg in tags:
                    if tg in TAG_TROPHY and TAG_TROPHY[tg] in TROPHY_ID:
                        tro.append(TROPHY_ID[TAG_TROPHY[tg]])
                name_ok = prim in ('ending', 'save') or '<t class=' in it['head_en'] or (prim == 'boss' and not bosses_en)
                for tname, tid in (TROPHY_ID.items() if name_ok else []):
                    if len(tname) > 4 and tid != 't0' and re.search(r'(?<![\w])' + re.escape(tname) + r'(?![\w])', txt_head) and tid not in tro:
                        tro.append(tid)
                hz, bz = split_head(tr.get('head', head_en), tr.get('body', it['body_en']))
                if not st(it['body_en']) and len(st(head_en)) > 120:  # a whole paragraph parsed as a title -> show it as body
                    it['body_en'], head_en = head_en, ''
                    if not st(bz or ''):
                        bz, hz = hz, ''
                item = {'id': it['id'], 'type': prim, 'check': check, 'style': style,
                        'head': {'zh': balance(re.sub(r'^<b>|</b>$', '', (hz or '').strip())), 'en': head_en},
                        'body': {'zh': bz or '', 'en': it['body_en']},
                        'miss': bool(miss) and check, 'tro': tro,
                        'stags': [t for t in dict.fromkeys([prim] + tags) if t in TYPES and TYPES[t]['stat']
                                  and not (t != prim and t in BOSS_TYPES_ALL and prim in BOSS_TYPES_ALL)] if check else [],  # a fight is a boss OR an elite
                        'imgs': [IMGKEY[u] for u in dict.fromkeys(it['imgs']) if u in IMGKEY],
                        'videos': list(dict.fromkeys(it['videos'])),
                        '_imgs_en': [u for u in it['imgs'] if u in IMGKEY],
                        '_tags': tags, '_area_en': a['title_en'], '_region': rid, '_txt': txt_all}
                for x in (expand_entities(item, ENT[it['id']]) if it['id'] in ENT else [item]):
                    sec['items'].append(x)
                    all_items.append(x)
            area['sections'].append(sec)
        reg['areas'].append(area)
    regions.append(reg)

# ---------------- collections ----------------
REGION_BY_EN = {}
for r in areas_en:
    REGION_BY_EN[r['title_en']] = r['id']
    REGION_BY_EN[re.sub(r'^(Region|Chapter|Act) \d+:\s*', '', r['title_en'])] = r['id']
for k, v in cfg.get('region_aliases', {}).items():
    REGION_BY_EN[k] = v
REG_NAMES = sorted(REGION_BY_EN, key=len, reverse=True)
REG_RX = '|'.join(re.escape(x) for x in REG_NAMES)


def parse_area(area_en):
    area_en = (area_en or '').replace('\xa0', ' ').strip()
    m = re.match(r'(?:(?:Region|Chapter|Act) \d+:\s*)?(' + REG_RX + r')\s*(?:[–-]\s*(.+))?$', area_en) if REG_RX else None
    if m:
        return REGION_BY_EN[m.group(1)], (m.group(2) or '').strip()
    return None, area_en


def area_zh(area_en):
    rid, name = parse_area(area_en)
    if rid is None:
        return {'zh': gz(area_en), 'en': area_en}
    rz = next(r['short']['zh'] for r in regions if r['id'] == rid)
    if not name:
        return {'zh': rz, 'en': area_en}
    return {'zh': f'{rz} · {gz(name.split(" (")[0])}', 'en': area_en}


def area_first_item(rid, aname):
    squash = lambda x: re.sub(r'[\s–\-:]+', '', x.lower())  # "Watermill" = "Water Mill", "Upper Tower – Antechamber" = "Upper Tower Antechamber"
    an = squash((aname or '').split(' (')[0])
    if not an:
        return None
    for it in all_items:
        if (rid is None or it['_region'] == rid) and an in squash(it['_area_en']):
            return it
    return None


def scoped(pool, rid, aname):
    an = (aname or '').split(' (')[0].lower()
    p1 = [it for it in pool if rid is None or it['_region'] == rid] or pool
    p2 = [it for it in p1 if an and an in it['_area_en'].lower()]
    return p2, p1


def lab_name(label):
    m = re.match(r'.*?#\s*\d+\s*[:–-]?\s*(.*)', label)
    n = m.group(1).strip() if m else label
    return re.split(r'\s+/\s+|\s+\(', n)[0].strip()


ORDER = {it['id']: i for i, it in enumerate(all_items)}
cols = {}
for c in COLS:
    key, src = c['type'], c.get('source', 'tag')
    lst, used = [], set()
    if src == 'items':  # built after the boss guide has added its bosses to the route (see below)
        cols[key] = []
        continue
    if src == 'tag':
        rx = re.compile(c['head_regex']) if c.get('head_regex') else None
        seen_names = set()
        for it in all_items:
            if key not in it['_tags'] or not it['check'] or (rx and not rx.search(st(it['head']['en']))):
                continue
            nm = re.sub(r'^#\s*\d+\s*[–-]\s*', '', st(it['head']['en']))
            if c.get('dedupe') and (it['_region'], nm) in seen_names:
                continue
            seen_names.add((it['_region'], nm))
            lst.append({'id': it['id'], 'label': {'zh': st(it['head']['zh']), 'en': nm},
                        'area': {'zh': next(r['short']['zh'] for r in regions if r['id'] == it['_region']) + ' · ' + next(a['title']['zh'] for r in regions for a in r['areas'] if any(x is it for s in a['sections'] for x in s['items'])),
                                 'en': it['_area_en']}})
        cols[key] = lst
        continue
    entries = bt.get(key, {}).get('entries', [])
    if c.get('dedupe'):
        seen_lab = set()
        entries = [e for e in entries if not (e['label_en'] in seen_lab or seen_lab.add(e['label_en']))]
    cursor = -1
    fmt = bt.get(key, {}).get('format', '')
    used |= {v for k, v in COL_REF.items() if k.rsplit('-', 1)[0] == key}
    for n, e in enumerate(entries, 1):
        label_en, area_en = e['label_en'], e['area_en']
        mreg = re.search(r'((?:' + REG_RX + r')\s+[–-]\s+.+)$', label_en) if REG_RX else None
        if mreg and mreg.start() > 0:
            area_en, label_en = mreg.group(1), label_en[:mreg.start()].strip()
        elif not parse_area(area_en)[0]:
            first = st(e['body_en'].split('<br>')[0])
            if parse_area(first)[0] and len(first) < 90:
                area_en = first
        rid, aname = parse_area(area_en)
        if fmt == 'dashlist':
            aname = label_en
        match = c.get('match', 'name')
        name = label_en if fmt == 'dashlist' else lab_name(label_en)
        if c.get('name_regex'):
            mm = re.match(c['name_regex'], name)
            if mm:
                name = mm.group(1)
        pool = [it for it in all_items if key in it['_tags'] and it['check'] and it['id'] not in used]
        if c.get('head_regex'):
            hrx = re.compile(c['head_regex'])
            pool = [it for it in pool if hrx.search(st(it['head']['en']))]
        it, goto = None, None
        nums = re.findall(r'#\s*(\d+(?:\s*[-–]\s*\d+)?)', e['label_en'])  # "#28, #29", "#2-4"
        num = '、#'.join(re.sub(r'\s*[-–]\s*', '-', x) for x in nums) if nums else str(n)
        if match == 'number':
            rx = re.compile(c['number_regex'].replace('{n}', num))
            it = next((x for x in pool if rx.search(st(x['head']['en']))), None)
            label = {'zh': c.get('label_zh', '{name} #{n}').replace('{n}', num), 'en': label_en}
        elif match == 'paren':
            bn = re.search(r'\((.*?)\)', label_en)
            core = (bn.group(1) if bn else '').split('–')[-1].strip().lower()
            it = next((x for x in pool if core and core in x['_txt'].lower()), None) or (scoped(pool, rid, aname)[0] or scoped(pool, rid, aname)[1] or [None])[0]
            zf = G.get(c.get('glossary_category', ''), {}).get(e['label_en'], '')
            zf = zf[:zf.index('）') + 1] if '）' in zf else (c.get('label_zh', '{n}').replace('{n}', num))
            label = {'zh': zf, 'en': label_en}
        elif match == 'order':
            # by-type lists are chronological like the route: take the first unused item in the entry's area,
            # else the next unused tagged item after the previous match (never jump backwards / to a far region)
            a2, _ = scoped(pool, rid, aname)
            a2 = [x for x in a2 if ORDER[x['id']] > cursor] or a2
            it = a2[0] if a2 else next((x for x in pool if ORDER[x['id']] > cursor), None)
            if it is not None:
                cursor = ORDER[it['id']]
            label = {'zh': c.get('label_zh', '#{n}').replace('{n}', num), 'en': re.sub(r':\s*$', '', label_en)}
            gzf = G.get(c.get('glossary_category', ''), {}).get(e['label_en'], '')
            if gzf:
                label['zh'] = re.sub(r'\s*(' + '|'.join(re.escape(r['short']['zh']) for r in regions) + r')\s*[–-].*$', '', gzf)
        else:  # name
            pat = re.compile(re.escape(name).replace('’', "['’]"), re.I)
            a2, r2 = scoped(pool, rid, aname)
            it = next((x for x in a2 + r2 + pool if pat.search(st(x['head']['en']))), None)
            if it is None:
                anyp = [x for x in all_items if x['id'] not in used]
                a3, r3 = scoped(anyp, rid, aname)
                g = next((x for x in a3 + r3 if pat.search(x['_txt'])), None)
                goto = g['id'] if g else None
            zh = gz(name, c.get('glossary_category', ''), key + 's', key)
            label = {'zh': zh, 'en': name}
            if c.get('category_suffix'):
                cat = re.search(r'\(([^)]+)\)', label_en)
                if cat:
                    cz = gz(cat.group(1), default='')
                    cz = cz if cz and cz != cat.group(1) else gz(cat.group(1).rstrip('s'), default=cat.group(1))
                    label = {'zh': f'{zh}（{cz}）', 'en': f'{name} ({cat.group(1)})'}
            note = re.search(r'\((Bought from [^)]+)\)', label_en)
            if note:
                seller = re.sub(r'^Bought from\s+', '', note.group(1))
                label = {'zh': label['zh'] + f'（{gz(seller)}处购买）', 'en': label['en'] + f' ({note.group(1)})'}
        if f'{key}-{n}' in COL_REF:  # prepare_entities.py: the agent matched this entry to a route entity
            it = next(x for x in all_items if x['id'] == COL_REF[f'{key}-{n}'])
            cursor = ORDER[it['id']]
        full = G.get(f'collection:{key}', {})  # research agents translate whole by-type labels (make_terms "collection:<type>")
        fz = full.get(e['label_en']) or full.get(e['label_en'].replace('’', "'")) or full.get(e['label_en'].replace("'", '’'))
        if fz:
            label = {'zh': fz, 'en': label['en']}
        if it is not None:
            used.add(it['id'])
            cid = it['id']
            for u in e.get('imgs', []):
                if u in IMGKEY and IMGKEY[u] not in it['imgs']:
                    it['imgs'].append(IMGKEY[u])
            if c.get('trophy') in TROPHY_ID and TROPHY_ID[c['trophy']] not in it['tro']:
                it['tro'].append(TROPHY_ID[c['trophy']])
        else:
            cid = f'col-{key}-{n}'
            if goto is None:
                g = area_first_item(rid, aname)
                if g is None and ':' in e['label_en']:  # "Prayer Bead #6: Estate Path" -> step titled "… Estate Path"
                    tail = re.sub(r'\s*\(.*?\)|\s*[–-]\s*MISSABLE.*$', '', e['label_en'].split(':', 1)[1]).strip()
                    tail = re.sub(r'\s+[Ii]dol$', '', tail)
                    g = area_first_item(rid, tail) or area_first_item(None, tail)
                goto = g['id'] if g else None
            report['unlinked'].append(f'{key} #{n}: {label_en} @ {area_en} -> goto {goto}')
        ent = {'id': cid, 'label': label, 'area': area_zh(area_en if fmt != 'dashlist' else (e['area_en']))}
        if MISS_RX.search(e['label_en'] + ' ' + st(e['body_en'])):  # the by-type page says this one is missable
            ent['miss'] = True
        if goto:
            ent['goto'] = goto
        if c.get('desc') and st(e['body_en']):
            ent['desc'] = {'zh': tm(f'col-{key}-{n}-desc', e['body_en']), 'en': e['body_en']}
            ent['imgs'] = [IMGKEY[u] for u in dict.fromkeys(e.get('imgs', [])) if u in IMGKEY]
            ent['videos'] = list(dict.fromkeys(e.get('videos', [])))
        lst.append(ent)
    cols[key] = lst
    if c.get('match') == 'number' and c.get('trophy') in TROPHY_ID:
        # numbered collectibles ("Riddle #3"): only the items that ARE checklist entries carry the trophy chip — not
        # "Riddle #3 (Wrong Answer)", save-revert notes or warnings that merely share the tag (Wuchang 《八斗之才》)
        ids, tid = {e['id'] for e in lst}, TROPHY_ID[c['trophy']]
        for it in all_items:
            if key in it['_tags'] and it['id'] not in ids and tid in it['tro']:
                it['tro'].remove(tid)


# ---------------- boss guide facts -> boss items ----------------
BOSS_TYPES = set(cfg.get('boss_types', ['boss', 'elite', 'miniboss']))


def name_words(name):
    return [w for w in re.findall(r"[A-Za-z’']+", name) if len(w) > 2 and w.lower() not in ('the', 'and', 'of')]


def name_hit(name, h):
    """exact name, or every word of a 2+-word name ("Gyoubu Oniwa" in "Gyoubu Masataka Oniwa")"""
    if not name:
        return False
    if name in h:
        return True
    ws = name_words(name)
    return len(ws) >= 2 and all(re.search(r'\b' + re.escape(w) + r'\b', h) for w in ws)


BOSS_ITEM = {}  # boss guide index -> route item id
FIGHT = re.compile(r'\b(defeat\w*|fight\w*|health ?bars?|kill\w*|beat|beaten|slay\w*|boss|mini-?boss|tak(e|es|ing) on|battle\w*|duel\w*)\b', re.I)
PROSE = bool(cfg.get('paragraph_items'))


def phrase_hit(name, text):
    """all words of the name appear close together (window = words + 3 tokens)"""
    ws = [w.lower() for w in name_words(name)]
    if not ws:
        return False
    toks = [t.lower() for t in re.findall(r"[A-Za-z’']+", text)]
    win = len(ws) + 3
    return any(all(w in toks[k:k + win] for w in ws) for k in range(len(toks)))


def boss_names(guide_name):
    g = re.sub(r'^Boss\s*#\s*\d+\s*[–-]\s*', '', guide_name)
    g = re.sub(r'\s*\([^)]*\)', '', g)
    names = [x.strip() for x in re.split(r'\s*\+\s*', g) if x.strip()]
    names += [n.split(' – ')[-1] for n in names]
    names += [re.sub(r'^(True|Real)\s+', '', n) for n in names]  # "True Corrupted Monk": the route just says "the real Corrupted Monk"
    names += [re.sub(r'\s+(\d+(st|nd|rd|th)|second|third)(\s+(version|fight|encounter|phase))?$', '', n, flags=re.I) for n in names]  # "Juzou the Drunkard 2nd Version"
    return list(dict.fromkeys(names))


PAST_FIGHT = re.compile(r"\s*(after|once|now that|since)\b[^.]{0,25}\b(defeated|beaten|killed|beat)\b", re.I)


def fights(it, names):
    """the body names the boss in a sentence that (or whose next sentence) talks about fighting —
    "a main boss awaits: Genichiro Ashina." / "Gyoubu … is a horse riding samurai. The best method to defeat him …"""
    sents = re.split(r'(?<=[.!?])\s+', st(it['body']['en']))
    for k, x in enumerate(sents):
        if PAST_FIGHT.match(x):  # "After having defeated the Corrupted Monk in Ashina Depths, …" is a precondition, not the fight
            continue
        if any(phrase_hit(n, x) for n in names) and (FIGHT.search(x) or (k + 1 < len(sents) and FIGHT.search(sents[k + 1]))):
            return True
    return False


def rev_hit(name, title):
    """an entity titled "Sakura Bull" is the boss-guide entry "Sakura Bull of the Palace" (all its 2+ words are in the name)"""
    tw = [w.lower() for w in name_words(title)]
    nw = {w.lower() for w in name_words(name)}
    return len(tw) >= 2 and all(w in nw for w in tw)


def boss_items(names, exclude=()):
    """route items for a boss: the title names it (or, if the title is empty, the body does);
    in prose walkthroughs the body must also describe the fight, otherwise a mere mention would count"""
    out = []
    for it in all_items:
        if it['type'] not in BOSS_TYPES or it['id'] in exclude:
            continue
        title = st(it['head']['en']) or st(it['body']['en'])[:200]
        if any(name_hit(n, title) or (it.get('_entity') and rev_hit(n, title)) for n in names) \
                and (not PROSE or '_boss_entry' in it or it.get('_entity') or fights(it, names)):
            out.append(it)
    return out


ENTRY_NAMES = [boss_names(b['name_en']) for b in bosses_en]


def item_title(it):
    return st(it['head']['en']) or st(it['body']['en'])[:200]


def best_len(names, it):
    t = item_title(it)
    if PROSE and '_boss_entry' not in it and not it.get('_entity') and not fights(it, names):
        return 0
    return max((len(name_words(n)) for n in names if name_hit(n, t)), default=0)


used = set()
for i, b in enumerate(bosses_en):
    vids, fen, fzh = [], [], []
    for k, blk in enumerate(b['blocks']):
        vids += blk.get('videos', [])
        if blk['k'] == 'video':
            vids.append(blk['src'])
        if blk['k'] == 'p' and re.match(r'<b>(Difficulty|Recommended Weapon|Reward|Rewards)', blk['html']):
            fen.append(blk['html'])
            fzh.append(tm(f'boss-{i}-p{k}', blk['html']))
    cands = boss_items(ENTRY_NAMES[i], used)
    # "Shichimen Warrior (Abandoned Dungeon)": the bracket names the place — never take the same-named fight elsewhere
    qual = re.search(r'\(([^)]*)\)', b['name_en'])
    qreg = next((rid for name, rid in REGION_BY_EN.items() if qual and name.lower() in qual.group(1).lower()), None)
    if qreg:
        cands = [it for it in cands if it['_region'] == qreg]
    # "Genichiro · Sword Saint Isshin Ashina" belongs to "Isshin, the Sword Saint", not to "Isshin Ashina (Shura Ending)"
    cands = [it for it in cands
             if not any(best_len(ENTRY_NAMES[j], it) > best_len(ENTRY_NAMES[i], it)
                        for j in range(len(bosses_en)) if j != i and j not in BOSS_ITEM)]  # entries still unassigned
    if '2nd' in b['name_en'] and len(cands) > 1:
        cands = cands[1:]
    if not cands:
        continue
    it = cands[0]
    used.add(it['id'])
    BOSS_ITEM[i] = it['id']
    it['videos'] = list(dict.fromkeys(it['videos'] + vids))
    if fen:
        it['body']['en'] += '<div class="bfacts">' + '<br>'.join(fen) + '</div>'
        it['body']['zh'] += '<div class="bfacts">' + '<br>'.join(fzh) + '</div>'


# ---------------- boss guide entries the route never covers -> into the route, in the boss guide's order --------
# Prose walkthroughs skip late-game / ending-specific / backtracking bosses (Sekiro: Guardian Ape Undying, Demon of
# Hatred, the Headless …); the boss guide has them, and its numbering (#1 … #53) is PowerPyx's own order, interleaved
# with the walkthrough. Each becomes a checkbox (boss name; body = location + when it appears, strategy, reward,
# video) inserted after the previous boss-guide entry that is on the route — or, between that one and the next one,
# after the last route item that names its place ("Feeding Grounds idol", "Ashina Castle"). User: "不应该在前面的时候
# 就能打吗？…应该按攻略里的顺序把这些首领加进去" (a separate 「补充首领」 region was rejected).
RULES = [(t, re.compile(rx)) for t, rx in cfg.get('type_rules', [])]
SUPP_DEFAULT = cfg.get('boss_extra_type') or ('elite' if 'elite' in TYPES and 'elite' in BOSS_TYPES else 'boss')
FACT_RX = re.compile(r'<b>(Difficulty|Recommended Weapon|Reward|Rewards)')


def route_seq():
    return [(sec, it) for r in regions for a in r['areas'] for sec in a['sections'] for it in sec['items']]


n_extra = 0
REG_EN_ALL = {r['id']: r['short']['en'] for r in regions}
AWAY = set()  # extra bosses fought back in another region (a 「回头清理」 note opens each run of them)
for i, b in enumerate(bosses_en):
    if i in BOSS_ITEM or cfg.get('boss_extra') is False:
        continue
    num = re.match(r'Boss\s*#\s*(\d+)', b['name_en'])
    name_en = re.sub(r'^Boss\s*#\s*\d+\s*[–-]\s*', '', b['name_en']).strip()
    ps = [(k, blk) for k, blk in enumerate(b['blocks']) if blk['k'] == 'p' and st(blk.get('html', ''))]
    loc = next((blk['html'] for k, blk in ps if re.match(r'<b>Location', blk['html'])), '')
    place_en = st(re.sub(r'<b>Location:?</b>:?', '', loc.split('<br>')[0])).strip(' :') if loc else ''
    place_en = re.sub(r'\s*\([^)]*\)', '', place_en)
    body_en, body_zh, fen, fzh, vids, imgs = '', '', [], [], [], []
    for blk in b['blocks']:
        vids += blk.get('videos', []) + ([blk['src']] if blk['k'] == 'video' else [])
        imgs += [IMGKEY[u] for u in blk.get('imgs', []) if u in IMGKEY]
    for k, blk in ps:
        if FACT_RX.match(blk['html']):
            fen.append(blk['html'])
            fzh.append(tm(f'boss-{i}-p{k}', blk['html']))
        else:
            body_en += f'<p>{blk["html"]}</p>'
            body_zh += f'<p>{tm(f"boss-{i}-p{k}", blk["html"])}</p>'
    if fen:
        body_en += '<div class="bfacts">' + '<br>'.join(fen) + '</div>'
        body_zh += '<div class="bfacts">' + '<br>'.join(fzh) + '</div>'
    tags = [t for t, rx in RULES if t in BOSS_TYPES and rx.search(name_en)] or [SUPP_DEFAULT]
    prim = next((p for p in PRIORITY if p in tags), tags[0])
    # where: after the previous boss-guide entry placed on the route; between it and the next one, after the last
    # route item naming this boss's place (sub-place or "X idol" first, then the region)
    seq = route_seq()
    pos = {it['id']: k for k, (sec, it) in enumerate(seq)}
    prev = next((pos[BOSS_ITEM[j]] for j in range(i - 1, -1, -1) if BOSS_ITEM.get(j) in pos), -1)
    nxt = next((pos[BOSS_ITEM[j]] for j in range(i + 1, len(bosses_en)) if BOSS_ITEM.get(j) in pos), len(seq))
    nxt = max(nxt, prev + 1)
    sub = [x.strip() for x in place_en.split(' – ')[1:]] + re.findall(r'([A-Z][\w’\']*(?: [A-Z][\w’\']*)*) [Ii]dol\b', st(loc))
    reg = place_en.split(' – ')[0].strip()
    names_txt = lambda k: (st(seq[k][1]['head']['en']) + ' ' + st(seq[k][1]['body']['en'])).lower()
    region_end = prev + 1
    while 0 <= prev and region_end < len(seq) and seq[region_end][1]['_region'] == seq[prev][1]['_region']:
        region_end += 1
    at = prev
    # a specific place ("Feeding Grounds idol"): where the walkthrough first gets there, up to the end of this region
    keys = [k for k in sub if len(k) > 3 and k.lower() not in ('sculptor', 'the')]
    hit = [k for k in range(prev + 1, nxt) if keys and any(kk.lower() in names_txt(k) for kk in keys)] or \
          [k for k in range(nxt, region_end) if keys and any(kk.lower() in names_txt(k) for kk in keys)]
    if hit:
        at = hit[0]
    else:  # the region ("Ashina Castle"): the first route text in the window that goes there ("return to Ashina Castle")
        hit = [k for k in range(prev + 1, nxt) if len(reg) > 3 and reg.lower() in names_txt(k)]
        if hit:
            at = hit[0]
    if at < 0:
        sec, host = seq[0][0], None
        idx = 0
    else:
        sec, host = seq[at]
        idx = sec['items'].index(host) + 1
        if host.get('style') == 'warn':  # a decision made at this place comes after its fights ("结局抉择")
            idx -= 1
            host = sec['items'][idx - 1] if idx > 0 else host
        while idx < len(sec['items']) and '-col-' in sec['items'][idx]['id']:  # keep a fight's drops right behind it
            idx += 1
    iid = f'bossguide-{num.group(1) if num else i}'
    txt_all = name_en + ' ' + st(body_en)
    item = {'id': iid, 'type': prim, 'check': True, 'style': '',
            'head': {'zh': tm(f'boss-{i}-name', H.escape(name_en)), 'en': H.escape(name_en)},
            'body': {'zh': body_zh, 'en': body_en}, 'miss': bool(MISS_RX.search(txt_all)), 'tro': [],
            'stags': [prim] if TYPES.get(prim, {}).get('stat') else [],
            'imgs': list(dict.fromkeys(imgs)), 'videos': list(dict.fromkeys(vids)),
            '_tags': tags, '_area_en': host['_area_en'] if host else place_en, '_region': host['_region'] if host else regions[0]['id'],
            '_txt': txt_all, '_boss_entry': i, '_boss_place': place_en}
    host_place = (REG_EN_ALL.get(host['_region'], '') + ' ' + host['_area_en'] + ' ' + st(host['head']['en']) + ' ' + st(host['body']['en'])) if host else ''
    prev_item = sec['items'][idx - 1] if idx > 0 else None
    host_base = re.sub(r'-note$', '', host['id'].split('-col-')[0]) if host else ''
    cont = host_base in AWAY  # right behind another backtracking boss (or its drop): same run, no new note
    away = cont or (bool(reg) and reg.lower() not in host_place.lower())
    if away:
        AWAY.add(iid)
    if away and not cont:  # one 「回头清理」 note per run of backtracking bosses
        sec['items'].insert(idx, {'id': f'{iid}-note', 'type': 'tip', 'check': False, 'style': '', 'head': {'zh': '', 'en': ''},
                                  'body': {'zh': '回头清理：按 PowerPyx 首领攻略的顺序，此时回到其他区域挑战下面的首领（每条开头写明位置与出现条件）。',
                                           'en': 'Backtracking: in the order of PowerPyx’s boss guide, go back to other regions for the bosses below (each starts with its location and when it appears).'},
                                  'miss': False, 'tro': [], 'stags': [], 'imgs': [], 'videos': [], '_tags': ['tip'],
                                  '_area_en': host['_area_en'], '_region': host['_region'], '_txt': ''})
        all_items.append(sec['items'][idx])
        idx += 1
    sec['items'].insert(idx, item)
    BOSS_ITEM[i] = iid
    all_items.append(item)
    n_extra += 1
if n_extra:
    print('bosses from the boss guide added to the route:', n_extra)

# ---------------- checklist entries a fight drops -> their own checkbox right after that fight ----------------
# By-type pages say "Prayer Bead #15: Dropped by the Armored Warrior miniboss"; prose walkthroughs often don't mention
# the drop at all. Such an unlinked entry becomes an item (title = its label, body = its 位置说明) placed right after the
# fight it names (sample_ui/7.png: 「残存的执念·执」 — 「击败琴女·烟千岁自动获得」), sharing its id with the checklist.
# "after defeating X, go …" only says when a spot becomes reachable — not a drop
DROP_RX = re.compile(r"(?:dropped by|drops? from|simply (?:defeat|kill|beat)|(?:(?:reward|obtain|grant|award|receiv|get|unlock|earn)\w* "
                     r"(?:(?:this|it)(?: one| \w+)? )?)(?:for|from|after|by) (?:defeating|killing|beating) )(?:the )?([^.;(]{3,90})", re.I)
FOUND_RX = re.compile(r'^\s*(collected in the open world|bought from|sold by)', re.I)  # found, not dropped, even if a fight is named


def loose_hit(name, text):  # phrase_hit that forgives transposed letters in long words ("Mizou" for "Mizuo")
    if phrase_hit(name, text):
        return True
    ws = [w.lower() for w in name_words(name)]
    toks = [t.lower() for t in re.findall(r"[A-Za-z’']+", text)]
    def same(w, t):  # transposed letters ("Mizou"/"Mizuo") or one wrong letter in a long word ("Qianziao"/"Qianxiao")
        if w == t:
            return True
        if len(w) >= 5 and len(w) == len(t) and sorted(w) == sorted(t):
            return True
        return len(w) >= 6 and len(w) == len(t) and sum(a != b for a, b in zip(w, t)) == 1
    return len(ws) >= 2 and all(any(same(w, t) for t in toks) for w in ws)


def col_item(ent, key, host, iid):
    """a trophy-checklist entry as a route item (title = its label, body = its 位置说明), sharing the entry's id"""
    t = st(ent['desc']['en'])
    x = {'id': iid, 'type': key, 'check': True, 'style': '', 'head': dict(ent['label']),
         'body': {'zh': ent['desc']['zh'], 'en': ent['desc']['en']}, 'miss': bool(ent.get('miss')),
         'tro': [TROPHY_ID[TAG_TROPHY[key]]] if key in TAG_TROPHY and TAG_TROPHY[key] in TROPHY_ID else [],
         'stags': [key] if TYPES.get(key, {}).get('stat') else [], 'imgs': list(ent.get('imgs', [])),
         'videos': list(ent.get('videos', [])), '_tags': [key], '_area_en': host['_area_en'], '_region': host['_region'],
         '_txt': ent['label']['en'] + ' ' + t, '_entity': True}
    ent['id'] = iid
    for k in ('goto', 'desc', 'imgs', 'videos'):  # the route item now carries the text
        ent.pop(k, None)
    return x
FIGHT_NAMES, FIGHT_FULL = {}, {}
for i, iid in BOSS_ITEM.items():
    FIGHT_NAMES.setdefault(iid, []).extend(ENTRY_NAMES[i])
    FIGHT_FULL[iid] = FIGHT_FULL.get(iid, '') + ' ' + bosses_en[i]['name_en']  # keeps "(Purification Ending Only)", "2nd Version"
FIGHTS = [it for it in all_items if it['type'] in BOSS_TYPES_ALL and it['check']]
SEC_OF = {x['id']: s_ for r in regions for a in r['areas'] for s_ in a['sections'] for x in s_['items']}
REG_EN = {r['id']: r['short']['en'] for r in regions}


def place_of(it):
    return it['_boss_place'].split(' – ')[0] if it.get('_boss_place') else REG_EN.get(it['_region'], '')


relinked, after = set(), {}
for key, lst in cols.items():
    for ent in lst:
        if not ent['id'].startswith('col-') or not ent.get('desc'):
            continue
        t = st(ent['desc']['en'])
        m = None if FOUND_RX.match(t) else DROP_RX.search(ent['label']['en'] + '. ' + t)
        if not m:
            continue
        hits = [it for it in FIGHTS if any(n and loose_hit(n, m.group(1)) for n in FIGHT_NAMES.get(it['id'], []) + [st(it['head']['en'])])]
        if not hits:
            continue
        etxt = (ent['label']['en'] + ' ' + t + ' ' + ent['area']['en']).lower()

        def score(it):  # shared qualifiers ("Purification", "2nd"), then the place, then route order
            extra = {w.lower() for w in re.findall(r"[A-Za-z0-9]+", FIGHT_FULL.get(it['id'], '') + ' ' + st(it['head']['en'])) if len(w) > 2}
            extra -= {w.lower() for n in FIGHT_NAMES.get(it['id'], []) for w in name_words(n)} | {'boss', 'the', 'only', 'ending', 'version'}
            return (sum(1 for w in extra if re.search(r'\b' + re.escape(w) + r'\b', etxt)),
                    bool(place_of(it) and place_of(it).lower() in etxt))
        boss = max(hits, key=score)  # max keeps the first of equals
        cid0 = ent['id']
        x = col_item(ent, key, boss, f"{boss['id']}-{cid0}")
        sec = SEC_OF[boss['id']]
        after[boss['id']] = after.get(boss['id'], 0) + 1
        sec['items'].insert(sec['items'].index(boss) + after[boss['id']], x)
        all_items.append(x)
        relinked.add(cid0)
n_drop = len(relinked)
# the rest with a known step (「定位」 target): a checkbox at the end of that step — the walkthrough skipped them
AREA_OF = {x['id']: a for r in regions for a in r['areas'] for s_ in a['sections'] for x in s_['items']}
ITEM_AT = {x['id']: x for x in all_items}
for key, lst in cols.items():
    for ent in lst:
        if ent['id'].startswith('col-') and ent.get('desc') and ent.get('goto') in AREA_OF:
            a = AREA_OF[ent['goto']]
            cid0 = ent['id']
            x = col_item(ent, key, ITEM_AT[ent['goto']], f"{a['id']}-{cid0}")
            a['sections'][-1]['items'].append(x)
            all_items.append(x)
            relinked.add(cid0)
if relinked:
    report['unlinked'] = [u for u in report['unlinked'] if not any(u.startswith(f"{c.rsplit('-', 1)[0][4:]} #{c.rsplit('-', 1)[1]}:") for c in relinked)]
    print('checklist entries added to the route:', n_drop, 'after their fight,', len(relinked) - n_drop, 'at the end of their step')

# boss guide "Reward: …, Great Serpent trophy / achievement" names the trophy explicitly
REWARD_TRO = {}
for i, b in enumerate(bosses_en):
    if i not in BOSS_ITEM:
        continue
    rew = ' '.join(st(blk['html']) for blk in b['blocks'] if blk['k'] == 'p' and FACT_RX.match(blk.get('html', '')))
    for tname in sorted(TROPHY_ID, key=len, reverse=True):
        m = re.search(r'[“"]?' + re.escape(tname) + r'[”"]?\s+trophy', rew)
        # skip "This boss does NOT unlock the “Corrupted Monk” trophy"
        if m and not re.search(r"\b(not|n[’']t)\b[^.]{0,40}$", rew[:m.start()], re.I):
            REWARD_TRO.setdefault(tname, BOSS_ITEM[i])

# ---------------- "defeat all bosses" style checklists over route items ----------------
# collections[].source "items": entries = the route checkboxes whose English title matches each regex in "names", in
# that order (Sekiro 《死斗的尽头》 = the 16 头目 of the game's BOSS list — not the prologue Genichiro, the Great
# Serpent, the Carp or any elite). Without a configured collection, a trophy "Defeat(ed) all bosses" gets one from
# every checkable item of type boss. Entries share the item ids, so ticking either side syncs.
AUTO_ALL = [t for t in trophies_en if re.search(r'\bdefeat(ed)?\s+(all|every)\s+(main\s+)?bosses\b', t['desc_en'], re.I)
            and t['name_en'] not in {c.get('trophy') for c in COLS}]
for t in AUTO_ALL:
    COLS.append({'type': 'allboss', 'trophy': t['name_en'], 'source': 'items', 'auto': True})
    TAG_TROPHY['allboss'] = t['name_en']
for c in COLS:
    if c.get('source') != 'items':
        continue
    key, lst = c['type'], []
    order = [(r, a, it) for r in regions for a in r['areas'] for sec in a['sections'] for it in sec['items'] if it['check']]
    if c.get('names'):
        picks = []
        for rx in c['names']:
            hit = next(((r, a, it) for r, a, it in order if re.search(rx, st(it['head']['en'])) and it['id'] not in {p[2]['id'] for p in picks}), None)
            if hit:
                picks.append(hit)
            else:
                report['unlinked'].append(f'{key}: no route item matches {rx}')
    else:
        picks = [(r, a, it) for r, a, it in order if it['type'] == 'boss']
    tid = TROPHY_ID.get(c.get('trophy'))
    for r, a, it in picks:
        lst.append({'id': it['id'], 'label': {'zh': st(it['head']['zh']), 'en': st(it['head']['en'])},
                    'area': {'zh': r['short']['zh'] + ' · ' + a['title']['zh'], 'en': r['short']['en'] + ' · ' + a['title']['en']}})
        if tid and tid not in it['tro']:
            it['tro'].append(tid)
    cols[key] = lst
COL_OF = {c['trophy']: c['type'] for c in COLS if c.get('trophy')}

# ---------------- trophies ----------------
def drop_links(h):
    parts = re.split(r'<br>', h or '')
    return re.sub(r'(<br>\s*)+$', '', '<br>'.join(x for x in parts if not st(x).startswith('»')))


COL_OF = {c['trophy']: c['type'] for c in COLS if c.get('trophy')}
# missable trophies: the roadmap line "Number of missable trophies: 16 (A, B, …)" names them; a line like
# "Everything missable except for 10 story-related bosses" means all but those whose notes say story / can't miss.
ROAD_TXT = ' '.join(st(b.get('html', '')) + ' ' + ' '.join(st(x) for x in b.get('items', [])) for b in road_en)
_m = re.search(r'missable trophies\s*:?\s*(.{0,900}?)(?:Glitched trophies|Does difficulty|Hardest Trophy|Minimum Playthroughs|$)', ROAD_TXT, re.I)
MISS_LINE = _m.group(1) if _m else ''
MISS_ALL = bool(re.search(r'\b(everything|all)\b[^.]{0,40}\bmissable\b|\bmissable\b[^.]{0,20}\bexcept\b', MISS_LINE, re.I))
SAFE_RX = re.compile(r"story[- ]related and cannot be missed|can(no|’|')t (be )?miss|cannot be missed|\*Story Boss\*|unmissable|mandatory story boss"
                     r"|come[s]? automatically|automatic story", re.I)


def trophy_missable(t):
    if t['grade'] == 'platinum':
        return False
    if MISS_ALL:
        return not SAFE_RX.search(st(t['detail_en']) + ' ' + t['desc_en'])
    if MISS_LINE and re.search(r'[A-Za-z]', MISS_LINE):
        return t['name_en'] in MISS_LINE
    return bool(re.search(r"(?<!un)\*?missable\b", st(t['detail_en'])[:120], re.I))  # no roadmap list: a leading "MISSABLE" note
BOSS_TRO = []  # (trophy index, names) — linked after the loop, most specific names first
END_RX = re.compile(r'ending', re.I)
trophies = []
for i, t in enumerate(trophies_en):
    nm = t['name_en']
    tro = {'id': f't{i}', 'grade': t['grade'], 'name': {'zh': TRZH.get(nm, gz(nm)), 'en': nm},
           'desc': {'zh': tm(f'trophy-{i}-desc', H.escape(t['desc_en'])), 'en': t['desc_en']},
           'detail': {'zh': drop_links(tm(f'trophy-{i}-detail', t['detail_en'])), 'en': drop_links(t['detail_en'])}, 'videos': t['videos']}
    cat = 'other'
    if t['grade'] == 'platinum':
        cat = 'other'
    elif nm in COL_OF and cols.get(COL_OF[nm]):
        cat, tro['col'] = 'col', cols[COL_OF[nm]]
    elif END_RX.search(t['desc_en']) and re.search(r'^(Achieved?|Attain(ed)?|Get|Got|Reach(ed)?|See|Saw|Unlock(ed)?|Complete[ds]?|View(ed)?|Watch(ed)?)\b', t['desc_en']):
        cat = 'ending'
        tro['items'] = [it['id'] for it in all_items if (it['type'] in ('ending', 'save') and nm.lower() in it['_txt'].lower())
                        or (it.get('_para') and it['_para'][0] in ('ending', 'save') and nm.lower() in it['_para'][1].lower())]
    elif re.match(r'(Defeat(ed)?|Encounter(ed)?|Beat(en)?|Kill(ed)?|Slay|Slain|Slew|Caught|Captured)\b', t['desc_en']):
        cat = 'boss'
        # boss names: quoted names in the description ('Defeated “Lady Butterfly”') or its object, plus the trophy name
        names = re.findall(r'[“"]([^”"]+)[”"]', t['desc_en']) or [re.sub(r'^(Defeat(ed)?|Encounter(ed)?|Beat(en)?|Kill(ed)?|Caught)\s+(the\s+)?', '', t['desc_en']).split(' at the ')[0].strip(' .')]
        names = list(dict.fromkeys(names + [nm]))
        BOSS_TRO.append((i, names))
        ids = []
        tro['items'] = list(dict.fromkeys(ids))
        for iid in tro['items']:
            it = next(x for x in all_items if x['id'] == iid)
            if f't{i}' not in it['tro']:
                it['tro'].append(f't{i}')
    tro['cat'] = cat
    # "Complete [Flesh Lily], [Apprentice Healer] …": link the quest items whose title starts with a bracketed name
    names = [x.strip() for x in re.findall(r'\[([^\]]+)\]', t['desc_en'])]
    if names and 'col' not in tro:
        def qname(it):
            h = re.sub(r'^#[\d &#]+[–-]\s*', '', st(it['head']['en']))
            return re.sub(r'\s*[–-]\s*MISSABLE.*$', '', h, flags=re.I)
        linked = [it for it in all_items if it['check'] and any(qname(it).lower().startswith(n.lower()) for n in names)]
        if linked:
            tro['items'] = [it['id'] for it in linked]
            tro['quests'] = names
            for it in linked:
                if tro['id'] not in it['tro']:
                    it['tro'].append(tro['id'])
    if trophy_missable(t):
        tro['miss'] = True
    rx_link = cfg.get('trophy_links', {}).get(nm)  # manual: trophy -> regex over route item titles
    if rx_link and 'col' not in tro:
        linked = [it for it in all_items if it['check'] and re.search(rx_link, st(it['head']['en']))]
        tro['items'] = list(dict.fromkeys(tro.get('items', []) + [it['id'] for it in linked]))
        for it in linked:
            if tro['id'] not in it['tro']:
                it['tro'].append(tro['id'])
        if not linked:
            report['warn'].append(f'trophy_links "{nm}": no route item matches {rx_link}')
    trophies.append(tro)

# ---------------- platinum mode vs completionist mode ----------------
# need: how many entries of a collection the trophy really asks for (first number in the trophy description,
#       "Collect 10 Memory Flowers" -> 10; "Find all …" -> everything), overridable with collections[].need.
# opt : a checkable item is optional for the platinum when every tag it has is a non-platinum type
#       (game.json non_platinum_types) or a partial collection (need < total), and it carries no other trophy.
NONPLAT = set(cfg.get('non_platinum_types', []))
COL_NEED = {c['type']: c.get('need') for c in COLS}
COL_NOTE = {c['type']: c.get('need_note') for c in COLS}
partial, partial_tro = set(), set()
for tro in trophies:
    if not tro.get('col'):
        continue
    key, total = COL_OF[tro['name']['en']], len(tro['col'])
    need = COL_NEED.get(key)
    if COL_NOTE.get(key):
        tro['needNote'] = COL_NOTE[key]
    if need == 'manual':  # the trophy counts something else (e.g. complete flowers made of several petals)
        partial.add(key)
        partial_tro.add(tro['id'])
        continue
    if need is None:
        m = re.search(r'\b(\d+)\b', tro['desc']['en'])
        need = int(m.group(1)) if m and not re.search(r'\ball\b', tro['desc']['en'], re.I) else total
    if need > total:
        report['warn'].append(f'{tro["name"]["en"]}: trophy asks for {need} but the checklist has only {total} entries')
        need = total
    tro['need'] = need
    if need < total:
        partial.add(key)
        partial_tro.add(tro['id'])
soft = NONPLAT | partial
n_opt = 0
for it in all_items:
    tags = set(it['_tags']) - {'tip', 'warn'}
    if it['check'] and tags and tags <= soft and not [t for t in it['tro'] if t not in partial_tro]:
        it['opt'] = True
        n_opt += 1
MODE = {'enabled': bool(n_opt or partial)}
MODE['default'] = cfg.get('default_mode') or ('plat' if MODE['enabled'] else 'all')

claimed = {}
REWARD_OF_RX = re.compile(r"(?:reward(?:ed)? (?:for|from|after) (?:defeating|killing|beating)|dropped by|obtained (?:by|after|for) defeating)"
                          r"\s+(?:the\s+)?([^.;]{3,120})", re.I)
ITEM_BY_ID = {it['id']: it for it in all_items}
for ti, tro in enumerate(trophies):
    iid = REWARD_TRO.get(tro['name']['en'])
    if iid and not tro.get('col'):
        it = ITEM_BY_ID[iid]
        tro['items'] = [iid]
        if tro['id'] not in it['tro']:
            it['tro'].append(tro['id'])
        names = dict(BOSS_TRO).get(ti, [tro['name']['en']])
        claimed.setdefault(iid, []).append({w.lower() for n in names for w in name_words(n)})
for ti, names in sorted(BOSS_TRO, key=lambda x: -max(len(name_words(n)) for n in x[1])):
    if trophies[ti]['name']['en'] in REWARD_TRO:
        continue
    tw = {w.lower() for n in names for w in name_words(n)}
    hits = [it for it in boss_items(names) if not any(tw < cw for cw in claimed.get(it['id'], []))]
    at = re.search(r'\bat the ([A-Z][^.]+?)\s*\.?$', trophies[ti]['desc']['en'])  # 'Defeated “Great Shinobi – Owl” at the Hirata Estate'
    if at:
        here = [it for it in hits if at.group(1) in item_title(it) or at.group(1) in it['_area_en']]
        hits = here or hits
    # the note may say which fight counts: "doesn't unlock from the first “Corrupted Monk” … it's the 2nd one"
    note = st(trophies[ti]['detail']['en'])
    if len(hits) > 1 and (re.search(r"\b(not|n[’']t)\b[^.]{0,40}\bfirst\b", note, re.I)
                          or any(re.search(r"\b(2nd|second)\b\W{0,3}(\w+\W+){0,2}" + re.escape(n), note, re.I) for n in names)):
        hits = hits[1:]
    if hits:
        it = hits[0]
        claimed.setdefault(it['id'], []).append(tw)
        trophies[ti]['items'] = [it['id']]
        if f't{ti}' not in it['tro']:
            it['tro'].append(f't{ti}')
    else:
        # no fight checkbox (Phantom Blade Zero lists bosses only through their drops): link the items whose text says
        # they are the reward for defeating this boss — ticking the drop means the fight is won
        obj = names[0].split(':')[-1]
        parts = [re.sub(r'^the\s+', '', x.strip(), flags=re.I) for x in re.split(r',\s*and\s+|\s+and\s+|,\s*(?=[A-Z])', obj) if x.strip()]
        parts = list(dict.fromkeys(parts + [p.split(', ')[0] for p in parts if len(name_words(p.split(', ')[0])) > 1]))  # "Hua" alone is ambiguous
        hit_ids = []
        for it in all_items:
            if not it['check']:
                continue
            for x in REWARD_OF_RX.findall(st(it['body']['en'])):
                if any(loose_hit(n, x) for n in parts):
                    hit_ids.append(it['id'])
                    if f't{ti}' not in it['tro']:
                        it['tro'].append(f't{ti}')
                    break
        if hit_ids:
            trophies[ti]['items'] = hit_ids

# 奖杯前置 (gates-brief.md): skippable prerequisites the guide states — reviewed by the user, then tr_out/gates.json
TRO_BY_EN = {t['name']['en']: t for t in trophies}
ITEM_BY_ID = {it['id']: it for it in all_items}
n_gate = 0
for f in sorted(glob.glob(os.path.join(W, 'tr_out', 'gates*.json'))):
    for g in json.load(open(f, encoding='utf-8')).get('gates', []):
        it = ITEM_BY_ID.get(g.get('item'))
        tids = [TRO_BY_EN[n]['id'] for n in g.get('trophies', []) if n in TRO_BY_EN]
        if it is None or not tids:
            report['warn'].append(f"gate {g.get('item')} / {g.get('trophies')}: unknown item or trophy")
            continue
        new = [t for t in tids if t not in it['tro'] and t not in it.get('pre', [])]
        if not new:
            continue
        if g.get('level') == 'self':  # the checkbox itself pops the trophy (final shop hand-in): gold chip, not 前置
            for t in new:
                it['tro'].append(t)
                tr = next(x for x in trophies if x['id'] == t)
                tr['items'] = list(dict.fromkeys(tr.get('items', []) + [it['id']])) if not tr.get('col') else tr.get('items')
            it.pop('opt', None)
            n_gate += 1
            continue
        it['pre'] = it.get('pre', []) + new
        it.pop('opt', None)  # the platinum needs it after all
        it['preNote'] = {'zh': '奖杯前置：' + (g.get('reason_zh') or g.get('reason_en', '')), 'en': 'Prerequisite: ' + (g.get('reason_en') or g.get('skippable', ''))}
        for t in new:
            tr = next(x for x in trophies if x['id'] == t)
            tr.setdefault('pre', []).append(it['id'])
        n_gate += 1
if n_gate:
    print('trophy prerequisites (前置):', n_gate)

# route items behind a missable boss / ending / other trophy (not collections — those have per-entry flags) are missable too
MISS_TRO = {tro['id'] for tro in trophies if tro.get('miss') and not tro.get('col')}
n_miss_tro = 0
for it in all_items:
    if it['check'] and not it['miss'] and set(it['tro']) & MISS_TRO:
        it['miss'] = True
        n_miss_tro += 1
if n_miss_tro:
    print('items flagged missable via a missable trophy:', n_miss_tro)

# ---------------- questlines ----------------
qcfg = cfg.get('questlines', {'mode': 'guide'})
questlines = []
if qcfg.get('mode', 'guide') == 'guide':
    for qi, q in enumerate(ql_en.get('questlines', [])):
        base = q['name_en'].split(' (')[0]
        pats = [re.escape(x.strip()) for x in base.split('&')] + qcfg.get('aliases', {}).get(q['name_en'], [])
        ids = [it['id'] for it in all_items if any(re.search(p, st(it['head']['en'])) for p in pats)]
        ien, izh = [], []
        for bi, b in enumerate(q['blocks']):
            if b['k'] == 'p' and b.get('lead'):
                break
            if b['k'] == 'p' and st(b['html']):
                ien.append(f'<p>{b["html"]}</p>')
                izh.append(f'<p>{tm(f"ql{qi}-p{bi}", b["html"])}</p>')
            elif b['k'] == 'ul':
                ien.append('<ul>' + ''.join(f'<li>{x}</li>' for x in b['items']) + '</ul>')
                izh.append('<ul>' + ''.join(f'<li>{tm(f"ql{qi}-ul{bi}-{j}", x)}</li>' for j, x in enumerate(b['items'])) + '</ul>')
        zh = qcfg.get('name_zh', {}).get(q['name_en']) or ' & '.join(gz(x.strip()) for x in base.split('&'))
        req = bool(re.search(r'needed for|required|trophy', q.get('group_en', ''), re.I)) and not re.search(r'not needed|optional', q.get('group_en', ''), re.I)
        questlines.append({'id': f'q{qi}', 'name': {'zh': zh, 'en': q['name_en']}, 'req': req, 'reward': {'zh': '', 'en': ''},
                           'intro': {'zh': ''.join(izh), 'en': ''.join(ien)}, 'items': ids, 'anchor': q.get('id') or re.sub(r'[^a-z0-9]+', '-', base.lower()).strip('-')})
elif qcfg.get('mode') == 'tag':
    tag = qcfg['tag']
    starters = [it for it in all_items if tag in it['_tags'] and it['check']]
    trophy_text = ' '.join(t['desc_en'] + ' ' + st(t['detail_en']) for t in trophies_en)
    for qi, it in enumerate(starters):
        nm = re.sub(r'^#\s*\d+\s*[–-]\s*', '', st(it['head']['en']))
        nm = re.sub(r'\s*\((?:Tales?|Side ?(?:Quest|Tale)s?)\)\s*.*$', '', nm).strip()
        nzh = re.sub(r'^#\s*\d+\s*[–-]\s*', '', st(it['head']['zh']))
        nzh = re.sub(r'\s*[（(][^）)]*[）)].*$', '', nzh).strip() or nm
        members = [it['id']] + [x['id'] for x in all_items if x is not it and st(x['head']['en']).startswith(nm)]
        questlines.append({'id': f'q{qi}', 'name': {'zh': nzh, 'en': nm}, 'req': any(nm.lower() == n.lower() for t in trophies for n in t.get('quests', [])) or f'[{nm}]' in trophy_text, 'reward': {'zh': '', 'en': ''},
                           'intro': {'zh': '', 'en': ''}, 'items': members, 'anchor': ''})


# ---------------- endings ----------------
def blocks_html(blocks, prefix, start=0, end=None):
    zh, en = [], []
    for i, b in enumerate(blocks):
        if i < start or (end is not None and i >= end):
            continue
        if b['k'] == 'h':
            en.append(f'<h3>{H.escape(b["text"])}</h3>')
            zh.append(f'<h3>{tm(f"{prefix}-h{i}", H.escape(b["text"]))}</h3>')
        elif b['k'] == 'p' and st(b['html']):
            en.append(f'<p>{b["html"]}</p>')
            zh.append(f'<p>{tm(f"{prefix}-p{i}", b["html"])}</p>')
        elif b['k'] == 'ul':
            en.append('<ul>' + ''.join(f'<li>{x}</li>' for x in b['items']) + '</ul>')
            zh.append('<ul>' + ''.join(f'<li>{tm(f"{prefix}-ul{i}-{j}", x)}</li>' for j, x in enumerate(b['items'])) + '</ul>')
    return {'zh': ''.join(zh), 'en': ''.join(en)}


endings, endings_all = [], None
ERX = re.compile(cfg.get('endings', {}).get('heading_regex', r'^Ending (\d+): (.*?)(?: \((.*)\))?$'))
hidx = [i for i, b in enumerate(endings_en) if b['k'] == 'h' and b['level'] == 2]
for k, hi in enumerate(hidx):
    nxt = hidx[k + 1] if k + 1 < len(hidx) else len(endings_en)
    title = endings_en[hi]['text']
    vids = [b['src'] for b in endings_en[hi:nxt] if b['k'] == 'video'] + [v for b in endings_en[hi:nxt] for v in b.get('videos', [])]
    body = blocks_html(endings_en, 'end', hi + 1, nxt)
    m = ERX.match(title)
    if m:
        num, nm = m.group(1), m.group(2)
        tro_nm = nm if nm in TROPHY_ID else next((t['name_en'] for t in trophies_en if re.search(r'[“"]' + re.escape(nm) + r'[”"]', t['desc_en'])), nm)
        endings.append({'id': f'e{num}', 'title': {'zh': f'结局{num}：{TRZH.get(tro_nm, gz(nm))}', 'en': title},
                        'sub': ({'zh': tm(f'end-h{hi}', H.escape(title)), 'en': m.group(3)} if m.lastindex and m.lastindex >= 3 and m.group(3)
                                else {'zh': '', 'en': ''}),  # only "(Bad Ending)"-style qualifiers make a subtitle
                        'html': body, 'videos': vids, 'trophy': TROPHY_ID.get(tro_nm, '')})
    elif st(body['en']) and (endings_all is None or (re.search(r'one (run|playthrough)|combine|all endings', title, re.I)
                                                      and not re.search(r'one (run|playthrough)|combine|all endings', endings_all['title']['en'], re.I))):
        t_zh = tm(f'end-h{hi}', H.escape(title)) if title else '一周目全结局方案'
        endings_all = {'title': {'zh': t_zh or '一周目全结局方案', 'en': title or 'All endings'}, 'html': body}


# ---------------- roadmap / hub intro ----------------
def collect(blocks, prefix):
    zh, en = [], []
    for i, b in enumerate(blocks):
        if b['k'] == 'h':
            en.append(f'<h3>{H.escape(b["text"])}</h3>')
            zh.append(f'<h3>{tm(f"{prefix}-h{i}", H.escape(b["text"]))}</h3>')
        elif b['k'] == 'p' and st(b['html']):
            en.append(f'<p>{b["html"]}</p>')
            zh.append(f'<p>{tm(f"{prefix}-p{i}", b["html"])}</p>')
        elif b['k'] == 'ul':
            en.append('<ul>' + ''.join(f'<li>{x}</li>' for x in b['items']) + '</ul>')
            zh.append('<ul>' + ''.join(f'<li>{tm(f"{prefix}-ul{i}-{j}", x)}</li>' for j, x in enumerate(b['items'])) + '</ul>')
    return {'zh': ''.join(zh), 'en': ''.join(en)}


roadmap = {'title': {'zh': '白金路线概览', 'en': 'Trophy Roadmap Overview'}, 'html': collect(road_en, 'road')}
hub = collect(hub_en, 'hub')
for reg, r_en in zip(regions, areas_en):
    trr = TRR.get(reg['id'], {})
    ez, ee = trr.get('colinfo_zh', ''), trr.get('colinfo_en', '')
    iz = ie = ''
    if cfg.get('step_mode', 'page') != 'page' and r_en['areas']:
        a0 = r_en['areas'][0]
        ie = a0.get('intro_en', '')
        iz = TRA.get(a0['id'], {}).get('intro') or ie
    reg['colInfo'] = {'zh': (f'<p>{ez}</p>' if ez else '') + (f'<div>{iz}</div>' if iz else '') + hub['zh'],
                      'en': (f'<p>{ee}</p>' if ee else '') + (f'<div>{ie}</div>' if ie else '') + hub['en']}
qintro = {'zh': '', 'en': ''}
for bi, b in enumerate(ql_en.get('intro', [])):
    if b['k'] == 'p' and st(b['html']):
        qintro['en'] += f'<p>{b["html"]}</p>'
        qintro['zh'] += f'<p>{tm(f"qlintro-p{bi}", b["html"])}</p>'

# ---------------- trophy-guide steps in the route (callouts-brief.md, sample_ui/8.png) ----------------
# save backups / reloads, ending branches, points of no return and "finish X first" as cards without checkbox;
# story trophies as 「成」 checkboxes where they pop; 【不可回头点】 tags on checkpoints
CALL = {'callouts': [], 'trophies': [], 'noreturn': []}
for f in sorted(glob.glob(os.path.join(W, 'tr_out', 'callouts*.json'))):
    o = json.load(open(f, encoding='utf-8'))
    for k in CALL:
        CALL[k] += o.get(k, [])
if any(CALL.values()):
    TYPES.setdefault('trophy', {'zh': '奖杯', 'en': 'Trophy', 'badge': {'zh': '成', 'en': 'T'}, 'stat': False})
    TYPES.setdefault('save', {'zh': '存档', 'en': 'Save', 'badge': {'zh': '存', 'en': 'SV'}, 'stat': False})
    TRO_BY_EN = {t['name']['en']: t for t in trophies}

    def place(where, iid, x):
        for r in regions:
            for a in r['areas']:
                for sec in a['sections']:
                    ids = [y['id'] for y in sec['items']]
                    if iid in ids:
                        k = ids.index(iid)
                        host = sec['items'][k]
                        if where == 'after':
                            k += 1
                            while k < len(ids) and ids[k].startswith(iid + '-col-'):  # keep a fight's drops with it
                                k += 1
                            k += AFTER_N.get(iid, 0)  # several cards after one item keep their listed order
                            AFTER_N[iid] = AFTER_N.get(iid, 0) + 1
                        x.update({'_area_en': host['_area_en'], '_region': host['_region'], '_txt': st(x['body']['en'])})
                        sec['items'].insert(k, x)
                        all_items.append(x)
                        return True
        report['warn'].append(f"callout target not found: {iid}")
        return False

    n_c = n_t = 0
    AFTER_N = {}
    for k, c in enumerate(CALL['callouts']):
        kind = 'save' if c.get('kind') == 'save' else 'warn'
        x = {'id': f"call-{k}", 'type': kind, 'check': False, 'style': kind,
             'head': {'zh': c.get('title_zh', ''), 'en': c.get('title_en', '')}, 'body': {'zh': c.get('body_zh', ''), 'en': c.get('body_en', '')},
             'miss': False, 'tro': [], 'stags': [], 'imgs': [], 'videos': [], '_tags': [kind]}
        n_c += place(c.get('where', 'before'), c['item'], x)
    for c in CALL['trophies']:
        tr = TRO_BY_EN.get(c.get('trophy'))
        if not tr:
            report['warn'].append(f"callout trophy unknown: {c.get('trophy')}")
            continue
        x = {'id': f"tro-{tr['id']}", 'type': 'trophy', 'check': True, 'style': '', 'head': dict(tr['name']),
             'body': {'zh': c.get('body_zh', ''), 'en': c.get('body_en', '')}, 'miss': bool(tr.get('miss')), 'tro': [tr['id']],
             'stags': [], 'imgs': [], 'videos': [], '_tags': ['trophy']}
        if place(c.get('where', 'after'), c['item'], x):
            n_t += 1
            if not tr.get('col'):
                tr['items'] = list(dict.fromkeys(tr.get('items', []) + [x['id']]))
    ITEM_BY_ID = {it['id']: it for it in all_items}
    for c in CALL['noreturn']:
        if c.get('item') in ITEM_BY_ID:
            ITEM_BY_ID[c['item']]['noreturn'] = True
    print('trophy-guide steps in the route:', n_c, 'cards,', n_t, 'trophy items,', len(CALL['noreturn']), 'points of no return')

# ---------------- output ----------------
n_titles = 0
for it in all_items:
    t = TRT.get(it['id'])
    if t and t.get('zh'):
        it['head'] = {'zh': t['zh'], 'en': t.get('en') or it['head']['en']}
        n_titles += 1
if TRT:
    print('short titles applied:', n_titles)
if MISSING_TXT:  # ready-made translation job for units that have no Chinese yet
    json.dump({'job': 'missing_units', 'units': [{'id': k, 'text': v} for k, v in MISSING_TXT.items()]},
              open(os.path.join(W, 'tr_in', 'missing_units.json'), 'w'), ensure_ascii=False, indent=1)
    print('  -> tr_in/missing_units.json: translate these units into tr_out/<job>.json {"units": {id: 中文}}')
for it in all_items:
    for k in [k for k in it if k.startswith('_')]:
        del it[k]
g = cfg['game']
data = {
    'storageKey': f'{g["slug"]}-platinum-helper-v1',
    'game': {'zh': g['zh'], 'en': g['en'], 'short': {'zh': g.get('short_zh', g['zh']), 'en': g.get('short_en', g['en'])}},
    'lang': {'default': LANG, 'bilingual': not EN_ONLY},
    'types': TYPES, 'statOrder': STAT_ORDER, 'regions': regions, 'trophies': trophies, 'questlines': questlines, 'mode': MODE,
    'endings': endings, 'endingsAll': endings_all, 'roadmap': roadmap,
    'side': {'title': {'zh': '结局与支线' if endings else '支线', 'en': 'Endings & Quests' if endings else 'Quests'},
             'intro': qintro, 'url': cfg.get('pages', {}).get('questlines') or cfg['sources']['collectibles_guide']},
    'about': {'zh': f'内容翻译整理自 PowerPyx 的《{g["en"]}》奖杯指南与全收集指南。勾选进度保存在本机浏览器中，可在此导出备份。',
              'en': f'Content adapted from PowerPyx’s {g["en"]} Trophy Guide and Collectible Guide. Progress is stored in this browser; export it here to back it up.'},
}
EN_BTN = [('左摇杆', 'L-Stick '), ('右摇杆', 'R-Stick '), ('触摸板', 'Touchpad')]  # ppx writes controller buttons in Chinese


def en_buttons(o):  # … so English fields (EN toggle / English-only pages) get English button names
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'en' and isinstance(v, str) and '[' in v:
                for a, b in EN_BTN:
                    v = v.replace('[' + a, '[' + b)
                o[k] = v
            else:
                en_buttons(v)
    elif isinstance(o, list):
        for v in o:
            en_buttons(v)


en_buttons(data)
js = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
for a, b in cfg.get('zh_replacements', []):
    js = js.replace(a, b)
js = js.replace('</', '<\\/')
tpl = open(TEMPLATE, encoding='utf-8').read()
out = tpl.replace('__TITLE__', f'{g["en"]} Platinum Helper' if EN_ONLY else f'{g["zh"]} 白金小助手').replace('__DATA__', js).replace('__IMGS__', json.dumps(IMG, separators=(',', ':')))
os.makedirs(os.path.dirname(os.path.abspath(OUT_HTML)), exist_ok=True)
open(OUT_HTML, 'w', encoding='utf-8').write(out)
if images.get('mode') == 'folder':
    import shutil
    dst = os.path.join(os.path.dirname(os.path.abspath(OUT_HTML)), 'images')
    os.makedirs(dst, exist_ok=True)
    for ent in images.get('map', {}).values():
        if ent.get('file'):
            shutil.copy(os.path.join(W, ent['file']), dst)
json.dump(report, open(os.path.join(W, 'assemble_report.json'), 'w'), ensure_ascii=False, indent=1)
print('wrote', OUT_HTML, len(out) // 1024, 'KB; images:', images.get('mode'), len(IMG))
print('items', len(all_items), 'checkable', sum(1 for i in all_items if i['check']), '| trophies', len(trophies), '| questlines', len(questlines), '| endings', len(endings))
print('collections', {k: len(v) for k, v in cols.items()})
print('platinum mode:', MODE, '| optional items', n_opt, '| partial collections',
      {t['name']['en']: (f"{t['need']}/{len(t['col'])}" if t.get('need') else 'manual') for t in trophies
       if t.get('col') and (not t.get('need') or t['need'] < len(t['col']))})
if partial:
    print('  -> check each partial collection against the trophy text: does the number count these entries, or groups of them?')
print('missing translations', len(report['missing_unit']), '| unlinked', len(report['unlinked']), '| warnings', len(report['warn']))
for x in report['warn'][:10]:
    print('  WARN', x)
