# Entities brief — split prose walkthrough paragraphs into one checkbox per thing

Used for prose walkthroughs (game.json `paragraph_items: true`, e.g. Sekiro) after the route translation exists.
Read `$W/tr_brief.md` too: terminology, glossary (`$W/glossary/glossary_merged.json`), HTML rules.

## Why
The page shows a checklist. Each checkbox must be ONE entity — a thing the player gets, fights, reaches, talks to or
decides — titled only with its name, with the how-to in the text under it (target look:
`assets/sample_ui/7.png`: 「烟儿的记忆之花 ×6」 + where they are; 「琴女·烟千岁」 + how to beat her; 「残存的执念·执」 +
「击败琴女·烟千岁自动获得…」; 「幻术琵琶的琴弦」 + 「击败获得」). The user rejected titles that were guidance sentences
(「过桥击败破戒僧（幻影） · 推荐用绝技·不死斩」) and titles that list every name in a paragraph
(「水生的凛 · 破戒僧 · 变若神子 · 金刚山 仙峰寺 · …」).

## Input `$W/tr_in/entities-NN.json`
- `types`: allowed type keys (zh label; `counts_for_platinum`), plus `route` and `warn`.
- `collection_entries`: every entry of the trophy checklists (`ref` like `bead-6`, PowerPyx label, area, where).
- `paragraphs`: `{id, region, step, tags, bold_names_en/zh, body_en, body_zh (existing translation), n_images}`.

## What to produce for each paragraph
An ordered list of parts, in the order things happen in the paragraph:
- **entity** `{"type", "name_zh", "name_en", "body_zh", "body_en", "col"}`
  - one per thing the player does in THIS paragraph: item / collectible picked up, boss or elite fought, checkpoint
    (idol / bonfire …) reached, NPC talked to (with what to say or give), skill / memory / ninjutsu / key item received,
    a decision or point of no return (`warn`: shown as a red note without checkbox).
  - not entities: places passed through, ordinary enemies, things mentioned as earlier or later references
    ("after O'rin …", "you could have come here earlier", "see the Folding Screen Monkeys boss").
  - `name_zh`: only the official name (glossary), no verbs: 「佛珠」, 「破戒僧（幻影）」, 「宫内破戒僧」, 「「水生村」鬼佛」,
    「永真」, 「忍者之药理知识·甲」. Several identical things picked up together → one entity 「灰烬团 ×3」 (only when the
    text gives the number). When the entity is a checklist entry, add its number as the trophy list shows it:
    「佛珠 #6」. Keep a disambiguation in （） when the same name appears twice in the game.
  - `name_en`: the guide's English name (as in bold_names_en), e.g. "Prayer Bead", "Corrupted Monk".
  - `body_zh` / `body_en`: how to get / do THIS entity, built from the paragraph's own sentences (body_zh for Chinese,
    body_en for English), trimmed to what concerns it. Keep every direction, condition, warning, reward and dialogue
    choice that belongs to it; a sentence that serves two entities may appear in both. Don't invent facts and don't
    re-translate — reuse the existing Chinese wording (fix only obvious errors). Keep `<b>` around names, `[○]` buttons.
    May be short: 「击败后获得」. Start with where it is when the paragraph says so.
  - `col`: the `ref` of the collection entry this entity is (same item kind, same place / boss / order); `null` when
    unsure or not a checklist item. Each ref at most once overall.
- **route** `{"type": "route", "body_zh", "body_en"}`: sentences about moving on / context that belong to no entity.
  Put it where it occurs (before, between or after entities). Omit when nothing is left.

**Nothing may be lost**: every sentence of the paragraph must end up in at least one part. A paragraph with no entity
becomes a single `route` part.

## Combined-title items (`"mode": "combined"`, Wuchang / Phantom Blade Zero)
The guide already has one item per spot, but some titles join several things: "NPC: Qiao Lin + Quest Item: Peachwood
Amulet", "#46 & #47 – Weeping Creek Valley Long Pillar (Challenge) / Counter Bracers (Accessory)". `bold_names_en/zh`
is that title. Split it into its entities the same way (title = name only, body = the sentences about it, `route` for
the rest). Keep PowerPyx's number in `name_en` when the title has one ("#46 – Weeping Creek Valley Long Pillar") and
keep the item kind as `type` (the kinds in the title map to the type keys: Weapon → weapon, Accessory → accessory,
Challenge → challenge …; a quest name in 【】 is the quest's type). Things obtained together that the guide treats as
one (an armor set's four pieces, "1x Cornucopia Elixir + 1x Bamboo Lantern" given by one NPC) may stay one entity,
e.g. 「明军套装」 or the NPC + 「获得：1×羽华丹、1×竹萤灯」 in the body. When the title really is one thing (a name that
contains "&" or "/"), return one entity with the whole body.

**English-only builds** (`"lang": "en"` in game.json, no Chinese text in the input): fill only `name_en` / `body_en`
(the guide's sentences as they are); leave out the `_zh` fields.

## Output `$W/tr_out/entities-NN.json`
```json
{"entities": {"<paragraph id>": [
  {"type": "route", "body_zh": "…", "body_en": "…"},
  {"type": "boss", "name_zh": "破戒僧（幻影）", "name_en": "Corrupted Monk", "body_zh": "…", "body_en": "…", "col": null},
  {"type": "bead", "name_zh": "佛珠 #6", "name_en": "Prayer Bead", "body_zh": "击败后获得。", "body_en": "Dropped on defeat.", "col": "bead-6"}
]}}
```
Every paragraph id must be present. Valid UTF-8 JSON. Verify with `python3 -I` (ids, types from the list, refs exist
and are unique) before replying. Reply briefly: counts (paragraphs, entities per type, refs used), and paragraphs where
the split was a judgment call.
