# Piece contract and kit reference

A piece is one Python file in `pieces/`. It describes the scene; `studio/run.py` renders, post-processes, checks and
exports it. Run files with `.tools/venv/bin/python` (made by `scripts/install-blender.sh`).

```python
import kit

META = dict(
    kind="motion",                  # "motion" or "model"
    size=(1080, 1080), fps=24, seconds=4, samples=96,
    palette={"ink": "#0D0806", ...},  # 4-5 hex values; ctx.hex[name] -> '#hex', ctx.palette[name] -> linear RGBA
    post=dict(bloom=0.5, aberration=1.2, vignette=0.3, grain=0.02),   # see studio/post.py
    alpha=False,                    # True: transparent background + alpha video exports
    exposure=0.0, tonemap="AgX",
    # model only: unit="mm", printable=True, max_tris=250_000, formats=["glb","stl","obj"], turntable_seconds=5, hero_t=0.07
)

def build(ctx): ...                 # make the scene; must create a camera with kit.camera(ctx, ...)
def animate(ctx, t): ...            # optional, t in [0,1). Motion pieces: every value periodic. Models default to a turntable.
```

Module-level state is fine (`RINGS = []`), because each run is a fresh process.

## Run

```
python studio/run.py <piece> --mode check      # ~2 s: build, one tiny frame, QA
python studio/run.py <piece> --mode preview    # contact sheet (look at it), loop seam check, model exports
python studio/run.py <piece> --mode preview --quick   # one frame only: fast look iteration
python studio/run.py <piece> --mode final --device gpu [--size 1080x1920] [--samples 128] [--out dir]
```

Output: `output/<piece>/<mode>/` with `contact_sheet.png`, `report.json`, and for final the video and exports.
Exit code 1 = a FAIL in the report. Read `report.json` `issues` and `loop` / `mesh`.
Harmless noise in the log: `CUEW initialization failed` (no CUDA on a CPU box) and `Draco`/`MeshOptimizer is not available`
(optional glTF compression libraries we don't use).

## kit.py

| | |
|---|---|
| `rgb('#hex')` | linear RGBA for Blender colors |
| `world(color, strength)` | background color the camera sees past everything |
| `dome(stops, radius)` | what chrome reflects: vertical gradient sphere, hidden from the camera. `stops=[(0..1 height, '#hex', strength)]`; close stops make hard bands. Scale `radius` above the camera distance for mm-sized models |
| `radial_backdrop(stops, z, radius)` | emissive disc behind the subject; `0` = rim, `1` = center. Blurs into a glow with a low f-stop |
| `softbox(name, location, size, color, power, aspect=1)` | rectangular light hidden from the camera but visible in reflections. Power scales with distance squared |
| `camera(ctx, location, target, lens, fstop, focus)` | `fstop=None` = all sharp; `focus` = object or point. Fits the short side |
| `chrome(name, tint, roughness)`, `enamel(name, color, roughness)`, `glow(name, color, strength)` | materials |
| `petal(length, width, flatten, sharp, belly)`, `pearl(radius)`, `torus(major, minor)`, `lathe(profile, flatten)` | meshes (shared data, smooth shaded); `lathe` revolves `[(radius, y)...]` around Y |
| `spawn(mesh, material, parent, location, rotation, scale, name, collect)` | an object using the mesh. Reusing one mesh for many objects is cheap |
| `empty(name, parent, location)` | grouping/pivot; rotate these to turn rings |
| `ring_of(count, radius, make, phase, parent)` | radial placement helper |
| `loop_sin(t, cycles, phase)`, `lerp`, `ease` | animation helpers |

Everything else in `bpy` is available too. `kit` only exists so the common moves are one line.

## Checks (`studio/qa.py`)

FAIL blocks delivery, WARN means look. Frames: blank / black / blown out / clipped, alpha present and subject coverage.
Loops: seam difference vs one normal step; almost-static animation. Video: dimensions, fps, frame count. Models:
open and non-manifold edges (FAIL if `printable`), inside-out normals, loose vertices, zero-area faces, triangle budget,
size in mm; exports re-read for triangle count.
