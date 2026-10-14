# 3D Claude

A game studio in a repo: Claude Code agents build a Godot 4.6 game from a one-line pitch, a GPU
worker generates the assets, and CI tests and exports every build. You make three calls along the
way (which concept, does the slice feel right, ship it), or one if you run it in auto mode.

```
/studio a chrome pinball rave where the ball is a disco mirror
/studio auto a cozy salvage game on a flooded mall roof
/studio            # continue where the last session stopped
```

Why these tools and not the other 11 from the list: [docs/PIPELINE.md](docs/PIPELINE.md).

## What's here

| Path | What it does |
|---|---|
| `.claude/skills/` | `/studio` autopilot plus its stages: `concept`, `gdd`, `milestone`, `asset-jobs`, `playtest`, `ship` |
| `.claude/agents/` | creative-director, game-designer, gameplay-programmer, technical-artist, audio-director, qa-tester |
| `.claude/hooks/` | parse-check on every GDScript edit; Claude can't finish while the game check fails; Godot auto-install in cloud sessions |
| `.mcp.json` | godot-mcp: run the game and read its errors from inside Claude |
| `game/` | Godot 4.6 starter: third-person controller, test level, headless smoke test, Linux/Windows export presets |
| `pipeline/assets.py` | asset job queue, GPU worker, placeholders, license ledger and ship gate |
| `.github/workflows/game.yml` | every push: import, parse, smoke test, pipeline tests. Tag `v*`: ship gate, exports, release |

## Quick start

**Claude Code on the web:** open this repo and run `/studio <pitch>`. The session hook installs Godot.

**On your machine:**
1. Install [Godot 4.6.3](https://godotengine.org/download) and Node 18+. Set `GODOT=/path/to/godot` if it isn't on PATH.
2. `scripts/check.sh` should end with `check.sh: OK`.
3. `claude`, then `/studio <pitch>`.

**GPU worker (optional, for real assets):** see [docs/PIPELINE.md#gpu-machine](docs/PIPELINE.md#gpu-machine).
Until it runs, the game uses placeholder meshes, textures and audio at the final file paths, and the
ship gate won't let a placeholder into a release.

## Checks

```
scripts/check.sh                              # Godot import + parse + gameplay smoke test
python3 -m unittest discover -s pipeline/tests
python3 pipeline/assets.py gate --ship        # anything placeholder or not cleared for commercial use?
```
