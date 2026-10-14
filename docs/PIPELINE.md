# The pipeline, and what happened to the 15 repos

The first version of this repo treated the list as a game studio. For motion graphics and 3D models the list
looks different: more of it is useful, and the engine changes. Blender replaces the game engine, and five of the 15
become useful. Eight stay out on purpose.

## How it runs

```
 you ── brief ──▶ Claude Code (/studio)
                   │  art-director · motion-designer · modeler · sound-designer · qa-reviewer
                   │
                   ├─ writes pieces/*.py            post-edit hook: build the piece + one tiny QA'd frame on every save
                   │  renders previews on the CPU   Stop hook: can't finish until scripts/check.sh passes
                   │  opens its own contact sheets, critiques them, revises
                   │
                   └─ pipeline/jobs/pending/*.json ──git──▶ GPU machine: assets.py work --watch
                        render · music · foley · mesh · pbr                Blender finals (Cycles GPU)
                                                                           ACE-Step · Foley · TRELLIS.2 · CHORD
                   deliverables/ + assets/generated/ + ledger ◀──git──┘
                                                                  GitHub Actions: every push builds each piece and runs QA
```

Human gates: **A** pick a direction from the rendered concept sheet, **C** approve the files. `/studio auto` lets the
art-director agent take gate A; C always comes back to you.

## Verdicts

| # | Repo | Verdict | Why |
|---|------|---------|-----|
| 01 | [Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) | Borrowed the shape, not the 49 agents | Roles and gates are the right idea; 49 roles is overhead for one person (each agent starts cold and costs tokens). Five roles here. It is a game studio, so most of its skills don't apply. |
| 02-05 | UnrealClaude, Unreal_mcp, VibeUE, unreal-engine-skills | Out | Unreal can make beautiful real-time renders, but it needs an open editor on a big GPU machine. That's the opposite of "run it from a prompt." |
| 06 | UnrealGenAISupport | Out | LLMs inside a game. Not relevant to loops or models. |
| 07 | [Audio2Face-3D](https://github.com/NVIDIA/Audio2Face-3D) | Later, if a clip needs a talking face | Voice to facial animation. The SDK is MIT, the model weights use the NVIDIA Open Model License. |
| 08 | Unity-MCP, and Unity's official Claude plugin | Out | Unity is a game engine. Worth it only if the deliverable must be interactive or AR. |
| 09 | ml-agents | Out | Trains game NPCs. |
| 10 | godot-mcp | Out (was in the game version) | No game engine anymore. |
| 11 | [CHORD](https://github.com/ubisoft/ubisoft-laforge-chord) | **In** (`pbr` jobs) | One texture image in, base color, normal, height, roughness and metalness maps out, for materials on models. **Research-only license**: the ledger marks its output not for release, and the ship gate blocks it. |
| 12 | [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) | **In** (`music` jobs) | Soundtracks for loops. MIT, runs on modest VRAM, model card allows commercial use of generated music. |
| 13 | [HunyuanVideo-Foley](https://github.com/Tencent-Hunyuan/HunyuanVideo-Foley) | **In** (`foley` jobs) | This is its natural use now: it scores a rendered clip. One synced track for the whole clip (not per-event sounds). Tencent community license: check it for your use before shipping (`commercial_ok` defaults to false). |
| 14 | Hunyuan-GameCraft | Not wired | Image plus keys in, playable-looking video out. Could produce weirdcore source footage, but needs 24-80 GB VRAM, and its license wasn't confirmed. Treat as an experiment. |
| 15 | Matrix-Game | Not wired | Same reasoning: a world model you can wander in; not a deliverable pipeline. |

### Added, because the list had none
- **Blender (headless, as the `bpy` module).** The engine for both lanes. Scriptable, so Claude can write it and diff it,
  runs with no GPU or display, and Cycles gives real chrome reflections. Installs from PyPI in about 30 seconds.
- **[TRELLIS.2](https://github.com/microsoft/TRELLIS.2)** (Microsoft, MIT): image to GLB, for organic shapes the
  procedural kit can't do. None of the 15 made 3D models.

### What's still missing
- **Typography.** Titles and lyrics over loops are common and the kit has no text helper yet. Blender can do it; it needs
  a font in the repo and a tested helper. The better lane for text-heavy 2D clips may be Remotion (React to video), added
  as a second engine if you need it.
- **Reference images for TRELLIS.2 and CHORD.** Those start from a picture; the owner supplies them (`assets/concept/`).
- Judging taste. The checks catch broken; the art-director agent and you catch generic.

## GPU machine

One 24 GB card (3090/4090) runs every job, one at a time:

| Job | Tool | VRAM (reported) | OS | License | Ship output? |
|---|---|---|---|---|---|
| `render` | Blender Cycles (OptiX/CUDA) | any NVIDIA card works | Win / Linux / Mac | GPL (output is yours) | yes |
| `music` | ACE-Step 1.5 | under 4 GB claimed, offloads below 16 GB | Win / Linux / Mac | MIT | yes |
| `mesh` | TRELLIS.2 | ~24 GB | Linux only (WSL2 on Windows) | MIT | yes |
| `pbr` | CHORD | see repo | see repo | Ubisoft ML License, research-only | **no** |
| `foley` | HunyuanVideo-Foley | ~20 GB, ~12 GB with offload | Linux / Win | Tencent Hunyuan Community | check terms |

Setup:
1. Clone this repo on the GPU machine and run `scripts/install-blender.sh`.
2. Install the AI models you want, each per its README.
3. `cp pipeline/worker.example.toml pipeline/worker.toml` and fill in `cwd` and `command` for each model (the `REPLACE_ME`
   entries are deliberate: these CLIs change between releases, so the worker refuses to run one you didn't set).
   The `render` job needs no model config.
4. `python3 pipeline/assets.py work --watch`. It pulls, runs pending jobs, commits the results and the ledger, and pushes.
   Set `branch` in `worker.toml` to the branch your Claude sessions push to.

Without a worker, previews and small renders run on the CPU, and AI assets are placeholders at their final paths.
`python3 pipeline/assets.py status` shows what's waiting.

## Cost reality

Measured on 4 CPU cores: about 8 s per 540 px frame at 32 samples, so a 96-frame preview-quality loop takes ~15 minutes
and a 1080 px, 96-sample version would take hours. That's the reason finals are GPU jobs.

## What stays human

Choosing a direction, approving the files, reference images, license calls on anything Tencent- or Ubisoft-licensed, and
posting or selling. The agents can tell you the render is broken or the loop doesn't close. They can't tell you it slaps.
