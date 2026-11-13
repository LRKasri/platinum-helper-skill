---
name: platinum-helper
description: Build a "白金小助手" platinum trophy helper — a single-file, phone-friendly HTML checklist modeled on the 小黑盒 mini-program, in Chinese with an EN toggle or English-only (no translation, far fewer tokens) — from a PowerPyx trophy-guide URL plus its collectibles-guide URL. Covers fetching and parsing every PowerPyx sub-page, researching the game's official Chinese names, parallel translation with an EN toggle, linking collectibles to trophies, embedded screenshots, and screenshot QA. Use this whenever the user hands over powerpyx.com trophy / collectible / walkthrough links, asks to 复刻/做一个 白金小助手、奖杯攻略、全收集清单、白金路线 page for any game, asks for an English platinum / trophy checklist page from PowerPyx, says "same as wuchang/phantom blade for game X", or wants to fix, update or re-translate a helper page built in this project (wuchang/…, */build/game.json).
---

# 白金小助手 builder

**Goal: a player who has never played the game can follow the page from start to platinum.** Everything below
serves that, and the pipeline should get there in one pass — the user should not have to fine-tune results.

Turn two PowerPyx URLs (trophy guide + collectibles guide) into `<project>/<slug>/<slug>_platinum_helper.html`:
a dark, phone-first page with region tabs → numbered route steps → checkable items, a trophy tab with
collection checklists, a quests/endings tab, search, progress saved in the browser, Chinese by default with an
"EN" button showing the original English. Reference result: `wuchang/wuchang_platinum_helper.html` in this project
(built by this pipeline); target look: `assets/sample_ui/*.png`.

`$SKILL` below = this skill's directory. All scripts take the work dir `W = <project>/<slug>/build` as first argument
and are plain Python 3 (stdlib; Pillow optional) — run them with `python3 -I`.

## 0. Confirm before starting

The user's standing preferences (project memory) are: Chinese UI using the game's **official in-game Chinese names**,
EN toggle, **local HTML only** (don't publish), screenshots embedded behind a button with videos as links, and
remote image links instead when embedding would make the file too big. Use them as defaults; only ask what is
genuinely open, typically:
- **language**: Chinese with an EN toggle (this user's default) or **English-only** for English-speaking readers —
  `"lang": "en"` in game.json skips the name research and all translation (about a third of the tokens); follow
  `references/english-mode.md` instead of §3–4;
- the game's Chinese title / whether it has an official Chinese localization (if not, ask how to render names);
- anything unusual in the guide (DLC sections, several playthroughs) that changes scope.

Tell the user the expected scale up front: a full game is ~1–2 hours wall-clock and several million subagent tokens
(Wuchang: 3 research + 6 translation subagents, then ~3 for entities / prerequisites). After that, run every stage
below to the end without stopping for approvals; decide judgment calls with the rules in "Quality bar" and list
them in the final report.

## Quality bar (what the user expects without being asked)

These came from the user's reviews of Wuchang, Phantom Blade Zero and Sekiro; apply them by default.
- **One checkbox = one entity**: title = the thing's official Chinese name only (佛珠 #6, 破戒僧（幻影）,
  「水生村」鬼佛, 烟儿的记忆之花 ×6); how to get / beat it goes in the body (`assets/sample_ui/7.png`). Never a
  sentence or a list of names as a title. Choices and points of no return are red notes without a checkbox.
- **Nothing from the guide is lost, and everything sits in the guide's order**: directions between entities stay as
  plain text; bosses the walkthrough skips but the boss guide covers are inserted into the route by the boss guide's
  numbering (never a separate region — the user rejected 「补充首领」); checklist entries the walkthrough never
  mentions appear as checkboxes after the fight that drops them or at the end of their step.
- **易错过 = the guide says so**: item text, a type the guide declares missable, and the roadmap's "missable
  trophies" line for trophies. Never translator judgment.
- **奖杯相关** has two levels: 奖杯本体 (the checkbox counts: collectible, the boss / ending that pops it, the final
  hand-in) → gold chip; 奖杯前置 → dashed chip, only when ① the trophy needs it, ② a player could skip it, ③ PowerPyx
  writes the dependency. No share limit — apply the three conditions and nothing else. "Pick any N" collections
  (30 of 63) get no prerequisites.
- **The trophy guide's steps are in the route** (`assets/sample_ui/8.png`): save backups and reloads, ending
  branches, points of no return (tagged 【不可回头点】 with a red 「点亮之前」-style card before them), "finish X
  before Y", and story trophies as 「成」 checkboxes where they pop. Multi-ending plans (2 playthroughs + backups) are
  laid out along the route so following it top to bottom yields every ending.
- **Official names**: glossary first; keep PowerPyx's own spelling in English fields (matching relies on it).
- **Report problems honestly**: say whether a gap is 攻略的问题 (PowerPyx doesn't cover / says otherwise) or 我的问题
  (pipeline parsed, matched or translated wrong), and fix the latter.

## 1. Discover and fetch

```bash
python3 -I $SKILL/scripts/discover.py $W <trophy_url> <collectibles_url>   # prints the hub outline
bash $SKILL/scripts/fetch.sh $W/urls_all.txt $W/raw                         # every linked sub-page
```
Read the outline: which links are route pages (by region/area, in story order), which are by-type pages
("All 24 Weapons"), and which are boss / NPC-questline / endings guides.

## 2. Configure and parse (English)

1. See how items are written: `python3 -I $SKILL/scripts/survey.py $W` (title shapes; warns when every item is a
   heading) and `python3 -I $SKILL/scripts/survey.py $W --dump <area-page-slug>` (parsed blocks of one page).
   Four layouts are known — `<b>Type: Name</b>` (Wuchang), `<b>#N – Name (Type)</b>` (Phantom Blade Zero),
   `<h3>Name / Type #N</h3>` (Stellar Blade, needs `item_heading_level: 3`), and prose walkthroughs with bold names
   inside paragraphs (Sekiro, needs `paragraph_items: true` + collections with `desc: true`).
   If the user gives only a trophy guide, or the game has no "collectible guide", use the guide PowerPyx links as
   the area-by-area walkthrough (e.g. "Full Walkthrough (All Areas)") as the second URL.
2. Write `$W/game.json` — start from the closest of the `examples/` and read `references/game-json.md`.
   Key decisions: `regions` (from the outline, story order), `step_mode` (`page` for one-page-per-checkpoint guides,
   `checkpoint` when one page covers a whole region), `type_rules`/`types` (every collectible kind, NPC, boss,
   save/ending/warning callouts), `collections` (one per "collect X" trophy), optional `pages`/`questlines`.
   **Platinum ≠ 100 %**: many platinums don't need every collectible. Put types no trophy needs into
   `non_platinum_types` (the trophy guide intro usually lists them), and check every collection whose trophy asks
   for fewer than the list holds — assemble.py prints these "partial collections"; confirm the number really counts
   those entries, otherwise set `"need": "manual"` + `need_note`. The page then defaults to 白金模式 and counts
   only what the platinum needs (全收集模式 one tap away).
3. Parse and check counts against PowerPyx's own numbers (region intros, hub page, trophy descriptions):
```bash
python3 -I $SKILL/scripts/build_en.py $W        # route -> data_en/areas.json (prints tags per region)
python3 -I $SKILL/scripts/build_en2.py $W       # trophies, by-type lists, bosses, questlines, endings
python3 -I $SKILL/scripts/fetch_images.py $W    # decides embed / remote, downloads if embedding
python3 -I $SKILL/scripts/assemble.py $W $W/preview_en.html   # English-only preview (zh falls back to en)
```
4. Look at the preview with the screenshot suite (section 6) before spending tokens on research and translation:
   steps sensible? item types/badges right? collections the right size, few unlinked entries
   (`assemble_report.json`)? Fix game.json and re-run — this loop is cheap.
   **After translation starts, never reorder pages or change `slug_strip`** (item ids are page + position).

## 3. Official Chinese names (glossary) — Chinese pages only

Read `references/glossary-research.md`. In short:
- seed `$W/glossary/seed_zh.json` with certain names (official trophy list first — it also yields boss and
  collectible-type names; see `examples/wuchang/seed_zh.json` for the shape: `{"trophies": {en: zh}, "known_terms": {...}}`);
- `python3 -I $SKILL/scripts/make_terms.py $W` → `glossary/terms_en.json`;
- spawn ~3 research subagents in parallel (background) with disjoint categories using the brief template there;
- `python3 -I $SKILL/scripts/merge_glossary.py $W` → `glossary/glossary_merged.json`; resolve the conflicts the
  agents report.

## 4. Translate — Chinese pages only (English-only: region notes job in `references/english-mode.md`)

```bash
python3 -I $SKILL/scripts/prepare_tr.py $W     # tr_in/route-NN.json, meta, endings, boss (+ size table)
```
Copy `references/translation-brief.md` to `$W/tr_brief.md`, fill in the game-specific parts (glossary notes,
checkpoint/currency words, typos found during research), then spawn one translation subagent per job, all in one
message, in the background. Each writes `$W/tr_out/<job>.json`. While they run, nothing else is needed; when each
reports, skim its "invented terms" and "ambiguous" lists — they are the review queue for section 6.

**Prose walkthroughs** (`paragraph_items: true`): when the route jobs are back, run
`python3 -I $SKILL/scripts/prepare_entities.py $W 2` and spawn one agent per `tr_in/entities-NN.json` with
`references/entities-brief.md`. Each paragraph becomes one checkbox per entity — title = the thing's name (佛珠 #6,
破戒僧（幻影）, 「水生村」鬼佛), how-to in the body (target `assets/sample_ui/7.png`) — and the agents tie entities to
trophy-checklist entries. For guides that already have one item per spot, still run
`prepare_entities.py $W 1 --combined`: it sends only the items whose title joins several things
("NPC: X + Weapon: Y", "#46 & #47 – A / B") through the same brief.

## 5. Assemble

```bash
python3 -I $SKILL/scripts/assemble.py $W <project>/<slug>/<slug>_platinum_helper.html
```
It merges English data, translations, glossary and images into `assets/template.html` and prints item counts,
collection sizes, missing translations and unlinked entries. Units it needs but nobody translated (e.g. boss-guide
bosses the route never covers, which it inserts into the route) are written to `tr_in/missing_units.json` —
translate that job too (one subagent, same brief) and re-run. Unify wording that differs between translators with
`zh_replacements` in game.json; fix a single text by editing the relevant `tr_out/*.json`; re-run (seconds).

**奖杯前置** (after the first full assemble): `python3 -I $SKILL/scripts/prepare_gates.py $W <html>`, one agent with
`references/gates-brief.md` → `$W/tr_out/gates.json` (applied directly) + `$W/gates_review.md` (for the report).
Re-run assemble. Skim the review file: every gate must quote PowerPyx and meet the three conditions.

**Trophy-guide steps** (after 前置): `python3 -I $SKILL/scripts/prepare_callouts.py $W <html>`, one agent with
`references/callouts-brief.md` → `$W/tr_out/callouts.json` (cards before/after route items, 「成」 trophy items,
no-return tags). Re-run assemble; read the cards in route order once — they decide whether a newcomer gets every
ending.

Also check what assemble.py prints: `bosses from the boss guide added to the route`, `checklist entries added to the route`,
boss trophies without items (qa_check). A boss trophy without an item usually means the fight hides in a drop's text
("Reward for defeating X") or the boss guide — assemble links both; investigate before calling it a guide gap.

## 6. QA (always)

```bash
python3 -I $SKILL/scripts/qa_check.py $W <html>                         # -> $W/qa_report.json
PLAYWRIGHT_BROWSERS_PATH=<scratch>/pw <scratch>/pwenv/bin/python $SKILL/scripts/shot.py <html> <scratch>/shots
```
(Playwright setup is in the `shot.py` docstring; install it in the session scratchpad, not the project.)
Then actually Read the screenshots and spot-check the text that can cost the player a playthrough: points of no
return, save backup / revert steps, riddle answers, ending choices, leave-region bullets. Also compare the trophy
tab's 易错过 filter with the roadmap's "missable trophies" line, and read each boss trophy's note against the route
item it links to (which fight counts). Details and known pitfalls: `references/pipeline-notes.md`.

## 7. Deliver

Final file in `<project>/<slug>/`, sources kept in `<project>/<slug>/build/`. Report to the user in Chinese:
path, what's in each tab, counts, how names were sourced (official / likely / guessed share), anything left in
English or uncertain (with examples), the 奖杯前置 list in one line each, guide problems found (攻略的问题),
deliberate omissions, and that progress lives in the browser (export via ⋯).
For publishing questions point to `guide.md` in the project root.

## Updating an existing helper

Work dir is `<project>/<slug>/build` (has `game.json`). Text fixes → edit `tr_out/*.json` (or add
`zh_replacements`), structure/type/collection fixes → edit `game.json`, template/UI fixes → `assets/template.html`
(check `references/ui-spec.md`); then re-run `build_en*.py` only if game.json parsing fields changed, and always
`assemble.py` + QA. Re-translate only the affected units: write a small job file with just those ids.

## Files

- `scripts/` discover, fetch.sh, survey, build_en, build_en2, fetch_images, make_terms, merge_glossary, prepare_tr,
  prepare_entities (one checkbox per entity), prepare_gates (奖杯前置), prepare_callouts (trophy-guide steps), assemble,
  qa_check, shot, ppx (PowerPyx HTML → blocks parser library)
- `assets/template.html` the page (data contract in `references/ui-spec.md`); `assets/sample_ui/` target look
- `examples/` game.json files: `wuchang/` (bold "Type: Name" items, page steps, by-type collections, + seed glossary),
  `phantom-blade-zero/` ("#N – Name (Type)", checkpoint steps on Bells, tag collections, partial/manual needs,
  trophy_links), `sekiro/` (prose walkthrough, paragraph_items, collections with desc), `stellar-blade/` (h3 items;
  English stage only). The first three were delivered as full Chinese pages.
- `references/` game-json.md, glossary-research.md, translation-brief.md, entities-brief.md, gates-brief.md,
  callouts-brief.md, english-mode.md, ui-spec.md, pipeline-notes.md
