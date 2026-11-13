# Gates brief — 奖杯前置: skippable prerequisites the guide names

The page marks three levels (agreed with the user):

| level | rule | page |
|---|---|---|
| 奖杯本体 | the checkbox itself counts: collectible, the boss / ending that pops the trophy | gold trophy chip (already done) |
| **奖杯前置** | ① without it a trophy (or a trophy collectible / boss / ending) can't be obtained, ② a player can skip it — not on the forced story path, ③ **PowerPyx's own text states the dependency** | 「前置 · 《奖杯》」 chip, counts as 奖杯相关 |
| not marked | story items everyone gets anyway; dependencies only inferred, not written | body text only |

Example that qualifies (Sekiro): 少主的守护铃 — Hirata Estate is an optional area, and PowerPyx writes in Prosthetic
Tool #3 and Prayer Bead #6: "To unlock Hirata Estate region you must talk to an old woman … She gives you a bell".
Without it: Flame Barrel (All Prosthetic Tools), beads (Peak Physical Strength), Lady Butterfly (boss trophy), Hirata
for Ashina Traveler.

Rule ③ is what keeps this small. By inference almost every story key leads to some collectible; then 只看奖杯相关 shows
everything and is useless. Only sentences that say it: "requires X", "you must first …", "to unlock X you need …",
"only possible after …", "talk to X / choose Y or the quest (trophy) is lost", "you need the X key to open …".

## Input
- `$W/tr_in/gates.json`: `trophies` (name, description, PowerPyx note), `roadmap_en`, `bytype_entries` (collectible
  list entries: `src`, `trophy`, label, text), `trophy_items` (checkboxes already linked to a trophy, with their text),
  `questlines` (NPC questline guide text, if any).
- `$W/tr_in/gates_items.tsv`: every checkbox on the page (id, type, names, place, trophies already linked, optional).
  Gates must point at one of these ids.

## What to do
Read the sources (use python3 -I to grep for: requir, must, need, first, unlock, only (possible|available) after,
before, key, choose, talk to, otherwise, locks?, prerequisite). For each dependency found:
1. Is the needed thing a checkbox in gates_items.tsv? Find its id (match by name, place, order). If the needed thing
   is itself already linked to that same trophy, skip it (already 奖杯本体).
2. Is it skippable? It is NOT if the text or the item makes it forced story progress (main boss you must beat, item
   "automatically" received, the only way forward). Optional areas, side NPCs, optional keys, dialogue choices,
   merchants, side quests are skippable.
3. Which trophies does it gate? Name them exactly (English trophy names from `trophies`). A gate for a collectible
   entry counts for that collection's trophy.

Apply the three conditions strictly — there is no target count (Sekiro 5, Phantom Blade Zero 42, Wuchang 66 were
all right). When the needed thing has no checkbox, put it in `missing` instead.

## Decide like this (the user approved these calls on Sekiro / Wuchang / Phantom Blade Zero)
- Keep: optional-area keys and items (少主的守护铃), side NPCs whose questline the guide ties to an ending or a
  trophy item — **every step** of such a questline (Wuchang 何有哉 / 方瑶 / 年岁长 …), optional bosses whose drop a
  trophy needs (七面武士 → 爱哭鬼的指环), keys and switches to rooms with trophy items, optional region entrances.
- Drop: ending-branch choices (the page already shows them as red notes and flags the trophies 易错过; a chip would
  list a dozen trophies), steps forced once a branch is chosen (永真 in the Shura route), alternatives that have
  another way in (a key when the river route also reaches the boss), steps already written inside the trophy item's
  own text, and anything that only feeds a "pick any N" collection (30 of 63 accessories) — don't even list those.
- `"level": "self"` instead of a gate when the checkbox itself pops or counts for the trophy and just wasn't linked:
  the final shop hand-in, the merchant that sells the trophy weapon, a challenge that is the trophy's own content.
  Give the trophy it counts for.

**English-only builds** (`"lang": "en"`): give `reason_en` (one short English line) instead of `reason_zh`.

## Output `$W/tr_out/gates.json` (applied by assemble.py) and `$W/gates_review.md`
```json
{"gates": [
  {"item": "<checkbox id>", "name_zh": "少主的守护铃", "trophies": ["All Prosthetic Tools", "Peak Physical Strength", "The Phantom Lady Butterfly", "Ashina Traveler"],
   "quote_en": "To unlock Hirata Estate region you must talk to an old Woman … She gives you a bell …",
   "source": "bytype:tool-3", "skippable": "Hirata Estate is optional", "reason_zh": "不拿就进不了平田宅邸（可跳过的区域）"}
 ],
 "missing": [{"needed": "…", "trophies": ["…"], "quote_en": "…", "source": "…"}],
 "rejected_examples": [{"needed": "…", "why": "forced story / only inferred"}]}
```
`reason_zh` is one short Chinese line shown on the page under the item (official names). `gates_review.md`: one line
per gate (name_zh → 《trophies》 — reason) plus the dropped candidates with why, for the final report. Verify ids
exist in the TSV and trophy names exist, with python3 -I, before replying. Reply with the count and the 3–5 most
borderline cases.
