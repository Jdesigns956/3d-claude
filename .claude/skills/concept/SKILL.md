---
name: concept
description: Turn a pitch into three genuinely different game concepts sized for this pipeline, for the human to choose from (Gate A). Use for "/concept <pitch>" or when the studio is at the concept stage.
---

# Concepts

Pitch: $ARGUMENTS (if empty, use the pitch in `docs/STUDIO_STATE.md`)

Write three concepts to `docs/concepts/1-<slug>.md`, `2-<slug>.md`, `3-<slug>.md`. They must differ in
**core verb, camera and tone**, not just theme or color. Each gets its own palette identity (hex values),
not a recolor of the others.

Each file:
- Title and one-line hook
- Core verb and 30-second loop
- Camera and controls
- Why it's fun (the specific tension or payoff)
- Look: palette (5 hex values with roles), materials, the one image that sells it
- Sound: music direction in ACE-Step tag style
- Scope: milestones to a vertical slice (aim for 3-4), asset count by type (mesh / pbr / music / foley)
- Pipeline fit: what TRELLIS.2, CHORD, ACE-Step and foley each contribute; what would need hand work
- Biggest risk and how M1 tests it

Then write `docs/concepts/README.md`: a comparison table and your recommendation with the reason.

Use the `creative-director` agent to review the three for genericness and scope before presenting.

**Gate A**: present the table and recommendation, ask which one (or which mix). In `mode: auto`,
the creative-director picks and logs the reason in `docs/STUDIO_STATE.md`. Record the choice as
`concept:` in the state file.
