---
name: model
description: "Build and refine a 3D model (display, print, merch) with mesh QA and GLB/STL/OBJ export until it passes QA and the art-director's review. Use for \"/model <piece>\", \"make the 3D model\", or the studio build stage for models."
---

# Model piece

Target: $ARGUMENTS (default: `piece` in `docs/STUDIO_STATE.md`)

Delegate to the `modeler` agent with the brief, the chosen direction and `docs/CRAFT.md`:

1. Pin the real-world size and use first (print, web/AR, mockup render): it sets `printable`, `max_tris` and the minimum feature size.
2. Iterate: write, `--mode preview` (eight turntable angles + exports + mesh QA), **look at the contact sheet**, fix.
   All mesh FAILs in `report.json` must be gone; explain each WARN.
3. `art-director` reviews the sheet (silhouette from every side, not just the hero angle). At most six rounds.
4. If the brief needs organic or sculpted forms, say the procedural kit can't do it well and queue a `mesh` job
   (TRELLIS.2 on the GPU worker) from a reference image the human supplies, then clean up the result.
5. `scripts/check.sh` passes, commit `studio: <piece> - model build done`, update the state file.
