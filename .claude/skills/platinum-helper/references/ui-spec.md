# UI spec and data contract

The page imitates a 小黑盒 mini-program ("影之刃零 白金小助手"); reference screenshots are in `assets/sample_ui/1–5.png`, and `7.png` shows the item rule: one checkbox = one entity, title = its name only (烟儿的记忆之花 ×6, 琴女·烟千岁, 幻术琵琶的琴弦), how-to in the body
(look at them before changing the template). `assets/template.html` already implements all of this; normally you only
feed it data. Change the template only for a real need, and keep `examples/*` games working.

## What the user expects to see (from the sample)

- Dark theme; calligraphy font (Ma Shan Zheng from Google Fonts, falls back to KaiTi offline) for region names.
- Top, sticky: search box (`搜索物品 / 首领 / 奖杯 / NPC`), language button (EN / 中), ⋯ menu (export / import / reset
  progress); horizontally scrolling region tabs `第一区域 / 名字` with red underline on the active one.
- Route tab, per region: label + big name + `x / y 项已完成` + progress ring; description with red left border;
  stat grid of collectible counts (5 per row, last row stretches; tap a cell = filter by that type; green when done);
  red "离开本区前确认" box (N 项, collapsible); collapsible "本区收集物说明"; four filter buttons
  隐藏已完成 / 只看易错过 / 只看奖杯相关 (items linked to a trophy only) / 本区全选 (toggles to 取消全选).
- 白金模式 / 全收集模式 switch under the region count (only when the game has optional items): platinum mode counts
  only items the platinum needs in the ring, region tab bars, step counters (「—」 when a step has only optional
  items), stat grid and 本区全选; optional items keep showing with a dashed checkbox and a 可选 chip.
- Numbered steps with a vertical line; each card: title (+ small tagline), `done/total`, chevron, progress bar
  (red → green when complete, number box turns into a green check).
- Items: checkbox (red fill + check when done; done items fade and strike through), one-character type badge,
  bold title, description; chips: 🏆 trophy (gold), 易错过 (purple), 截图 N (blue, toggles screenshots), ▶ 视频 (link).
  Notes have an (i) icon and no checkbox; warnings use a red left-bordered box; save-backup steps a gold one.
- Trophy tab: earned count, grade counts, ring; collapsible roadmap overview; filter chips 全部/未获得/易错过 (only when some trophy has `miss`)/收集类/首领/结局/其他; 易错过 tag on missable trophy cards;
  trophy cards (grade gem, Chinese name + English small, description, progress) expanding to guide notes, videos,
  checklist (collection entries or linked route items, each with 定位 › jump) and a 标记已获得 toggle.
- Quests tab: ending cards + red "all endings in one playthrough" box; NPC questline cards (奖杯相关 / 非奖杯 tag,
  progress) listing the linked route items with their location.
- Bottom nav 路线 / 成就 / 支线. Phone-first (412 px), centred 760 px column on desktop.
- Progress lives in localStorage under `<slug>-platinum-helper-v1`; export/import JSON in the ⋯ menu.

## Data contract (`<script id="appdata">` JSON, written by assemble.py)

All user-visible text is `{zh, en}`; the page shows `zh` (falls back to `en`) or `en` after the toggle.

```
storageKey, game{zh,en,short{zh,en}}, about{zh,en}
types{tag: {zh, en, badge{zh,en}, stat}}, statOrder[tag]
regions[{id, no{}, short{}, summary{}, leave[{zh,en}], colInfo{} (html),
         areas[{id, url, title{}, tagline{}, reach{}, sections[{title{}, items[ITEM]}]}]}]
ITEM = {id, type, check (bool), style ('', 'warn', 'save'), head{} (html), body{} (html), miss, tro[trophy id],
        stags[stat types it counts as], opt? (not needed for the platinum), imgs[image key], videos[url],
        pre?[trophy id] + preNote?{} (奖杯前置: dashed 「前置 · 《奖杯》」 chip, counts as 奖杯相关),
        noreturn? (red 【不可回头点】 chip)}
Trophy-guide cards are ITEMs with check false and style warn (red) / save (gold), head = short title (点亮之前,
存档备份 #1), body = what to do; story trophies are checkable ITEMs of type `trophy` (badge 成) with the trophy chip,
id `tro-<trophy id>`, also listed in that trophy's items.
trophies[{id 't<n>', grade, cat (col|boss|ending|other), miss?, name{}, desc{}, detail{} (html), videos[],
          col[{id, label{}, area{}, goto?}], need?, needNote?{}  or  items[item id], pre?[item id] (listed under 奖杯前置)}]
mode{enabled, default ('plat'|'all')}
questlines[{id, name{}, req, reward{}, intro{} (html), items[item id], anchor}]
endings[{id, title{}, sub{}, html{}, videos[], trophy}], endingsAll{title{}, html{}} | null
roadmap{title{}, html{}}, side{title{}, intro{}, url}
```
`<script id="imgdata">` maps image key → data URI (embed), relative path (folder) or URL (remote).
A collection entry shares its `id` with a route item when linked, so one checkbox state drives both views.

## Known template gotchas

- Use inline SVG icons, not emoji — headless Chromium (and some Android fonts) render emoji as boxes.
- Region-tab auto-scroll must only set `scrollLeft` of the tab strip; `scrollIntoView` also scrolls the window and
  breaks the 「定位」 jump. Centre the active tab once per region change (not on every re-render).
- Horizontal strips with hidden scrollbars are unreachable with a mouse (user report: "点到后面区域就回不到前面").
  Keep the ‹ › arrow buttons, the wheel→sideways handler and the thin scrollbar under `@media (pointer:fine)`, and
  test with a 1280 px mouse viewport as well as a touch phone viewport (9 regions overflow both).
- Escape `</` as `<\/` inside the JSON script blocks (assemble.py does it).
