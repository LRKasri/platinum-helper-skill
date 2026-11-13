# Finding official Chinese names (glossary research)

The player plays in Chinese, so every place / boss / NPC / item / trophy name on the page must be the in-game
Chinese name, otherwise the guide can't be followed. Machine-translating names is the single biggest quality risk.
Wuchang needed ~570 terms; 3 research subagents in parallel took ~18 min and ~700k tokens total and reached
~85 % "official", ~13 % "likely", ~2 % "guess".

## Sources that worked (try in this order)

| source | good for | how |
|---|---|---|
| Steam achievements page `https://steamcommunity.com/stats/<appid>/achievements/?l=schinese` | official trophy/achievement names + descriptions (PC releases) | WebFetch; appid from the store URL |
| PSNine `psnine.com/psngame/<id>` | official PlayStation trophy names in Chinese | WebSearch "<中文游戏名> 奖杯 psnine" |
| B站 wiki `wiki.biligame.com/<wikiid>/` | item / weapon / spell / NPC / achievement lists with in-game text | find via WebSearch "<中文游戏名> wiki biligame". Rate-limits with HTTP 567 after a few page loads. Use the MediaWiki API instead: `api.php?action=query&prop=revisions&rvprop=content&rvslots=main&format=json&titles=A|B|C` (up to 50 pages per request, wait 45–90 s between requests) and `api.php?action=query&list=allpages&aplimit=500&format=json` for the page index |
| 游民星空 gamersky | full walkthrough in story order (`gamersky.com/tools/guide-map/roadbooks/<id>`), handbook articles listing all shrines / bosses / options per region | WebSearch "<中文游戏名> 全收集 游民星空"; pages are plain HTML, curl works |
| 3DM 全流程图文攻略 | chronological walkthrough, ~90 pages `3dmgame.com/gl/<id>_N.html` — same order as PowerPyx area pages, so it lines up | curl each page with a browser UA; save text |
| 18183 / TapTap / bilibili 专栏 / 小黑盒 | lists (pendants, weapons) and dialogue options | WebSearch; some lists are images only |
| 灰机wiki (huijiwiki), fandom zh | non-Chinese games with large fan wikis | |

Name matching technique: PowerPyx lists are chronological with location text, Chinese lists are usually grouped by
chapter. Match by chapter + location + meaning, and use the wiki item pages' "获取方式" text to confirm.
For a non-Chinese game, official Chinese names still exist when the game shipped a Chinese localization (PlayStation
Asia almost always does) — the same sources apply; if a game has no Chinese localization, tell the user and ask
whether to translate names with the English kept in parentheses.

## How to split the work

Run `make_terms.py` first; it writes `glossary/terms_en.json` with categories. Give each subagent a disjoint set of
categories (typical split for ~500 terms):

- A: regions, steps (shrine/area names), bosses, NPCs (`type:npc`), questlines, endings, dialogue
- B: weapons, armour/accessories, collectible item names (`type:*` and `collection:*` for items), quest/key items
- C: spells/skills, game-system terms (`misc` + mechanics you notice: currency, upgrade materials, status effects,
  weapon classes, menu names), collectible type names used in badges/stat grid

Before spawning, seed `glossary/seed_zh.json` with anything already certain (the official trophy list is the best
seed: boss names and collectible type names often appear inside trophy names/descriptions). See
`examples/wuchang/seed_zh.json`.

## Subagent brief template (fill the <> parts; one per agent, run in background, in parallel)

```
You are building an English→official-Simplified-Chinese glossary for the game <English title> (Chinese title
《<中文名>》). The glossary feeds a Chinese platinum-trophy helper page; the player plays in Chinese and must be able
to match names to what they see in-game, so we need OFFICIAL in-game Chinese names, not your own translations.

Work dir ($W): <abs path to build dir>
Inputs: $W/glossary/terms_en.json (terms by category, each with a ctx snippet showing where it appears),
$W/glossary/seed_zh.json (already certain), English page text under $W/raw/ (area pages are chronological).
YOUR CATEGORIES (only these): <list>.

Sources: <paste the source table rows that apply, incl. the wiki API tip and rate limits>.
Save raw downloads under a NEW dir $W/raw/zh_<X>/ and useful extracted plain text under $W/text/zh/ (prefix files
<X>_) — translators will grep them later. Use `python3 -I` for Python that reads downloaded files; keep scripts in
$W/scripts_<X>/.

OUTPUT: $W/glossary/zh_<X>.json shaped as
{"<category>": {"<English term exactly as in terms_en.json>": {"zh": "...", "conf": "official|likely|guess", "src": "<url>", "note": "..."}}}
official = this exact Chinese name seen tied to this exact thing; likely = strong indirect evidence; guess = your own
translation (fill it anyway, nothing blank). Budget ~60–90 tool calls.
Final reply: counts per conf, uncertain mappings, and the paths of saved Chinese source texts.
```

Afterwards run `merge_glossary.py <work>` → `glossary/glossary_merged.json` (`flat`, `conf`, `by_category`; adds
aliases without trailing "(…)"). Skim the agents' "uncertain" lists and resolve conflicts (e.g. two guides spell a
dialogue option differently) before translating. Keep the research agents' saved texts — translators use them.

## Things that went wrong before

- Same-name areas in two regions (ruined version of an earlier town): JSON keys collide; record both forms in `note`.
- English guide typos ("Forgotten Remains" for Lost Remains, "Qiao Ling"/"Qiao Ying" same NPC) — note them so
  translators use the right name.
- Two sources disagree (3DM vs gamersky dialogue wording): prefer the source quoting the option verbatim in 「」/【】.
- The glossary said `Fast travel = 羽渡` but the translation brief said 传送 — the brief won and the page was
  inconsistent. Put game-specific direction words into the translation brief only after checking the glossary.
