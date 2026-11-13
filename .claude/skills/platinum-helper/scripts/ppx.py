"""PowerPyx article parser -> simplified block list.

Block kinds:
  {"k":"h","level":2,"text":...}
  {"k":"p","html":...,"strong_lead":header-or-None,"rest":html,"red":bool,"em_only":bool,"imgs":[...]}
  {"k":"ul","items":[html,...]}
  {"k":"img","imgs":[...]}
  {"k":"video","src":...}
  {"k":"table","rows":[[cell_html,...],...]}
Simplified HTML keeps: <b>, <i>, <span class="red">, <br>, <u>, trophy markers <t class="bronze|silver|gold|platinum"></t>
"""
import re, html as H
from html.parser import HTMLParser

VOID = {'br', 'img', 'hr', 'input', 'meta', 'link', 'source', 'wbr'}


class Node:
    __slots__ = ('tag', 'attrs', 'children', 'parent')

    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs, self.children, self.parent = tag, dict(attrs or {}), [], parent


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root')
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def body_of(raw):
    i = raw.find('entry-content')
    i = raw.find('>', i) + 1
    j = raw.find('prevnextmd_wrapper', i)
    if j < 0:
        j = raw.find('entry-footer', i)
    b = raw[i:j]
    b = re.sub(r'<script.*?</script>', '', b, flags=re.S)
    b = re.sub(r'<div class=.code-block.*', '', b, flags=re.S) if False else b
    return b


def parse_tree(fragment):
    tb = TreeBuilder()
    tb.feed(fragment)
    return tb.root


def is_red(n):
    st = n.attrs.get('style', '') if isinstance(n, Node) else ''
    return 'ff0000' in st.lower() or 'color: red' in st.lower()


def trophy_of(n):
    alt = n.attrs.get('alt', '')
    m = re.match(r':(bronze|silver|gold|platinum):', alt)
    if m:
        return m.group(1)
    src = n.attrs.get('src', '')
    if 'smilies/' in src:
        return re.sub(r'.*smilies/([\w-]+)\.(png|gif|svg).*', r'\1', src)
    return None


BUTTONS = {  # PowerPyx renders controller buttons as smiley images
    'o': '○', 'x': '✕', 'square': '□', 'triangle': '△', 'l1': 'L1', 'r1': 'R1', 'l2': 'L2', 'r2': 'R2', 'l3': 'L3', 'r3': 'R3',
    'l-up': '左摇杆↑', 'l-down': '左摇杆↓', 'l-left': '左摇杆←', 'l-right': '左摇杆→', 'r-up': '右摇杆↑', 'r-down': '右摇杆↓',
    'r-left': '右摇杆←', 'r-right': '右摇杆→', 'up': '↑', 'down': '↓', 'left': '←', 'right': '→',
    'options': 'OPTIONS', 'share': 'SHARE', 'touchpad': '触摸板', 'a': 'A', 'b': 'B', 'y': 'Y', 'lb': 'LB', 'rb': 'RB', 'lt': 'LT', 'rt': 'RT',
}


def lazy_iframe(n):
    """WP lazy-load placeholder <img data-lazy-type="iframe" data-lazy-src="<iframe src=…>"> -> video url"""
    if n.attrs.get('data-lazy-type') == 'iframe':
        m = re.search(r'src=["\']([^"\']+)', H.unescape(n.attrs.get('data-lazy-src', '')))
        return m.group(1) if m else ''
    return None


def img_src(n):
    """Return best image url for screenshot img (prefer linked full-size, else largest srcset)."""
    if lazy_iframe(n) is not None:
        return None
    src = n.attrs.get('data-lazy-src') or n.attrs.get('data-src') or n.attrs.get('src', '')
    if src.startswith('data:'):
        return None
    if 'smilies' in src or 'trophy' in src:
        return None
    ss = n.attrs.get('srcset', '')
    best = None
    for part in ss.split(','):
        part = part.strip()
        m = re.match(r'(\S+)\s+(\d+)w', part)
        if m and int(m.group(2)) <= 1280:
            if best is None or int(m.group(2)) > best[1]:
                best = (m.group(1), int(m.group(2)))
    return best[0] if best else src


def simplify(n, out, ctx):
    """Render node children to simplified html, collecting imgs/videos into ctx."""
    if isinstance(n, str):
        out.append(H.escape(n, quote=False))
        return
    t = n.tag
    if t in ('script', 'style', 'noscript'):
        return
    if t == 'img':
        vid = lazy_iframe(n)
        if vid is not None:
            if 'youtube' in vid:
                ctx['videos'].append(vid)
            return
        tr = trophy_of(n)
        if tr in BUTTONS:
            out.append(f'[{BUTTONS[tr]}]')
        elif tr and tr not in ('bronze', 'silver', 'gold', 'platinum'):
            out.append(f'[{tr}]')
        elif tr:
            out.append(f'<t class="{tr}"></t>')
        else:
            s = img_src(n)
            if s:
                ctx['imgs'].append(s)
        return
    if t == 'iframe':
        s = n.attrs.get('data-lazy-src') or n.attrs.get('data-src') or n.attrs.get('src', '')
        if 'youtube' in s:
            ctx['videos'].append(s)
        return
    if t == 'br':
        out.append('<br>')
        return
    if t == 'div' and 'rll-youtube-player' in n.attrs.get('class', ''):
        vid = n.attrs.get('data-id') or ''
        if vid:
            ctx['videos'].append('//www.youtube.com/embed/' + vid)
        return
    open_, close = '', ''
    if t in ('strong', 'b'):
        open_, close = '<b>', '</b>'
    elif t in ('em', 'i'):
        open_, close = '<i>', '</i>'
    elif t == 'span':
        st = n.attrs.get('style', '')
        if is_red(n):
            open_, close = '<span class="red">', '</span>'
        elif 'underline' in st:
            open_, close = '<u>', '</u>'
        elif '008000' in st or 'green' in st:
            open_, close = '<span class="green">', '</span>'
    elif t == 'a':
        href = n.attrs.get('href', '')
        if 'youtube.com/watch' in href or 'youtu.be' in href:
            ctx['videos'].append(href)
    elif t == 'li':
        open_, close = '<li>', '</li>'
    elif t in ('ul', 'ol'):
        open_, close = '<ul>', '</ul>'
    elif t == 'p':
        open_, close = '<br>', ''
    elif t == 'noscript':
        return
    out.append(open_)
    for c in n.children:
        simplify(c, out, ctx)
    out.append(close)


def clean_html(s):
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'(<br>\s*)+$', '', s.strip())
    s = re.sub(r'^(\s*<br>)+', '', s)
    s = re.sub(r'<b>\s*</b>|<i>\s*</i>|<span class="\w+">\s*</span>|<u>\s*</u>', '', s)
    s = s.replace('\xa0', ' ').strip()
    return s


def text_of(n):
    if isinstance(n, str):
        return n
    if n.tag in ('script', 'style'):
        return ''
    return ''.join(text_of(c) for c in n.children)


def render(n):
    ctx = {'imgs': [], 'videos': []}
    out = []
    for c in (n.children if isinstance(n, Node) else [n]):
        simplify(c, out, ctx)
    return clean_html(''.join(out)), ctx


def split_lead(p):
    """If paragraph starts with <strong>, return (lead_html, rest_html, red)."""
    kids = [c for c in p.children if not (isinstance(c, str) and not c.strip())]
    if not kids:
        return None
    first = kids[0]
    # unwrap red span that wraps strong
    red = False
    lead_nodes = []
    if isinstance(first, Node) and first.tag in ('strong', 'b'):
        lead_nodes = [first]
    elif isinstance(first, Node) and first.tag == 'span' and first.children:
        inner = [c for c in first.children if not (isinstance(c, str) and not c.strip())]
        if inner and isinstance(inner[0], Node) and inner[0].tag in ('strong', 'b'):
            lead_nodes = [first]
            red = is_red(first)
    if not lead_nodes:
        return None
    # collect consecutive strong/span-strong nodes until <br>
    idx = p.children.index(lead_nodes[0])
    lead = []
    rest_start = None
    for k in range(idx, len(p.children)):
        c = p.children[k]
        if isinstance(c, Node) and c.tag == 'br':
            rest_start = k + 1
            break
        if isinstance(c, Node) and c.tag in ('strong', 'b', 'span', 'img', 'a'):
            lead.append(c)
            continue
        if isinstance(c, str):
            lead.append(c)
            continue
        rest_start = k
        break
    lead_ctx = {'imgs': [], 'videos': []}
    lo = []
    for c in lead:
        simplify(c, lo, lead_ctx)
    lead_html = clean_html(''.join(lo))
    rest = p.children[rest_start:] if rest_start is not None else []
    ro = []
    ctx = {'imgs': list(lead_ctx['imgs']), 'videos': list(lead_ctx['videos'])}
    for c in rest:
        simplify(c, ro, ctx)
    return lead_html, clean_html(''.join(ro)), red, ctx


def blocks(fragment):
    root = parse_tree(fragment)
    res = []

    def walk(nodes):
        for n in nodes:
            if isinstance(n, str):
                if n.strip():
                    res.append({'k': 'p', 'html': H.escape(n.strip(), quote=False), 'lead': None, 'rest': '', 'imgs': [], 'videos': []})
                continue
            t = n.tag
            if t in ('h1', 'h2', 'h3', 'h4'):
                anchor = ''
                for c in n.children:
                    if isinstance(c, Node) and c.tag == 'a' and c.attrs.get('id'):
                        anchor = c.attrs['id']
                res.append({'k': 'h', 'level': int(t[1]), 'text': re.sub(r'\s+', ' ', text_of(n)).strip(), 'id': n.attrs.get('id', '') or anchor})
            elif t == 'p':
                sl = split_lead(n)
                full, ctx = render(n)
                if not full and not ctx['imgs'] and not ctx['videos']:
                    continue
                if sl:
                    lead, rest, red, c2 = sl
                    res.append({'k': 'p', 'html': full, 'lead': lead, 'rest': rest, 'red': red, 'imgs': c2['imgs'], 'videos': c2['videos']})
                else:
                    em_only = bool(re.fullmatch(r'(<span class="red">)?\s*(<b>)?\s*<i>.*</i>\s*(</b>)?\s*(</span>)?', full, re.S))
                    res.append({'k': 'p', 'html': full, 'lead': None, 'rest': full, 'em_only': em_only, 'red': 'class="red"' in full[:40], 'imgs': ctx['imgs'], 'videos': ctx['videos']})
            elif t in ('ul', 'ol'):
                items = []
                imgs, vids = [], []
                for li in n.children:
                    if isinstance(li, Node) and li.tag == 'li':
                        h, ctx = render(li)
                        items.append(h)
                        imgs += ctx['imgs']
                        vids += ctx['videos']
                res.append({'k': 'ul', 'items': items, 'imgs': imgs, 'videos': vids})
            elif t == 'table':
                rows = []
                for tr in iter_tag(n, 'tr'):
                    cells = []
                    for td in tr.children:
                        if isinstance(td, Node) and td.tag in ('td', 'th'):
                            h, ctx = render(td)
                            cells.append({'html': h, 'imgs': ctx['imgs'], 'videos': ctx['videos'], 'raw_imgs': [c.attrs for c in iter_tag(td, 'img')]})
                    rows.append(cells)
                res.append({'k': 'table', 'rows': rows})
            elif t == 'iframe' or (t == 'div' and 'rll-youtube-player' in n.attrs.get('class', '')):
                ctx = {'imgs': [], 'videos': []}
                simplify(n, [], ctx)
                for v in ctx['videos']:
                    res.append({'k': 'video', 'src': v})
            elif t in ('div', 'figure', 'center', 'blockquote', 'span', 'a', 'section'):
                cls = n.attrs.get('class', '')
                if any(x in cls for x in ('code-block', 'nc_socialPanel', 'swp', 'prevnext', 'ezoic', 'adsbygoogle')):
                    continue
                walk(n.children)
            elif t == 'img':
                s = img_src(n)
                if s:
                    res.append({'k': 'img', 'imgs': [s]})
    walk(root.children)
    return res


def iter_tag(n, tag):
    for c in n.children:
        if isinstance(c, Node):
            if c.tag == tag:
                yield c
            yield from iter_tag(c, tag)


SKIP_HEADINGS = re.compile(r'(Comments|Leave a Reply|Latest|Recent)')


def promote_headings(bl, level):
    """For guides that give every collectible its own <hN> ("Hydra / Box #4") followed by plain paragraphs:
    turn those headings into bold-lead paragraphs so they parse like <p><strong>Title</strong>… items."""
    out = []
    for b in bl:
        if b['k'] == 'h' and b['level'] == level and not SKIP_HEADINGS.match(b['text']):
            lead = '<b>' + H.escape(b['text'], quote=False) + '</b>'
            out.append({'k': 'p', 'html': lead, 'lead': lead, 'rest': '', 'red': False, 'imgs': [], 'videos': []})
        else:
            out.append(b)
    return out
