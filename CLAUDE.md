# 3D Claude: motion graphics and 3D model studio

Claude Code agents make motion graphics (loops, VJ visuals, social clips) and 3D models (display, print, merch) as
Blender Python pieces, render them headless, check them, and hand over files. A GPU worker is optional.
Flow: `/studio <brief>` (see `.claude/skills/studio/SKILL.md`). State: `docs/STUDIO_STATE.md`.

## Layout
- `pieces/`: one Python file per piece (scene description). Working examples: `chrome_mandala_loop.py` (motion), `mandala_medallion.py` (model).
- `studio/`: `kit.py` (helpers), `run.py` (render, post, QA, export), `qa.py`, `post.py`, `sheet.py` (concept sheets).
- `pipeline/`: asset and render job queue for the GPU worker, license ledger (`pipeline/ledger.json`).
- `docs/`: `KIT.md` (piece contract + API), `CRAFT.md` (lessons: read first), `TASTE.md` (house taste), `briefs/`, `PIPELINE.md`.
- `showcase/`: small committed samples. `deliverables/`: final files per piece. `output/`: scratch renders (gitignored).
- `assets/generated/`: written only by `pipeline/assets.py`. `assets/concept/`: reference images from the human.

## Commands (use the venv python: `.tools/venv/bin/python`, made by `scripts/install-blender.sh`)
- `scripts/check.sh`: compile, pipeline tests, every piece builds and renders a QA-clean tiny frame. Must print `check.sh: OK` before committing changes under `studio/`, `pieces/`, `pipeline/`.
- `studio/run.py <piece> --mode check|preview|final [--quick] [--size WxH] [--device gpu]`: see `docs/KIT.md`.
- `python3 pipeline/assets.py enqueue|status|placeholders|gate`: jobs for the GPU worker (`-h` for details).
- `python3 -m unittest discover -s pipeline/tests`: pipeline tests.

## Rules
- **Look at your renders.** Open `output/<piece>/preview/contact_sheet.png` (you can read images) and judge palette, contrast,
  focal point and depth before showing anything. The QA checks only catch broken, not generic.
- Edit pieces with Edit/Write, not sed or heredocs: the post-edit hook builds the piece and renders a tiny frame on every save.
- Motion loops: every animated value is periodic over t in [0,1) (rules in `docs/CRAFT.md`). The seam check must pass.
- Don't run `--mode final` on the CPU for more than a few seconds of 540 px footage; queue a `render` job.
- Each design gets its own palette identity (`docs/TASTE.md`). Say plainly which deliverables are production-ready and which are previews.
- Don't edit `.tools/`, `output/`, or `pipeline/ledger.json` by hand. Never upload or publish anything; releasing is the human's call.
