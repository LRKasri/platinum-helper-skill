"""Stage 7b: screenshot QA with headless Chromium (Playwright).

usage: <venv>/bin/python shot.py <html> <outdir> [name=js ...]
With no name=js actions it runs the standard suite below and prints JS errors.
Setup once (keep it out of the project, e.g. in the session scratchpad):
  python3 -m venv <scratch>/pwenv && <scratch>/pwenv/bin/pip install -q playwright
  PLAYWRIGHT_BROWSERS_PATH=<scratch>/pw <scratch>/pwenv/bin/python -m playwright install chromium
and run with the same PLAYWRIGHT_BROWSERS_PATH. Then Read the PNGs to look at them.
"""
import sys, asyncio, os
from playwright.async_api import async_playwright

SUITE = [
    ('01_route_top', ''),
    ('02_route_items', "window.scrollTo(0, document.querySelector('.steps').getBoundingClientRect().top + scrollY - 140)"),
    ('03_checked', "document.querySelectorAll('.it .cb')[0].click(); document.querySelectorAll('.it .cb')[1].click(); window.scrollTo(0, document.querySelector('.steps').getBoundingClientRect().top + scrollY - 140)"),
    ('04_english', "document.getElementById('langBtn').click(); window.scrollTo(0, document.querySelector('.steps').getBoundingClientRect().top + scrollY - 140)"),
    ('05_missables', "document.getElementById('langBtn').click(); document.querySelector('[data-f=onlyMiss]').click(); window.scrollTo(0, 700)"),
    ('06_screenshot', "document.querySelector('[data-f=onlyMiss]').click(); const b=document.querySelector('[data-imgs]'); if(b){ const r=b.closest('[data-id]'); b.click(); r.scrollIntoView(); scrollBy(0,-160);}"),
    ('07_region2', "document.querySelectorAll('.rtab')[1] && document.querySelectorAll('.rtab')[1].click()"),
    ('08_trophies', "document.querySelector('[data-tab=trophy]').click()"),
    ('09_trophy_list', "const c=[...document.querySelectorAll('.tro-card')].find(x=>x.querySelector('.tp .bar')); if(c){ c.querySelector('.bh').click(); c.scrollIntoView(); scrollBy(0,300);}"),
    ('10_quests', "document.querySelector('[data-tab=side]').click(); const q=document.querySelector('.ql-card .bh'); if(q){ q.click(); q.scrollIntoView(); scrollBy(0,-100);}"),
    ('11_search', "const i=document.getElementById('q'); i.value=(window.__q||'Boss'); i.dispatchEvent(new Event('input'))"),
]


async def main():
    html, outdir = os.path.abspath(sys.argv[1]), sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    acts = [a.split('=', 1) for a in sys.argv[3:]] or SUITE
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 412, 'height': 900})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        await pg.goto('file://' + html)
        await pg.wait_for_timeout(600)
        for name, js in acts:
            if js:
                try:
                    await pg.evaluate(js)
                except Exception as e:
                    errs.append(f'{name}: {e}')
                await pg.wait_for_timeout(1200 if 'imgs' in js else 350)
            await pg.screenshot(path=f'{outdir}/{name}.png', full_page=name.endswith('_full'))
        if not sys.argv[3:]:
            await pg.set_viewport_size({'width': 1280, 'height': 900})
            await pg.evaluate("document.getElementById('qclr').click(); document.querySelector('[data-tab=route]').click()")
            await pg.wait_for_timeout(300)
            await pg.screenshot(path=f'{outdir}/12_desktop.png')
        print('screenshots ->', outdir)
        print('errors:', errs)
        await b.close()

asyncio.run(main())
