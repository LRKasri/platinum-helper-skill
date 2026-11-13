# game.json reference

One file per game at `<project>/<slug>/build/game.json`. Every script reads it. Two complete, tested examples:

- `examples/wuchang/game.json` — Wuchang: Fallen Feathers. Hub groups area pages under "Region N" headings, items look
  like `<b>Weapon: Halberd (Axes)</b><br>…`, step_mode `page`, by-type pages for every collectible, plus boss / NPC
  questline / endings guides. Rebuilds the delivered page exactly.
- `examples/phantom-blade-zero/game.json` — Phantom Blade Zero (the sample game). One page per region, items look like
  `<b>#4 – Hunter’s Insight (Accessory)</b>`, step_mode `checkpoint` on Bells, collections from tags, side tales as
  questlines (`mode: tag`), 1 400 screenshots → remote image mode. English pipeline tested end to end.

- `examples/stellar-blade/game.json` — Stellar Blade. Every item is its own `<h3>` ("Hydra / Box #4") →
  `item_heading_level: 3`; `checkpoint` on Camps with h2 "Second Visit" parts split off; past-tense trophy
  descriptions ("Defeated Abaddon."); one collection spanning three tags (Records = memory sticks + documents +
  passcodes). English pipeline tested end to end by a fresh agent.

Start from whichever example the new guide resembles more (compare `hub_outline.json`, `survey.py` output and
`survey.py --dump <slug>` of one area page).

## Fields

| field | required | meaning |
|---|---|---|
| `lang` | no | `zh` (default: Chinese page with EN toggle) or `en` (English-only page: no glossary research, no translation, no toggle — see `references/english-mode.md`) |
| `game` | yes | `zh` (official Chinese title, e.g. 明末：渊虚之羽), `en`, `short_zh`, `short_en` (shown big on the trophy tab), `slug` (folder name + localStorage key) |
| `sources` | yes | `trophy_guide`, `collectibles_guide` — the two URLs the user gave |
| `slug_strip` | yes | substrings removed from page slugs to make short step ids, e.g. `["wuchang-fallen-feathers-", "-collectible-locations"]` |
| `regions` | yes | `[{id, title_en, note_en?, pages: [{url, title_en}]}]` in story order. `note_en` is context for the translators' region summary / leave list only (not shown). In checkpoint/section mode the region page's own intro (PowerPyx's "Bells: 23 …" counts) is shown in 本区收集物说明. Copy page order from `hub_outline.json`. A page listed twice with `#anchor` (two shrines on one page) is merged automatically. **Item ids derive from page slug + position, so never reorder pages after translation starts.** |
| `step_mode` | yes | `page` (one route step per page), `checkpoint` (split pages at every item tagged `checkpoint_type`), `section` (one step per h2/h3) |
| `checkpoint_type` | if checkpoint | tag that starts a step (`bell`, `bonfire`, `shrine`, `camp`, `site of grace`…). Combined titles "Boss / Camp #4" use the part matching the checkpoint rule as the step name |
| `split_heading_level` | no | checkpoint mode: a heading of this level or higher (default 2; 0 = never) also starts a step — keeps "Second Visit" / "After getting X" parts separate |
| `paragraph_items` | no | `true` for prose walkthroughs (Sekiro: each h2 is a sub-area, items are bold words inside paragraphs). Every paragraph with bold names becomes an item keyed by those names (type rules run on them); paragraphs without bold become tips. After translation, split the paragraphs into one checkbox per entity with `prepare_entities.py` (see SKILL.md §4). Use with `step_mode: section` |
| `note_head_regex` | no | bold leads that are only labels, not things to tick (Sekiro `^(Checkpoints \(Idols\)|How to reach|Side Areas of interest)`) → shown as tips |
| `item_heading_level` | no | set to 3 (or 4) when every item is its own heading instead of `<p><strong>Title</strong>`; `survey.py` warns when headings far outnumber bold leads |
| `type_rules` | yes | ordered `[tag, regex]`; every regex that matches the item title adds that tag. Write them from the survey of item titles (see pipeline stage 2). Keep `save`, `ending`, `warn` rules if the guide has save-backup / ending / warning callouts |
| `type_priority` | yes | which tag becomes the item's displayed type when several match (first wins) |
| `types` | yes | `tag: [zh label, en label, zh badge (1 char), en badge, show-in-stat-grid]`. Badge chars follow the sample: 龛/武/佩/首/人/铃/饰… Use official Chinese category names from the glossary. `other`, `tip`, `warn` are filled in if missing |
| `note_tags` | no | tags whose items become non-checkable notes when they have no body (default `warn, save, ending`) |
| `non_platinum_types` | no | types no trophy needs (Wuchang: `spell`, `armor`, `skill`; Phantom Blade Zero: `bell`, `amber`, `blackstone`, `medicine`). Read the trophy guide's intro ("The things not required are: …") and the collectible hub ("X – not needed for trophies"). Items whose every tag is in this list (or in a partial collection, see `need`) become **optional**: dashed checkbox + 可选 chip, and they don't count in 白金模式 |
| `default_mode` | no | `plat` or `all`; default `plat` whenever the game has optional items or partial collections. The page shows a 白金模式 / 全收集模式 switch under the region title; 白金模式 makes the ring, step counters, stat grid and 本区全选 count only items the platinum needs |
| `miss_types` | no | types the guide itself declares missable as a whole (Wuchang: `npc` — "all NPC interactions are immediately missable", `riddle` — "All riddle doors are missable"). Quote the sentence in your notes; don't add types on judgment |
| `miss_rule` | no | `source` (default): 易错过 = the item's own text says missable / point of no return / will fail / no longer available / only one chance (not "unmissable"), or its type is in `miss_types`; also applied to by-type collection entries. `translator`: use the translators' per-item `missable` judgment instead (not recommended — user asked for 易错过 to mean what the guide says) |
| `collections` | no | per collectible trophy, see below |
| `pages` | no | optional extra guides: `bosses`, `questlines`, `endings` (URLs) |
| `questlines` | no | `{mode: "guide", aliases: {name: [regex…]}, name_zh: {name: 中文}}` when there is an NPC questline guide with one h2 per NPC; `{mode: "tag", tag: "tale"}` to build quests from route items (each tagged item starts a quest; items whose title starts with the quest name — "X Objective 2" — join it) |
| `endings` | no | `{heading_regex}` matching the h2 of each ending in the endings guide; default `^Ending (\d+): (.*?)(?: \((.*)\))?$`. Other h2s become the "all endings in one run" box (the first one) |
| `boss_extra` | no | default on: boss-guide entries with no route item become checkboxes inserted into the route in the boss guide's order (location + when it appears, strategy, reward, video). `false` to skip |
| `boss_extra_type` | no | type for those entries when no `type_rules` boss/elite rule matches their name (default `elite` if it is a boss type, else `boss`) |
| `trophy_links` | no | `{trophy name: regex}` — link a trophy to route items whose title matches (e.g. Phantom Blade Zero "Even Trees Know Sorrow" → `Ba(n)?yan Tree` challenge spots). Trophies whose description names quests in brackets ("Complete [Flesh Lily], [Apprentice Healer]") are linked automatically to items whose title starts with those names, and those quests count as 奖杯相关 |
| `images` | no | `{mode: auto|embed|folder|remote|none, embed_limit_mb: 8}` — auto = embed when small, else remote (user preference) |
| `region_aliases` | no | extra spellings of region names used in by-type pages, e.g. `{"Cloud Spire": "r2"}` |
| `region_heading_regex` | no | how region headings look on dash-list by-type pages (default `^(Region|Chapter|Act) \d+`) |
| `skip_paragraph_regex`, `reach_paragraph_regex` | no | override which paragraphs are dropped / used as "how to reach" |
| `zh_replacements` | no | `[[from, to]]` applied to the final Chinese JSON — use it to unify wording that different translators rendered differently (e.g. PS5 menu names) |

## collections

Each entry turns a "collect all X" trophy into a checklist on the trophy tab. Checking an entry checks the linked route
item and vice versa (they share the id). Entries that can't be linked get their own checkbox plus a 「定位」 jump to the
nearest related route item — that is expected for shop purchases and boss drops.

```json
{"type": "weapon", "trophy": "Legendary Collector", "source": "bytype", "url": "…all-weapon-locations/",
 "match": "name", "category_suffix": true}
```

| key | meaning |
|---|---|
| `type` | route tag the collectible uses (also used to add the trophy chip to items) |
| `trophy` | exact English trophy name from the trophy guide |
| `source` | `bytype` (a PowerPyx "All X Locations" page; parsed in numbered / dash-list / headed layouts automatically), `tag` (every checkable route item with that tag) or `items` (route checkboxes whose English title matches each regex in `names`, in order — for "defeat all bosses" trophies: Sekiro 《死斗的尽头》 = the game's 16 BOSS-class enemies per the Chinese wiki, not minibosses / Great Serpent / Carp / prologue Genichiro). A trophy "Defeat(ed) all bosses" with no collection gets an automatic `items` list of every boss-type checkbox |
| `match` | how by-type entries find their route item: `name` (entry name found in an item title; falls back to text search for a goto), `number` (`number_regex` with `{n}`, e.g. `Bamboozling\\s*#\\s*{n}\\b`), `order` (n-th unused tagged item in the entry's area), `paren` (text in the entry's parentheses, e.g. a benediction name) |
| `name_regex` | trims the entry name, e.g. `^(.*?Pendant)\\b` |
| `label_zh` | Chinese label template for numbered things: `笋精 #{n}` |
| `glossary_category` | look the full English label up in this glossary category for the Chinese label |
| `category_suffix` | append the weapon class from `(Longsword)` |
| `head_regex` | restrict linking to items whose title matches (e.g. `^Shrine`) |
| `dedupe` | `source: tag`: drop repeated names within a region; `source: bytype`: drop repeated labels (lists repeated per location) |
| `need` | how many entries the trophy really asks for. Default: the first number in the trophy description ("Collect 10 Memory Flowers" → 10, "Opened 200 boxes." → 200), or all entries when it says "all"/has no number. `need < total` → the trophy card shows 「奖杯需要 N 个（共 M 个，任选即可）」, turns green at N, marks the rest 可选, and the collection's items are optional in 白金模式. Set an integer to override, or `"manual"` when the number counts something else |
| `desc` | `true` → each entry also carries the by-type page's location text + screenshots (translated in a `collections` job, shown under 「位置说明」). Use it whenever the route doesn't itemize that collectible (prose walkthroughs), otherwise unlinked entries are just names |
| `need_note` | `{zh, en}` shown on the trophy card — required with `need: "manual"`, e.g. Phantom Blade Zero "10 complete Memory Flowers, each made of 2–6 petals; this list is per petal" |

**Always check every partial collection** (assemble.py prints them): read the trophy's guide note and decide
whether the number counts the listed entries (Stellar Blade "Opened 200 boxes" of 293 — yes) or groups of them
(Phantom Blade Zero flowers — no → `"need": "manual"` + `need_note`). A number larger than the list (Stellar Blade
"Acquired 30 Nano Suits", 27 on the route; the rest come from shops) is reported as a warning — mention it in the
`need_note` or add the missing entries.

**One trophy over several kinds** (Stellar Blade "Records Collector" = memory sticks + documents + passcodes):
add a rule-only tag that matches all of them — `["record", "Memory Stick|Document|Passcode"]` in `type_rules`,
`"record": ["记录", "Records", "录", "R", false]` in `types` (stat false so the grid isn't double counted),
and `{"type": "record", "trophy": "Records Collector", "source": "tag"}`.

Labels with several numbers ("Prayer Bead #28, #29", "Lapis Lazuli Location #2-4") keep all of them (`佛珠 #28、#29`).
When an unlinked entry's label ends in ": <place>" ("Prayer Bead #6: Estate Path"), 「定位」 jumps to the step whose
title contains that place.

**By-type parsing limits**: numbered (`#N:` leads, bold or as the first line before `<br>`), "Name N – X" or "X #N"
headings, dash-list ("Name – how to reach" under region headings) and
headed (`<h2>X #N</h2>`, optionally followed by an `<h3>` area) layouts parse automatically. A page with one h2 per
entry and no `#N` gives 0 entries, and a list repeated for every location gives duplicates — use `source: tag` or
`dedupe`. PowerPyx by-type names sometimes differ from the route page spelling ("Americano"/"Americana"); those
entries stay unlinked (own checkbox + 定位 jump) — fix with `name_regex` or accept.

**Stat grid and type filter** count every stat-type tag of an item (a "Boss / Camp #4" item counts as a boss and a
camp), not just its displayed type, so the grid matches PowerPyx's per-region counts.

Check the counts after assembling: `assemble.py` prints `collections {...}` and `qa_check.py` compares each with the
number in the trophy description ("Defeat 20 Bamboozlings"). Off-by-a-few is usually two collectibles in one title
("#49 & #50 – …") or a by-type page that counts DLC — fix with `head_regex`, `name_regex` or a different `match`.
