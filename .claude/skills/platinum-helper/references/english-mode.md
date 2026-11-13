# English-only mode

For English-speaking readers. The page keeps every feature (one checkbox per entity, boss-guide bosses in order,
checklist drops, 奖杯前置 → "Prereq" chips, trophy-guide cards, missables, all-bosses checklists) but has no Chinese
and no language toggle. It skips the two most expensive stages — official-name research (§3) and unit translation
(§4) — so it costs roughly a third of the subagent tokens of a Chinese build (Wuchang Chinese: 3 research + 6
translation agents before the later stages).

## Switch it on
`"lang": "en"` in `$W/game.json` (default `"zh"`). Effects:
- assemble.py fills every Chinese field with the English text, reports no missing translations, titles the page
  "<Game> Platinum Helper", and tells the template to start in English and hide the 中/EN button;
- qa_check.py skips the Chinese checks (English left in Chinese fields, glossary misses);
- controller buttons are written in English ([L-Stick ↑], [○]).

## Pipeline
1. §1–2 as usual (discover, fetch, game.json, build_en, build_en2, fetch_images, English preview).
2. Skip §3 (glossary) and the unit translation in §4.
3. **Region notes job** (small, replaces what translators wrote alongside the units): run
   `python3 -I $SKILL/scripts/prepare_tr.py $W` and give each `tr_in/route-NN.json` to an agent with this brief:
   read the region's items and write `$W/tr_out/route-NN.json` as
   ```json
   {"regions": {"<region id>": {"summary_en": "1–2 sentences: what this region is about and its biggest trap",
                               "leave": [{"en": "a missable thing to finish before leaving"}],   // 3–6
                               "colinfo_en": "one paragraph about this region's collectibles"}},  // regions listed in the job
    "areas": {"<step id>": {"tagline_en": "≤ 60 chars: what happens in this step"}},
    "units": {}}
   ```
   Leave bullets must come from the guide's text (missable / point of no return / "before leaving"), not judgment.
   One agent can take several route jobs — it only reads and writes a few lines per region.
4. Prose walkthroughs / combined titles: `prepare_entities.py` + `entities-brief.md` — fill only `name_en` and
   `body_en` (omit the `_zh` fields; use the guide's sentences as they are).
5. Assemble. Boss-guide bosses missing from the route are inserted with their English text; nothing to translate.
6. `prepare_gates.py` + `gates-brief.md` — give `reason_en` (one short line shown under the item) instead of
   `reason_zh`.
7. `prepare_callouts.py` + `callouts-brief.md` — fill only `title_en` / `body_en` (titles 2–5 words: "Before Lighting
   It", "Backup Save #1", "Ending Branch"; bodies complete, ≤ ~60 words).
8. Assemble + QA + screenshots as in §6. Report in the user's language.

The same build directory can produce both versions: run the Chinese pipeline, then copy `game.json` with
`"lang": "en"` into a second work dir together with `data_en/`, `images/` and the entity / gates / callouts outputs
(they already carry English fields) — no new agents needed.
