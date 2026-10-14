---
name: ship
description: Prepare a release build. License and placeholder gate, Linux and Windows exports, a headless run of the exported binary, and release notes, then stop for human approval. Use for "/ship" or the studio ship stage.
---

# Ship

1. `python3 pipeline/assets.py gate --ship`. If blocked, list every placeholder and non-commercial
   asset with what replaces it (rerun with a cleared model, hand-made, or CC0) and stop. Don't fake it.
2. `scripts/check.sh` must pass.
3. `scripts/install-export-templates.sh` (once per machine), then:
   `godot --headless --path game --export-release "Linux" ../build/linux/3d-claude.x86_64` and
   `godot --headless --path game --export-release "Windows" ../build/windows/3d-claude.exe`.
4. Smoke the export: `build/linux/3d-claude.x86_64 --headless --quit-after 300` must exit 0 with no `SCRIPT ERROR`.
5. Write `docs/RELEASE_NOTES.md` (what's in, known issues from `docs/BUGS.md`, asset credits from the ledger
   with each model and license).
6. **Gate C**: report the build paths and the gate result. Releasing (itch.io, Steam, tags) is the human's call,
   even in auto mode. If they approve a tag, pushing `v*` makes CI build and attach the exports.
