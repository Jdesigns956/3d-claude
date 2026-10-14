# Craft notes

What the first two pieces taught us. Read before writing a piece; add to it when a new lesson costs you a render.

## Chrome

- **Chrome is a mirror. It looks like chrome only if the thing it reflects has contrast.** A bright, even environment
  turns it white or cream (our first try). A dark one turns it black. What reads as liquid metal is a mostly dark dome
  with 2-4 crisp bright bands and a couple of softbox rectangles. `kit.dome([...])` builds that; the stops in
  `pieces/chrome_mandala_loop.py` are a good starting point.
- **The palette reaches chrome through its reflections.** Warm bands (butter, gold) make the metal read as brass. For
  silver, keep the bands bone-white and cool-tinted (`#E4EAF0`) and let warm color live in the backdrop, enamels and
  one thin accent band. That split is also what gives the strong contrast against the background.
- Plump, inflated shapes (`kit.petal`, `kit.pearl`) catch more bands than sharp ones. Sharp pointed petals read as
  throwing stars, not soft Y2K chrome.
- Pair chrome with a non-metal (`kit.enamel`) so the eye has something to rest on.

## Loops (motion pieces)

A piece's `animate(ctx, t)` gets `t` in [0, 1). The runner renders `t = 1.0` as a seam frame and compares it to
frame 1. **Every animated value must be periodic.** Rules that keep it true:

- Radial rings turn a **whole number of petal pitches** per loop (`2π/count × n`).
- If petals alternate materials, use an **even** number of pitches, or the colors swap at the seam.
- **Nesting adds up.** A child on a rotating parent inherits the parent's turn. The child's *world* turn
  (parent + its own spin) must be a multiple of the child's own repeat. The mandala's rosettes do this: they sit on a
  ring that turns 45 degrees and need a multiple of 120, so their local spin is `240 - 45`.
- Use `kit.loop_sin(t, cycles, phase)` for bobbing and breathing; never `t * something` without a whole-turn multiple.
- Don't use randomness in `animate`.

The seam check (`loop` in the report) failing means one of these is broken. Find it by comparing object transforms at
`t=0` and `t=1`.

## Depth and look

- Selective blur is the camera's `fstop` (1.2-2.8 for a strong effect) plus layers at different distances. Focus on
  the hero layer. A far emissive backdrop (`kit.radial_backdrop`) blurs into a soft glow.
- Bloom, chromatic aberration, vignette and grain are `META["post"]`, applied per frame in `studio/post.py`. Grain is
  seeded per frame index so loops still match. Transparent pieces skip bloom and vignette.
- AgX tone mapping (default) desaturates hot highlights. If a color keeps washing to white, lower the light or
  exposure first, then try `META["tonemap"] = "Khronos PBR Neutral"`.
- Every design gets its own palette identity, declared in `META["palette"]` with roles. Four or five hex values, one of
  them a neutral. Don't default to magenta/cyan/purple.

## Formats

- `--size WxH` renders any aspect ratio. The camera fits the lens to the *short* side, so a subject framed for a
  square also fits 9:16 (room above and below for text) and 16:9. Check the contact sheet at the target size.
- Transparent output: `META["alpha"] = True`. Final mode then also writes `_alpha.webm` (VP9) and `_alpha.mov`
  (ProRes 4444). Keep a sharp edge: no baked glow, no soft shadows on the background.
- Loops are encoded without a repeated last frame, so playing them on repeat is seamless.

## Cost

CPU (4 cores): about 8 s per 540 px frame at 32 samples. A 1080 px, 96-sample frame is roughly 12x that, so
**finals go to the GPU worker** (`enqueue render <piece>`). Iterate on `--mode preview` and `--mode preview --quick`
(one frame, about 10 s). `--mode check` takes about 2 s and is what the hooks run.

## Models

- Model pieces set `META["unit"] = "mm"`, `printable=True` for anything that will be 3D printed. STL and OBJ export in
  mm; GLB is converted to meters (the glTF spec).
- `ctx.model_objects` is what gets QA'd and exported; parent objects to `ctx.pivot` (the turntable spins it).
- One material per mesh datablock. Objects that share a mesh share its material.
- Overlapping closed shells pass the watertight check and slice fine (slicers union them), but they are not one
  boolean-merged solid. If someone needs a single solid (CNC, some resin workflows), merge it explicitly and say so.
- Watch the triangle budget (`max_tris`). Dense lathe meshes add up fast: 160k triangles for the medallion.

## Not covered yet

- **Typography.** No text helper in `kit.py`; Blender's default font is poor. Needs a font file in `assets/fonts/` and a
  `kit.text()` built and tested on a real piece.
- Rigged characters, cloth and fluid simulation, anything needing the EEVEE realtime engine (needs a GPU display; the
  headless build uses Cycles only).
- Judging whether something looks *good*. The checks catch broken; a person or the art-director agent looking at the
  contact sheet catches generic.
