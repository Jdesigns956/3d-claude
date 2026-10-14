---
name: studio
description: "Studio autopilot for motion graphics and 3D models. Takes a one-line brief to delivered files by running the concept, motion or model, review and deliver stages, stopping only at human gates. Use for \"/studio <brief>\", \"/studio auto <brief>\", \"/studio\" (continue), \"make me a loop of ...\", \"make a 3D model of ...\"."
---

# Studio autopilot

Arguments: $ARGUMENTS

State lives in `docs/STUDIO_STATE.md` (committed, so any session can resume). Read it first.

## Start or resume
- A brief in the arguments with state `stage: brief` → record it. Starting with `auto` sets `mode: auto`
  (the `art-director` agent decides Gate A and logs why); otherwise `mode: guided`.
- No arguments → continue from the recorded stage.
- Decide the kind from the brief: "loop", "visual", "animation", "VJ", "clip" is motion; "model", "charm",
  "pendant", "print", "STL" is model; both is allowed (one piece each, shared palette identity is optional).

## Stages
| stage | do | ends with |
|---|---|---|
| brief | `art-director` writes `docs/briefs/<slug>.md` (see its instructions) | brief committed |
| concept | run the `concept` skill | **Gate A**: human picks a direction (auto: art-director picks) |
| build | run the `motion` skill (motion) or `model` skill (model) on the chosen direction | piece passes preview + art-director review |
| review | run the `review` skill | PASS from `qa-reviewer` |
| deliver | run the `deliver` skill | **Gate C**: human approves release of the files. Never upload or post anywhere. |

There is no Gate B here; the human sees the contact sheet at Gate A and the finals at Gate C. If the brief is large
(a set of pieces), repeat build, review and deliver per piece and keep the list in the state file.

## Rules for the loop
- Keep going stage to stage without asking, until a gate, a blocker, or the end. At a gate, stop and present exactly what
  the human must decide, with your recommendation and the image to look at.
- After each stage update `docs/STUDIO_STATE.md` (stage, mode, choices, one log line) and commit
  (`studio: chrome mandala loop - build done`). Push if the session normally pushes.
- `scripts/check.sh` must pass before any commit that touches `studio/`, `pieces/` or `pipeline/`. The Stop hook enforces it.
- Look at your own renders (open the PNG contact sheets) before showing anything. Don't hand over something you wouldn't pick.
- Missing GPU worker or reference images never block the work: previews run on CPU, placeholders stand in, and the
  stage notes what the human needs to provide.
- What can't be automated (taste, license calls, release) goes in the gate summary. Don't guess.
