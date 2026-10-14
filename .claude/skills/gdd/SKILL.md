---
name: gdd
description: Write the game design doc, style bible and milestone plan for the chosen concept. Use for "/gdd" or when the studio is at the design stage.
---

# Design docs

1. `game-designer` agent: write `docs/GDD.md` and `docs/MILESTONES.md` from the chosen concept
   (formats are in the agent's instructions). M1 = core verb in a greybox. Mark one milestone
   `(vertical slice)`.
2. `creative-director` agent: write `docs/STYLE_BIBLE.md`:
   - Palette: hex values with roles (base, accent, light, shadow, UI)
   - Materials: which surfaces are reflective, matte, emissive; roughness ranges
   - Shapes and silhouettes; what the camera should always be able to read
   - Lighting and post: environment, fog, glow, depth of field
   - **Prompt prefix**: one line every asset job starts with, e.g. `"low-poly chrome toy, soft studio light, #1B1F3B #E8C547 palette"`
   - Never list: things generated assets must not include
3. Cross-check: every asset in the GDD asset list has a type, a name and a prompt; every milestone
   task has acceptance criteria a smoke test can check.
4. Update `docs/STUDIO_STATE.md` (`stage: build`, `current_milestone: M1`) and commit.
