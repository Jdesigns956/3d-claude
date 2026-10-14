# The pipeline, and what happened to the 15 repos

Short version: one engine, six agents, one GPU queue. Of the 15 repos, 4 are wired in, 3 are
optional later, and 8 are left out on purpose: they're for a different engine, or they generate
video instead of game assets.

## How it runs

```
 you ── pitch ──▶ Claude Code (/studio)                         GitHub Actions
                   │  creative-director · game-designer          on every push: Godot import,
                   │  gameplay-programmer · technical-artist     parse, smoke test, pipeline tests
                   │  audio-director · qa-tester                 on tag v*: ship gate, Linux +
                   │                                             Windows export, attach to release
                   ├─ edits game/ (Godot 4.6)
                   │    post-edit hook: parse-check every .gd
                   │    stop hook: can't finish until scripts/check.sh passes
                   │    godot-mcp: run the game, read runtime errors
                   │
                   └─ pipeline/jobs/pending/*.json ──git──▶ GPU machine: assets.py work --watch
                        + placeholders at final paths            ACE-Step · TRELLIS.2 · CHORD · Foley
                                                                 │
                   game/assets/generated/ + ledger.json ◀──git──┘
```

Placeholders and final assets share the same path, so the game always runs, and real assets
replace the stand-ins with no scene changes when the worker pushes them.

Human gates: **A** pick a concept, **B** play the vertical slice, **C** approve a release.
With `/studio auto ...` the creative-director agent decides A and B; C always comes back to you.

## Verdicts

| # | Repo | Verdict | Why |
|---|------|---------|-----|
| 01 | [Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) | Borrowed the idea, not the 49 agents | The studio hierarchy is the right shape, but 49 roles is mostly overhead for one person: each agent starts cold and costs tokens. Six roles here cover it. MIT, so you can drop it in later if you want the full org chart. |
| 02-05 | UnrealClaude, Unreal_mcp, VibeUE, unreal-engine-skills | Out (Unreal path) | All good if you commit to Unreal. Unreal needs a big Windows box with the editor open, and minute-long C++ builds. That's the opposite of "as automatic as possible". |
| 06 | UnrealGenAISupport | Out | LLM-driven NPCs are a design decision with per-player API costs, not a pipeline step. |
| 07 | [Audio2Face-3D](https://github.com/NVIDIA/Audio2Face-3D) | Later, maybe | Only matters for talking 3D faces. The SDK is MIT, the model weights use the NVIDIA Open Model License, and the plugin targets UE5, so Godot needs a blendshape import step. |
| 08 | Unity-MCP | Alternative engine | If you go Unity, start with Unity's official Claude Code plugin (Sept 2026) and add Unity-MCP for in-game/runtime AI. |
| 09 | ml-agents | Out on Godot | Unity only. The Godot equivalent is godot_rl_agents, if a design ever needs trained NPCs. |
| 10 | [godot-mcp](https://github.com/Coding-Solo/godot-mcp) | **In** | `.mcp.json`. Runs the project, reads debug output, does scene/node operations. MIT. |
| 11 | [CHORD](https://github.com/ubisoft/ubisoft-laforge-chord) | **In, prototype only** | Great image → PBR maps, but **research-only license**. The ledger marks its output `commercial_ok: false` and the ship gate blocks it. |
| 12 | [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) | **In** | MIT, small VRAM footprint, and the model card allows commercial use of generated music. |
| 13 | [HunyuanVideo-Foley](https://github.com/Tencent-Hunyuan/HunyuanVideo-Foley) | **In, for trailers/cutscenes** | Scores a video clip; the worker records gameplay with Godot's Movie Maker first. It makes one synced track, not per-event SFX. Tencent community license: check it for your territory before shipping (`commercial_ok` defaults to false). |
| 14 | Hunyuan-GameCraft | Out of the pipeline | Outputs *video of* a game, not a game. Fine for a mood or pitch clip if you have 24-80 GB of VRAM. |
| 15 | Matrix-Game | Out of the pipeline | Same: a real-time world model you can walk around in, but nothing you can ship. |

### What the list is missing
- **3D models.** None of the 15 make meshes, and this is a 3D repo. Added
  [TRELLIS.2](https://github.com/microsoft/TRELLIS.2) (Microsoft, MIT, image → GLB with PBR).
- **Reference images.** TRELLIS.2 and CHORD both start from a picture. That part stays yours, from
  whatever image generator you already use. The technical-artist agent writes a brief per asset in
  `docs/asset-briefs/`, and you drop the PNG in `game/assets/concept/`.
- **Interactive SFX.** Foley-from-video is for linear clips. One-shots (jump, hit, pickup) come from a
  CC0 library or short sliced foley captures.

## GPU machine

Jobs run one at a time, so one 24 GB card (3090/4090) covers everything:

| Model | VRAM (reported) | OS | License | Ship output? |
|---|---|---|---|---|
| ACE-Step 1.5 | under 4 GB claimed, auto-offload below 16 GB | Win / Linux / Mac | MIT | yes |
| TRELLIS.2 | ~24 GB | Linux only (use WSL2 on Windows) | MIT | yes |
| CHORD | see repo | see repo | Ubisoft ML License, research-only | **no** |
| HunyuanVideo-Foley | ~20 GB, ~12 GB with offload | Linux / Win | Tencent Hunyuan Community | check terms |

Setup:
1. Clone this repo on the GPU machine, install each model per its README.
2. `cp pipeline/worker.example.toml pipeline/worker.toml`, then fill in `cwd` and `command` for each model
   (the `REPLACE_ME` entries are deliberate; the worker refuses to run them).
3. `python3 pipeline/assets.py work --watch`. It pulls, runs pending jobs, commits the assets and ledger, and pushes.
4. Set `branch` in `worker.toml` to the branch your Claude sessions push to.

Without a GPU worker everything still runs on placeholders; `python3 pipeline/assets.py status`
shows what's waiting.

## Why Godot and not Unity

Godot is the only one of the three that runs fully headless on a Linux box with no license: import,
test and export all work in a cloud session and in CI (verified with 4.6.3). Scenes are plain text, so
Claude can diff and review them. Unity now has an official Claude Code plugin
(`claude plugin install unity@unity-agent-plugin`) and is a good choice if you already know it, but it
expects an open, licensed Editor, so less of the loop runs without you.

## What stays human

Concept choice and the feel of the vertical slice (gates A and B, unless you run auto mode), reference
images, license calls on Foley and anything Tencent-licensed, and pressing release. Headless tests prove
the game works. They can't tell you it's fun.
