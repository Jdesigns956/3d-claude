# Showcase

What the two sample pieces render to. Both were made by the studio's own loop (write, render, look, revise).

| Folder | Files | Status |
|---|---|---|
| `chrome_mandala_loop/` | `chrome_mandala_loop.mp4` (540x540, 24 fps, 4.000 s, 96 frames), `.gif` (360 px, 15 fps), `hero.png` | **Preview quality.** Rendered on 4 CPU cores in 17.5 min at 32 samples, so there is visible grain. The loop closes (seam difference 0.00018 vs 0.0238 for a normal frame step). For a 1080 px, 96-sample final, run `enqueue render chrome_mandala_loop` on a GPU worker. |
| `mandala_medallion/` | `mandala_medallion.stl` (mm), `.glb` (meters), `contact_sheet.png`, `report.json` | **Print-ready geometry, preview render.** 44.2 x 50.0 x 11.4 mm, 160,592 triangles, every shell closed (checked), layers overlap on purpose (slicers union them). The sheet is a 540 px CPU render. Not yet test-printed. |

Regenerate: `.tools/venv/bin/python studio/run.py <piece> --mode final --out showcase/<piece>` (motion) or `--mode preview` (model).
