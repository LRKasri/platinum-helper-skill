# Callouts brief — trophy-guide steps placed into the route

The page is for players who have never played the game. The trophy guide (roadmap), the endings guide and the
trophy notes tell them **when** to do things: back up the save before a choice, reload it later, which ending branch
to take first, what to finish before a point of no return, which story trophy pops where. The route must show these
at the exact spot, like `assets/sample_ui/8.png`: a red card titled 「点亮之前」 — "下一个铃铛是不可回头点：点亮后要一路
打到通关才能离开。先手动存档，确认真结局任务、五座龙柱、祝原和毕峰都已完成；没做完的现在回头补。" — then the checkpoint
item marked 【不可回头点】, then a 「成」 item for the story trophy that pops right there.

## Input
- `$W/tr_in/callouts.json`: `roadmap_en/zh` (trophy roadmap with its steps), `endings` (endings guide sections,
  English + the page's Chinese), `endings_guide_en` (the whole endings guide incl. its intro notices), `trophies` (name, description, category, missable, PowerPyx note en/zh).
- `$W/tr_in/callouts_route.tsv`: the route in order — `n`, `id`, region, step, `kind` (check / warn / save / note /
  tip), type, names, an English text excerpt. Items with kind warn / save already are callouts.
- Terminology: `$W/tr_brief.md`, `$W/glossary/glossary_merged.json`. Reuse the page's Chinese (roadmap_zh, endings
  text_zh, note_zh) wherever it says the same thing.

## What to produce
Go through the roadmap steps, every endings-guide step and every trophy note. For each instruction that depends on
*when* the player does something, decide where it belongs in the route and emit:

1. **callout** — a card without checkbox, placed `before` or `after` a route item id:
   - `kind: "save"` — back up / copy the save, or reload it ("备份存档", "读取备份"), with how (PS5 cloud / USB, Steam
     folder) only if the guide says so;
   - `kind: "warn"` — point of no return, ending branch / dialogue choice, "finish X before going on", "don't do Y",
     an ending's requirement the player must have done by now;
   - `title_zh`: 2–8 汉字, says when (点亮之前 / 存档备份 #1 / 结局分支 / 不可回头 / 读档回到这里); `body_zh`: what to do and
     why, complete (all items to finish, the exact option to pick, what is lost otherwise), official names, ≤ ~120 字;
     `title_en` / `body_en` from the guide's wording.
2. **trophy** — a 「成」 checkbox for a trophy that pops at a specific moment of the route (story bosses' trophies that
   aren't already linked, endings, "reach X", "first time Y"), `before`/`after` an item: `trophy` (exact English
   name), `body_zh`/`body_en` = when / how it unlocks (one sentence; add the choice if it depends on one).
   Skip trophies already linked to a route item (`linked_items`) and collection trophies.
3. **noreturn** — `item` id of an existing checkpoint / step that is itself the point of no return → it gets a
   【不可回头点】 tag (pair it with a warn callout before it).

Rules:
- **Don't duplicate**: if the route already has a warn / save item saying the same thing at that spot, skip it (or
  emit a callout only for what is missing). Wuchang's route already contains its save backups.
- Multi-ending games: lay out the guide's plan (minimum playthroughs, which ending first, where to back up, when to
  reload) along the route in order — a player following the page top to bottom must end up with every ending trophy.
  If an ending needs a second playthrough or a reload after the credits, put that callout at the end of the route
  (after the last item) and say exactly which save to load / what to do.
- Every callout cites its source: `source` ("roadmap" / "endings: <section>" / "trophy: <name>") and `quote_en` (≤ 300
  chars of the guide's sentence). Nothing invented; if the guide doesn't say where, place it at the first moment it
  matters (e.g. before the ending choice) and say so in `note`.
- Prefer few strong cards over many weak ones, but never leave out a save / reload / branch / no-return instruction.

**English-only builds** (`"lang": "en"`): fill only `title_en` (2–5 words: "Before Lighting It", "Backup Save #1")
and `body_en` (complete, ≤ ~60 words); leave out the `_zh` fields.

## Output `$W/tr_out/callouts.json`
```json
{"callouts": [
  {"where": "before", "item": "<id>", "kind": "save", "title_zh": "存档备份 #1", "body_zh": "…", "title_en": "Backup Save #1", "body_en": "…",
   "source": "endings: Important Notice", "quote_en": "…"}],
 "trophies": [{"where": "after", "item": "<id>", "trophy": "Shura", "body_zh": "…", "body_en": "…", "source": "…", "quote_en": "…"}],
 "noreturn": [{"item": "<id>", "source": "…", "quote_en": "…"}]}
```
Verify with python3 -I (ids exist in the TSV, trophy names exist, no duplicate cards at one spot) before replying.
Reply with the counts and the list of cards in route order (title_zh — one line each).
