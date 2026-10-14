---
name: deliver
description: "Make the final files. Renders at full quality (queues a GPU render job, or renders small on the CPU), adds sound, builds every format, runs the license gate, and stops for the human to approve. Use for \"/deliver\", \"render the final\", or the studio deliver stage."
---

# Deliver

Piece: $ARGUMENTS (default: `piece` in `docs/STUDIO_STATE.md`)

1. **Formats**: list what the brief promises (sizes, transparent version, STL, GLB). One render job per size, each in its
   own folder: `enqueue render <piece>` (default size), `enqueue render <piece>_story --piece <piece> --param size=1080x1920`.
   Check each size's framing first with `--mode preview --quick --size WxH`.
2. **Where it renders**:
   - GPU worker available (the human runs `python3 pipeline/assets.py work --watch` on a GPU machine): queue the
     render job, commit and push, and tell the human the job is waiting. Move on to sound while it runs.
   - No worker: estimate the cost first (`seconds per preview frame x frames x (final pixels / preview pixels) x (final samples / 32)`).
     If it's under about 20 minutes, render it here with `studio/run.py <piece> --mode final --out deliverables/<piece>`; otherwise
     render a reduced size or a preview-quality version here, label it so, and queue the GPU job for the real one.
3. **Sound** (motion): the `sound-designer` queues music and, if wanted, foley, then muxes the approved audio into the video.
4. **License gate**: `python3 pipeline/assets.py gate --ship`. Placeholders and non-commercial assets block a release. List
   each with what replaces it, and stop if blocked.
5. `qa-reviewer` checks the actual files in `deliverables/<piece>/` (ffprobe, hero, formats).
6. Write `deliverables/<piece>/README.md`: every file with size, duration, fps and what it's for, and a clear line for each
   saying **production-ready** or **concept/preview only** (and why). Credit AI models and their licenses from `pipeline/ledger.json`.
7. Update `docs/STUDIO_STATE.md`, commit.

**Gate C**: report the files and the gate result. Posting, uploading or selling is the human's call, even in auto mode.
