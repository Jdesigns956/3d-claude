# 3D Claude

A motion graphics and 3D model studio in a repo. Describe what you want; Claude Code agents write it as Blender
scenes, render it headless, look at their own renders, run technical QA, and hand you files: seamless loops (MP4, GIF,
transparent WebM/ProRes), turntables, and 3D models (GLB, STL, OBJ). You make the taste calls: pick a direction, approve
the files.

```
/studio a chrome mandala loop, butter and oxblood, for a 1080 square and a 9:16 story
/studio auto a 44 mm pendant charm, pistachio and cherry, print-ready
/studio            # continue where the last session stopped
```

## What's here

| | |
|---|---|
| `pieces/chrome_mandala_loop.py` | 4 s seamless loop: recursive chrome petal rings, depth of field, bloom and grain |
| `pieces/mandala_medallion.py` | 44 mm pendant with a hanging eyelet: watertight shells, GLB + STL + OBJ |
| `showcase/` | what they render to |
| `studio/` | the kit (chrome, lights, depth, loops), renderer, QA checks, post effects |
| `.claude/` | `/studio` autopilot + stage skills, five agents (art director, motion designer, modeler, sound designer, QA), hooks |
| `pipeline/` | job queue for a GPU worker: final renders, ACE-Step music, Foley, TRELLIS.2 meshes, CHORD materials, license ledger |

Why these tools and not the 15 from the original list: [docs/PIPELINE.md](docs/PIPELINE.md).

## Quick start

**Claude Code on the web:** open the repo and run `/studio <brief>`. The session hook installs Blender.

**Local:** Python 3.13, ffmpeg, then:
```
scripts/install-blender.sh          # headless Blender as a Python module, about 400 MB, no GPU or display needed
scripts/check.sh                    # should end with: check.sh: OK
.tools/venv/bin/python studio/run.py chrome_mandala_loop --mode preview     # ~80 s on 4 CPU cores
```
Open `output/chrome_mandala_loop/preview/contact_sheet.png`.

**GPU worker (optional):** finals at 1080 px are about 12x the CPU cost per frame, so they go to a GPU machine:
see [docs/PIPELINE.md](docs/PIPELINE.md#gpu-machine). Without one, previews and small renders run on the CPU.

## Checks

```
scripts/check.sh                                # every piece builds and passes QA on a tiny frame
python3 -m unittest discover -s pipeline/tests  # job queue
python3 pipeline/assets.py gate --ship          # any placeholder or non-commercial asset left?
```

Reference: [docs/KIT.md](docs/KIT.md) (piece contract), [docs/CRAFT.md](docs/CRAFT.md) (lessons), [docs/TASTE.md](docs/TASTE.md) (house taste).
