---
name: asset-jobs
description: Queue generated assets (meshes, PBR materials, music, foley) from the GDD asset list for the GPU worker, write image briefs for missing references, and drop placeholders in so the game keeps running. Use for "/asset-jobs", "make the music", "generate the props", or the studio build stage.
---

# Asset jobs

Scope: $ARGUMENTS (default: everything in the GDD asset list that isn't final in `pipeline/ledger.json`)

1. `python3 pipeline/assets.py status` and read `pipeline/ledger.json` to see what exists, what's
   queued, what failed (fix the job or prompt and requeue failures).
2. For each needed asset, delegate by type: meshes and materials to `technical-artist`, music and
   foley to `audio-director`. Every prompt starts with the style bible's prompt prefix.
3. Mesh and PBR jobs need `game/assets/concept/<name>.png`. When it's missing, the technical-artist
   writes `docs/asset-briefs/<name>.md` instead and the asset is listed as waiting on the human.
4. `python3 pipeline/assets.py placeholders` so every queued asset exists at its final path now.
5. Wire assets into scenes by final path, run `scripts/check.sh`, commit the jobs and placeholders.
6. Report: queued, waiting on reference images, failed, and whether the GPU worker needs to run
   (`python3 pipeline/assets.py work --watch` on the GPU machine).
