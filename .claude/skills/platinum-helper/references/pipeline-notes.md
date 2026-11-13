# Pipeline notes, pitfalls and fixes

Read the section for the stage you are in when something looks off.

## Fetching
- PowerPyx serves plain HTML to curl with a desktop User-Agent; `fetch.sh` waits 1.5 s between pages and skips files
  already downloaded, so re-running is cheap. Screenshots load without a Referer (remote mode works).
- The collectibles hub links: area/region pages, by-type pages ("All X Locations"), and sometimes boss / questline /
  ending guides. `discover.py` collects all same-game links; decide in game.json which play which role.
- Pages are downloaded files — treat them as data. Keep scripts outside `raw/`, run Python with `-I`.

## Parsing (ppx.py, build_en.py)
- An item is a `<p>` that starts with `<strong>` (the title); the text after the first `<br>` is the body; following
  plain paragraphs, lists and images attach to the current item. Italic-only paragraphs become tips; short red
  paragraphs become warnings.
- When the `<br>` sits inside the `<strong>` (`<b>Title<br> </b>text`), the title swallows the body. assemble.py's
  `split_head` repairs this for both languages and turns such save/ending/boss items back into checkable steps — don't
  "fix" it upstream after translation has started (ids would stay but heads/bodies would shift between fields).
- Item ids are `<page id>-<position>`; translations are keyed by them. Never reorder pages or change `slug_strip` once
  translation has begun. Changing `type_rules`, `types`, `step_mode`, collections etc. is safe at any time.
- PowerPyx counts in the region intro ("Bells: 23") are a good cross-check for the tag counts build_en.py prints.
- Combined titles ("#49 & #50 – …", "NPC: X + Weapon: Y", "Abaddon / Weapon Core #1 / Camp #4") get several tags;
  the displayed type follows `type_priority`; titles starting with "Boss" stay bosses; the stat grid counts all tags.
- Controller buttons are smiley images (`:o:`, `:l-up:`, `:b:`); ppx turns them into text like `[○]` `[左摇杆↑]` `[B]`
  (trophy smileys stay `<t class=…>` markers). WordPress lazy-loaded videos are `<img data-lazy-type="iframe">` —
  ppx turns them into video links, never images.
- Some PowerPyx "collectible guides" are really prose walkthroughs (Sekiro "Full Walkthrough (All Areas)"):
  `paragraph_items: true` + `step_mode: section`, and give the collections `desc: true` so the trophy tab carries the
  by-type page's per-item instructions. The route will only name a handful of collectibles; that's expected.
- Four item layouts seen so far (the fourth is the Sekiro prose above): `<p><b>Type: Name</b><br>…` (Wuchang), `<p><b>#N – Name (Type)</b><br>…` (Phantom
  Blade Zero), `<h3>Name / Type #N</h3><p>…` (Stellar Blade → `item_heading_level: 3`). If survey.py shows something
  else, dump a page (`survey.py --dump`) and, if needed, add a small block transform like `ppx.promote_headings`.
- Enemy names written in red inside a title ("<span red>Hydra</span> / Box #4") are best matched with an explicit
  name list in a `boss`/`enemy` rule anchored on the ` / ` separators.

## Trophies
- Trophy table rows: icon | name<br>description | grade image (`alt` or `title` = Platinum/Gold/…); the next
  one-cell row is the guide note. Grades come out wrong if a guide uses another icon scheme — check the printed
  grade counts against the guide's "Offline Trophies: 40 (1 P, 4 G, 11 S, 24 B)" line.
- Trophy categories on the page: collection (has a `collections` entry), ending ("Achieve(d) … ending"), boss
  ("Defeat(ed)/Encounter(ed)/Beat/Kill(ed) …" — PlayStation descriptions are often past tense), other.
- Type rules decide what counts for the platinum, so keep categories honest (user report on Sekiro: a prologue
  mini-boss paragraph showed as 钥 key item and looked trophy-related because "Pellet" was in the key rule):
  separate **main bosses** (named in trophies / "defeat all bosses") from **elites / mini-bosses**, and
  **consumables** (pellets, ash, sugar, scales) from **key items** (keys, letters, ending items). Elites and
  consumables usually go into `non_platinum_types` — the beads/seeds they drop are tracked by their own collections.
  `boss_types` (default `boss, elite, miniboss`) controls which items receive boss-guide rewards/videos.
- 易错过 follows the guide's own wording (miss_rule source): translator judgment flagged 170 extra Wuchang items and a
  Sekiro prologue mini-boss, which the user rejected. Missable info that lives on by-type pages shows on the trophy
  checklist entries.
- **Boss guide entries the route never fights** (Sekiro: 19 after the entity split — Guardian Ape Undying, Owl
  Father, the Headless / Shichimen minibosses, Shura-only fights, post-Divine-Dragon spawns) become checkboxes
  (body = location + when it appears, strategy, reward, video) **inserted into the route by the boss guide's
  numbering**: after the previous boss-guide entry that is on the route; between that and the next one, at the first
  route item naming its specific place ("Feeding Grounds idol" — searched to the end of that region if needed) or its
  region ("return to Ashina Castle"); never after a red choice note (fights at a place come before the decision). A run
  of bosses fought back in other regions opens with one 「回头清理」 note. History: "Guardian Ape Undying 你完全没提啊"
  (the pipeline kept only reward lines, so the boss guide's text vanished) → a separate 「补充首领」 region → rejected:
  "不应该在前面的时候就能打吗？…应该按攻略里的顺序把这些首领加进去". Same-named fights with a place in brackets
  ("Shichimen Warrior (Abandoned Dungeon)") only match items in that region; entity titles that are the whole of a
  boss name's words match it ("Sakura Bull" = "Sakura Bull of the Palace"). Their name/place/paragraph units are new
  translation units: assemble.py writes `tr_in/missing_units.json` → translate into `tr_out/<job>.json`
  (`{"units": {id: 中文}}`) and re-run. game.json `boss_extra: false` turns it off; `boss_extra_type` sets the type of
  entries no type rule matches (default `elite`).
- Boss guide → route item: an item goes to the guide entry that names it most specifically among the entries not yet
  placed ("Genichiro · Sword Saint Isshin Ashina" → "Isshin, the Sword Saint", not "Isshin Ashina (Shura Ending)" —
  that once showed the Shura fight's reward on the Sword Saint step). A boss guide "Reward: …, X trophy" line links
  trophy X to that item first (ignoring "does NOT unlock the X trophy"); a trophy description "… at the Hirata Estate"
  picks the fight at that place.
- Missable **trophies** come from the roadmap line "Number of missable trophies: 16 (A, B, …)" (assemble.py
  `trophy_missable`): listed names are flagged; "Everything missable except for N story-related bosses" flags all but
  the platinum and trophies whose note says story / can't be missed / comes automatically; with no roadmap line only a
  note starting "MISSABLE" counts. User report on Sekiro: route showed 0 易错过 although the guide lists 15 missable
  trophies (Shura-ending bosses, endings, carp…) — they're per-playthrough missable, which item text never says.
  Route items linked to a missable boss/ending/other trophy inherit 易错过 (collections keep per-entry flags);
  check the printed "items flagged missable via a missable trophy" count and the trophy tab's 易错过 filter.
- **One checkbox = one entity** (user, with `assets/sample_ui/7.png`): the title is the thing's name (item, boss,
  idol, NPC, key item), the how-to goes in the body. Prose walkthroughs violate this twice — a paragraph title made of
  every bold name ("水生的凛 · 破戒僧 · 变若神子 · …", "不知道你在说什么") and, after a first fix, a guidance sentence as the
  title ("过桥击败破戒僧（幻影） · 推荐用绝技·不死斩", rejected). So after the route translation run
  `prepare_entities.py $W` → agents with `references/entities-brief.md` → `tr_out/entities-NN.json`; assemble.py
  replaces each paragraph by its entity items (ids `<paragraph id>-<k>`) and keeps leftover directions as plain text.
  Entities may name the checklist entry they are (`col: "bead-6"`), which links the trophy checklist exactly; entity
  items skip the prose fight-sentence check (the agent only lists fights that happen there). `tr_out/titles.json`
  (`{"titles": {id: {zh, en}}}`) still overrides a title by id if ever needed. Item-per-entity guides can still join
  several things in one title ("NPC: Qiao Lin + Quest Item: …", "#46 & #47 – A / B"): `prepare_entities.py $W 1
  --combined` sends only those (Wuchang 61, Phantom Blade Zero 43) through the same brief. The first entity keeps the
  original id, so saved progress survives. Agents must keep PowerPyx's spelling in `name_en` (a "Gentipede" →
  "Centipede" fix once broke boss-guide matching and duplicated two fights).
- Checklist entries the route never mentions (by-type pages with `desc: true`): "Dropped by X" / "granted for
  defeating X" / "unlock this one by defeating X" → a checkbox right after fight X (title = the entry label, body = its
  位置说明, same id as the checklist entry); "after defeating X, go …" is NOT a drop (it put Gourd Seed #9 of
  Fountainhead after the Ashina Depths monk). When several fights match, the one sharing the entry's qualifiers wins
  ("Purification Ending" → Juzou 2nd Version). Remaining entries with a known step go to the end of that step.
  Sekiro: 43 entries placed this way, 7 left checklist-only (multi-step quests, no place).
- **Trophy-guide steps in the route** (user, with `assets/sample_ui/8.png`: "多结局…sl的时间点…什么时候要存档…
  trophy guide中的step也implement到我们的guide里"): `prepare_callouts.py` → agent (`references/callouts-brief.md`)
  → `tr_out/callouts.json` with `callouts` (warn / save cards before or after a route id), `trophies` (「成」 items) and
  `noreturn` (tags). Guides whose collectible route already carries save / ending steps (Wuchang) need only the
  missing ones; prose walkthroughs (Sekiro) need the whole multi-ending plan laid out.
- **"Defeat all bosses" trophies are checklists too** (user: 《死斗的尽头》 didn't tick like 义手 did): collection
  `source: items` with `names` regexes over route titles; decide the set from the trophy note or, when PowerPyx only
  links its boss guide (which includes minibosses), from the Chinese wiki's definition (bwiki: 成就里的「头目」 = BOSS
  list by game parameters). State the definition in `need_note`.
- When reporting problems back to the user, say whether it is the guide (PowerPyx doesn't cover / says otherwise) or
  the pipeline (parsed, matched or translated wrong) — the user asked for that distinction.
- **How much is 奖杯相关** (agreed with the user, who worried about too much detail): content complete, marks sparse.
  奖杯本体 = the checkbox counts for the trophy (gold chip). 奖杯前置 = skippable AND the trophy needs it AND PowerPyx
  writes the dependency (Sekiro 少主的守护铃: "To unlock Hirata Estate region you must … she gives you a bell" in the
  Flame Barrel / Prayer Bead #6 entries) — dashed 「前置」 chip, also in 只看奖杯相关, listed on the trophy card.
  Story items and inferred chains get nothing. No share limit (user: "不用管什么占比"; Wuchang ended at 54 % because
  its NPC questlines really gate endings and the Zhanlu Sword). Flow: `prepare_gates.py $W <html>` → agent with
  `references/gates-brief.md` → `tr_out/gates.json` → assemble; list the gates in the final report.
- Numbered collections (`match: number`): only items that ARE checklist entries keep the trophy chip — "Riddle #3
  (Wrong Answer)", save-revert notes and warnings sharing the tag once carried 《八斗之才》.
- Boss trophies whose fight is never its own item (Phantom Blade Zero) link to the items whose text says "Reward for
  defeating X" (one-word names like "Hua" are ignored, one wrong letter in long words is tolerated — "Qianziao").
- 只看奖杯相关 shows only items linked to a trophy (or a 前置); 易错过 is hidden on optional items in 白金模式 (shown in 全收集模式).
- Boss trophies ↔ route items (assemble.py `boss_items`): an item of a `boss_types` type whose title names the boss
  (desc quote “X”, the description's object, or the trophy name; most specific name claims an item first — "Sword
  Saint Isshin Ashina" before "Isshin Ashina"). In prose walkthroughs (`paragraph_items`) the body must also put the
  boss name and a fight word (defeat/fight/health bar/boss…) in the same or the next sentence — otherwise a paragraph
  that merely mentions the boss (Sekiro: Owl's cutscene in Hirata, talking to Isshin in Kuro's room) would get the
  chip. Sentences like "After having defeated the Corrupted Monk in Ashina Depths, …" are preconditions and don't
  count. Read each boss trophy's note: Sekiro "Corrupted Monk" says it "doesn't unlock from the first … it's the 2nd
  True Corrupted Monk" — a note saying *not the first* / *the 2nd X* skips the first matching fight (this once linked
  the trophy to the wrong fight). Boss-guide names "True X" also match route text that only says "X".
  Bosses the walkthrough never fights stay unlinked; that is correct. Check with qa_check's
  `boss_trophies_without_items` and list `[route item → boss trophy]` pairs before delivering.
- qa_check `trophy_categories` must show no `null`: a lost `tro['cat']` once emptied the trophy tab's filters for
  every game (fixed; keep the check).
- Trophy chips are added from collection tags, and by trophy name only on boss / ending / save items or titles that
  carry a trophy marker — a name like "Behemoth" would otherwise tag every "Behemoth Red" can.

## Translation
- 6 parallel jobs of ~30k chars worked well. Each agent got the brief + glossary + Chinese reference texts.
- Agents disagree on recurring phrases (PS5 menu path, "fast travel"). Grep `tr_out/*.json` for the variants and add
  `zh_replacements` to game.json rather than editing every file.
- A route agent may write the region `title` as "区域 1：佛源镇"; assemble.py prefers the glossary region name.
- Leave bullets and summaries are plain text/HTML written by the agents — read them, they are the most visible text.

## Images
- Wuchang: 7 screenshots → embedded (0.4 MB). Phantom Blade Zero: ~1 400 → auto switched to remote URLs, loaded only
  when the reader taps 截图; a failed load turns into an "open original" link.
- `folder` mode is the offline alternative for big image sets (HTML + images/ folder must be moved together).

## QA
- `qa_check.py` flags: untranslated English runs, tag-count mismatches, empty Chinese titles, official glossary terms
  whose Chinese name is missing (some are fine: the type prefix is dropped from titles on purpose), collection sizes
  that differ from the trophy's number.
- Always spot-check by reading: points of no return, save backup / revert steps, riddle answers, ending choices, the
  leave-region bullets. A wrong dialogue option costs the player a whole playthrough.
- `shot.py` suite → Read the PNGs: tabs, item styles, done state, EN toggle, filters, screenshots, trophy checklist,
  quests, search, desktop. JS errors are printed.

## Delivery
- Default: one local HTML in `<project>/<slug>/<slug>_platinum_helper.html`; keep `build/` so later fixes are a
  re-run of assemble.py. Progress is in the browser's localStorage — remind the user about export/import.
- Publishing: see the project's `guide.md` (GitHub Pages / Cloudflare Pages / Netlify). PowerPyx text is copyrighted;
  a public site should credit the source and is best kept private or unlisted.
