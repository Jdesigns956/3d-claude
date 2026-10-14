---
name: milestone
description: Implement the next milestone from docs/MILESTONES.md in Godot, with a smoke-test check per acceptance criterion, until scripts/check.sh passes. Use for "/milestone", "build M2", or the studio build stage.
---

# Build a milestone

Target: $ARGUMENTS (default: `current_milestone` in `docs/STUDIO_STATE.md`)

1. Read the milestone's tasks, the GDD tuning table and the style bible.
2. For each task, in order, delegate to the `gameplay-programmer` agent with: the task, its acceptance
   criteria, the relevant tuning values, and the files it will likely touch. One task per delegation
   keeps context small. Independent tasks touching different files can run in parallel.
3. After each task: `scripts/check.sh` must pass. Commit (`M<n>: <task>`).
4. When the milestone needs assets that aren't in the ledger yet, run the `asset-jobs` skill for just
   those assets so placeholders exist at the final paths.
5. Mark the milestone's tasks done in `docs/MILESTONES.md`, then hand off to the `playtest` skill.

Don't add features the milestone doesn't list. If a task turns out bigger than planned, split it in
`docs/MILESTONES.md` and say so instead of half-finishing it.
