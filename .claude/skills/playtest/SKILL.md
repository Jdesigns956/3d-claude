---
name: playtest
description: QA pass on the current build. Headless check, new regression checks from acceptance criteria, bug log, asset/license status, and a five-minute playtest card for the human. Use for "/playtest" or after a milestone.
---

# Playtest

1. Delegate to the `qa-tester` agent for the current milestone (see its instructions).
2. Read `docs/BUGS.md`. Severity high → back to `gameplay-programmer` now, then re-run `scripts/check.sh`.
3. If the human left feel notes in `docs/PLAYTEST.md` (under "Human notes"), turn them into tuning changes
   via the `game-designer` agent (numbers before new mechanics), then implement.
4. Update `docs/STUDIO_STATE.md`: milestone done or not, open bugs, placeholders remaining. Commit.
5. If this milestone is the vertical slice, stop at **Gate B** with the playtest card and a clear ask:
   "play it, add notes under Human notes, then run /studio".
