# 3D Claude: game studio repo

A Godot 4.6 game built by Claude Code agents, with generated assets from a GPU worker.
Studio flow: `/studio <pitch>` (see `.claude/skills/studio/SKILL.md`). State: `docs/STUDIO_STATE.md`.

## Layout
- `game/`: the Godot project. Scenes `game/scenes/`, scripts `game/scripts/`, tests `game/tests/smoke_test.gd`.
- `game/assets/generated/`: written only by `pipeline/assets.py`. Never hand-place, move or rename files here.
- `game/assets/concept/`: reference images from the human (inputs for mesh/pbr jobs).
- `pipeline/`: asset job queue, GPU worker, license ledger (`pipeline/ledger.json`).
- `docs/`: GDD, style bible, milestones, bugs, playtest card, pipeline notes (`docs/PIPELINE.md`).

## Commands
- `scripts/check.sh`: import + parse every script + gameplay smoke test. Must print `check.sh: OK` before any commit touching `game/`.
- `scripts/check.sh --file game/scripts/x.gd`: parse one script.
- `python3 pipeline/assets.py enqueue|status|placeholders|gate`: asset jobs (details: `python3 pipeline/assets.py -h`).
- `python3 -m unittest discover -s pipeline/tests`: pipeline tests.

## Rules
- Edit game files with Edit/Write, not sed or heredocs: the post-edit hook parse-checks GDScript and the
  Stop hook runs the full check before you can finish.
- Typed GDScript, `@export` for every tuning value, input via actions in `project.godot`.
- Every new mechanic gets a check in `game/tests/smoke_test.gd`.
- Asset prompts start with the prompt prefix in `docs/STYLE_BIBLE.md`.
- Don't edit `game/.godot/`, `.tools/`, or `pipeline/ledger.json` by hand.
- Never publish a build or upload anywhere; releasing is the human's call.
