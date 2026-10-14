---
name: motion
description: "Build and refine a motion piece (loop, VJ visual, animated symbol) until it passes QA and the art-director's review. Use for \"/motion <piece>\", \"make the loop\", or the studio build stage for motion."
---

# Motion piece

Target: $ARGUMENTS (default: `piece` in `docs/STUDIO_STATE.md`)

Delegate to the `motion-designer` agent with the brief, the chosen direction, `docs/CRAFT.md`, and these steps:

1. Start from the chosen direction's file; keep what the human picked.
2. Iterate: write, `--mode preview --quick`, **look at the contact sheet**, fix; then `--mode preview` for the six-frame
   sheet and the loop seam check. The loop check must pass.
3. `art-director` reviews the sheet and gives at most three targeted notes per round. Apply, re-render, repeat; at most
   six rounds, then hand back with a plain list of what's unsolved.
4. Check the other formats the brief asks for: `--mode preview --quick --size WxH` for each (a 9:16 version needs its
   own look at the crop). If a format needs a different composition, say so; don't stretch.
5. `scripts/check.sh` passes, commit `studio: <piece> - motion build done`, update the state file.
