---
name: review
description: "Technical QA of a built piece before delivery: checks, report, real files, formats, loops, asset licenses. Use for \"/review\" or the studio review stage."
---

# Review

Run the `qa-reviewer` agent on the current piece (see its instructions). Expect PASS or BLOCKED with a short fix list.
BLOCKED: send each item to the agent that owns it (`motion-designer`, `modeler`, `sound-designer`), then review again.
PASS: update `docs/STUDIO_STATE.md` and move to `deliver`. Don't soften a FAIL because the picture looks good.
