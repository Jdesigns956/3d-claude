---
name: studio
description: Studio autopilot. Takes a game from pitch to exported build by running the concept, gdd, milestone, asset-jobs, playtest and ship stages in order, stopping only at human gates. Use for "/studio <pitch>", "/studio auto <pitch>", "/studio" (continue), "keep building the game", or "next milestone".
---

# Studio autopilot

Arguments: $ARGUMENTS

All state lives in `docs/STUDIO_STATE.md` (committed, so any session can resume). Read it first.

## Start or resume
- Arguments contain a pitch and the state is `stage: pitch` → record the pitch. If the arguments start
  with `auto`, set `mode: auto`; otherwise `mode: guided`.
- No arguments → continue from the recorded stage.
- `mode: auto` is the user asking for maximum automation: the `creative-director` agent decides Gates A
  and B and logs why. Gate C (release) is always the human's.

## Stages
| stage | do | ends with |
|---|---|---|
| pitch → concept | run the `concept` skill | **Gate A**: human picks a concept (auto: creative-director picks) |
| design | run the `gdd` skill | GDD, style bible, milestones committed |
| build | for the next unfinished milestone: `milestone` skill, then `asset-jobs`, then `playtest` | milestone marked done |
| slice review | after the milestone the GDD calls the vertical slice | **Gate B**: human plays the build using `docs/PLAYTEST.md` (auto: creative-director reviews the playtest report) |
| build (cont.) | remaining milestones, same loop | all milestones done |
| ship | run the `ship` skill | **Gate C**: human approves release. Never upload anywhere. |

## Rules for the loop
- Keep going stage after stage without asking, until a gate, a blocker, or the end. At a gate, stop
  and present exactly what the human must decide, with your recommendation.
- After each stage: update `docs/STUDIO_STATE.md` (stage, current milestone, gate results, a one-line
  log entry), then commit with a message like `studio: M2 combat loop done`. Push if the session
  normally pushes.
- `scripts/check.sh` must pass before any commit that touches `game/`. The Stop hook enforces this.
- Missing reference images or a GPU worker never block the build: placeholders stand in, and the stage
  notes what the human should provide.
- If something can't be automated (feel, art taste, license calls), say so and put it in the gate
  summary instead of guessing.
