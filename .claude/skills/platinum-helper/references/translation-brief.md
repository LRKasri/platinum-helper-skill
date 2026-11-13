# Translation brief (template)

Copy this file to `<work>/tr_brief.md`, fill the `<>` parts and the game-specific notes, then spawn one translation
subagent per `tr_in/*.json` job in parallel (background). Prompt per agent:

> Translate one job of a Chinese game-guide localization. Read the brief first: `<work>/tr_brief.md`.
> Your job: `<work>/tr_in/<job>.json` (<what it covers, e.g. "Region 1 / 佛源镇, 11 steps, 117 units">).
> Write `<work>/tr_out/<job>.json` in the <route | meta> shape. <Region context for the leave checklist: what
> becomes unreachable when, points of no return, ending prerequisites in this region.> Validate before finishing.
> Final reply: unit count, invented terms (English → Chinese), anything ambiguous. Don't touch other jobs' files.

Wuchang: 6 jobs of 20–40k chars, ~10 min and ~200k tokens each.

---

# Translation brief — <English title> (《<中文名>》) platinum helper

You translate English PowerPyx guide text into Simplified Chinese for a Chinese trophy-helper page (players play the
game in Chinese). An "EN" toggle shows the original, so the Chinese must stand on its own: complete, accurate,
natural 简体中文 game-guide style (like 小黑盒 / 游民星空), concise but never dropping a step, direction, condition,
warning, reward or dialogue choice.

Work dir ($W): <abs path>

## Terminology (most important)
- Use `$W/glossary/glossary_merged.json` for every proper noun (`flat`: English → 中文, `conf`: official|likely|guess).
- Trophy names: glossary `by_category.trophies`; write a trophy mention as 《奖杯名》.
- Not in the glossary: grep `$W/text/zh/*.txt` (Chinese wiki / walkthrough extracts) for the official name; if still
  unknown, translate sensibly and keep the English in parentheses the first time in that unit: 骨哨（Bone Whistle）.
- In-game dialogue options and riddle answers: 「中文」; if not official (conf guess or absent) append the English:
  「我同意」(I agree).
- Direction words: left/right 左/右, turn around 180° 转身, shortcut 捷径, ladder 梯子, elevator 升降梯, chest 宝箱,
  yellow/purple/blue item 黄色/紫色/蓝色物品, red-eyed enemy 红眼敌人, exhaust dialogue 对话至无新内容,
  rest at <checkpoint> 在<检查点>休息, back up save 备份存档, New Game+ 二周目（NG+）.
  <Fast travel / checkpoint / currency: use the glossary's game-specific words, e.g. Wuchang 神龛, 羽渡, 赤汞.>
- <Game-specific notes from glossary research: typos in the English guide, same-name NPCs, disputed terms.>

## HTML rules
Keep exactly, around the translated words: `<b> <i> <u> <br> <ul><li> <span class="red"> <span class="green">`
`<div class="bfacts">` and empty trophy markers `<t class="bronze|silver|gold|platinum"></t>` (usually right before
the trophy name). Don't add other markup. Escape literal `& < >` as entities.

## Item titles (`head`)
The page shows a type badge, so drop the leading category prefix (`Weapon:`, `NPC:`, `Shrine:`, `Boss:`,
`Jade Pendant:`, `Spell:`, `Armor Set:`, `#12 –`) and `(Boss Guide)`; remove the outer `<b>`. Keep the rest translated:
`长柄斧（斧）` · `何有哉（获得：1×羽华丹 + 1×竹萤灯）` · `神龛：摩崖像` → `摩崖像`.
Save / warning heads: translate fully but short: `→ 存档备份 #1（PS5：设置 > …）`.

**Prose walkthroughs** (game.json `paragraph_items: true`; the input `head` is every bold name of the paragraph joined
by " · "): just translate `head` name by name, keeping the " · " separators. These paragraphs are split into one
checkbox per entity afterwards (`prepare_entities.py` + `references/entities-brief.md`), so the joined names are never
shown as a title.

## `missable` (checkable units only — informational; the page's 易错过 uses the guide's own wording unless game.json sets miss_rule: translator)
true when missing it at this point can lose it for the playthrough: NPC interactions and dialogue choices, items that
vanish when the region / boss / story advances, riddles, one-time fights, anything the text calls missable / point of
no return / "before X" / "don't …". false for things collectable later (most checkpoints, story bosses, shop items).

## Output JSON
Route jobs (`tr_in/route-NN.json`) → `$W/tr_out/route-NN.json`:
```
{
 "regions": {"<region id>": {"title": "区域中文名", "summary_zh": "1–2 句：本区重点与最大的坑", "summary_en": "…",
             "leave": [{"zh": "离开本区前必须完成的易错过事项", "en": "…"}],   // 3–6 bullets
             "colinfo_zh": "本区收集要点 1 段", "colinfo_en": "…"}},          // only for regions listed in the job's "regions"
 "areas": {"<step id>": {"title": "中文名（官方地名；两处用 ' & ' 连接）", "tagline": "≤20字要点，如：初遇何有哉 · 教学首领白克虏",
                         "tagline_en": "≤60 chars", "reach": "如何到达（不要 'How to reach X:' 前缀）", "sections": ["各 section 标题中文"],
                         "intro": "only when the input area has a non-empty intro: translate it (keep its <ul> list)"}},
 "units": {"<unit id>": {"head": "中文标题（无类型前缀，可空）", "body": "中文正文 HTML", "missable": true}}
}
```
Every unit id must appear (notes: head may be "", missable false).
Meta / endings / boss / collections / `missing_units` jobs → `{"units": {"<id>": "中文 HTML"}}` (`col-<type>-<n>-desc` = how to find that collectible). Trophy descriptions (`trophy-N-desc`): use the
official in-game Chinese description when the glossary/wiki has it.

## Process
1. Read the brief, glossary and your input. 2. Translate area by area (holding the output in a Python dict and
writing it with a script is fine; run Python with `python3 -I`). 3. Validate: JSON loads; every input id present;
counts of `<b> <t <li> <span` match the English (outer `<b>` of heads removed); no leftover English sentences.
4. Reply with counts, invented terms, ambiguities.
