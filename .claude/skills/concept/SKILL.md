---
name: concept
description: "Turn a brief into three genuinely different directions as a rendered concept sheet, for the human to choose from (Gate A). Use for \"/concept <brief>\", \"show me options\", or when the studio is at the concept stage."
---

# Concept sheet

Brief: $ARGUMENTS (default: `docs/briefs/` for the current slug)

1. Three directions that differ in **composition, central symbol and mood**, not just color. Give each its own palette
   identity (`docs/TASTE.md`). If two only differ by palette, replace one.
2. Build each as a quick piece, `pieces/<slug>_a.py`, `_b.py`, `_c.py`: rough is fine, but real geometry and a real
   palette, because the sheet is what the human judges. Delegate to `motion-designer` or `modeler`, one per direction
   (they can run in parallel).
3. Render the first frame of each: `.tools/venv/bin/python studio/run.py <piece> --mode preview --quick`. Open the images
   yourself; fix anything broken or muddy before it goes on the sheet.
4. Tile them: `python3 studio/sheet.py docs/briefs/<slug>/sheet.png <a>.png <b>.png <c>.png --labels "A  <name>" "B  <name>" "C  <name>"`.
5. `art-director` writes `docs/briefs/<slug>/directions.md`: one paragraph per direction (symbol, palette with hex, motion
   or form idea, risk) and a recommendation with the reason.

**Gate A**: show the sheet and the recommendation and ask which direction (or which mix). In `mode: auto`
the art-director picks and logs the reason. Delete the directions that lost: `git rm pieces/<slug>_b.py pieces/<slug>_c.py`
(the chosen one is renamed to `pieces/<slug>.py` and becomes the piece to build). Record `direction:` in the state file.
