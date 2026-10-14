#!/usr/bin/env python3
"""Render, check and export a piece. Run it with the venv python (scripts/install-blender.sh makes it).

  .tools/venv/bin/python studio/run.py <piece> --mode check      ~10 s: builds the scene, one tiny frame, QA
  .tools/venv/bin/python studio/run.py <piece> --mode preview    contact sheet (look at it!), loop-seam check, model exports
  .tools/venv/bin/python studio/run.py <piece> --mode final      full-quality video / turntable + exports  (use a GPU: --device gpu)

<piece> is a name in pieces/ or a path. Output goes to output/<piece>/<mode>/ unless --out is given.
Exit code 1 means a FAIL in report.json; WARNs don't fail the run.
"""

import argparse
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import bpy  # noqa: E402  (must come first: it registers bmesh and mathutils)
import bmesh  # noqa: E402
from mathutils import Matrix  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import kit  # noqa: E402
import post  # noqa: E402
import qa  # noqa: E402

META_DEFAULTS = {"kind": "motion", "size": (1080, 1080), "fps": 24, "seconds": 4, "alpha": False, "samples": 128,
                 "turntable_seconds": 5, "hero_t": 0.0, "formats": ["glb", "stl", "obj"]}
PREVIEW_LONGEST = 540
CHECK_LONGEST = 160


def load_piece(ref):
    path = Path(ref)
    if not path.suffix:
        path = ROOT / "pieces" / f"{ref}.py"
    if not path.exists():
        sys.exit(f"piece not found: {path}")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "META") or not hasattr(module, "build"):
        sys.exit(f"{path.name} must define META and build(ctx)")
    return path.stem, module


def scaled(size, longest):
    w, h = size
    k = longest / max(w, h)
    if k >= 1:
        return (w, h)
    return (max(16, round(w * k / 2) * 2), max(16, round(h * k / 2) * 2))


def log(msg):
    print(f"[run] {msg}", flush=True)


# ------------------------------------------------------------------ posing and rendering


def pose(ctx, piece, t):
    if hasattr(piece, "animate"):
        piece.animate(ctx, t)
    elif ctx.meta["kind"] == "model":
        ctx.pivot.rotation_euler[2] = 2 * math.pi * t   # default turntable


def render(ctx, piece, t, path, seed=0):
    pose(ctx, piece, t)
    ctx.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    post.apply(path, ctx.meta.get("post", {}), seed=seed)


def contact_sheet(paths, cols, out, alpha=False):
    imgs = [Image.open(p).convert("RGBA") for p in paths]
    w, h = imgs[0].size
    rows = math.ceil(len(imgs) / cols)
    sheet = Image.new("RGB", (cols * w, rows * h), (14, 14, 14))
    draw = ImageDraw.Draw(sheet)
    for i, im in enumerate(imgs):
        if alpha:  # show transparency on a checkerboard
            checker = Image.new("RGBA", (w, h), (70, 70, 70, 255))
            cd = ImageDraw.Draw(checker)
            for y in range(0, h, 16):
                for x in range((y // 16) % 2 * 16, w, 32):
                    cd.rectangle((x, y, x + 15, y + 15), fill=(110, 110, 110, 255))
            im = Image.alpha_composite(checker, im)
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(im.convert("RGB"), (x, y))
        draw.text((x + 6, y + 4), f"{i + 1}/{len(imgs)}", fill=(255, 255, 255))
    sheet.save(out)


# ------------------------------------------------------------------ encoding


def ffmpeg(*args):
    res = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *map(str, args)], capture_output=True, text=True)
    if res.returncode:
        raise RuntimeError(f"ffmpeg failed: {res.stderr.strip()[:400]}")


def encode(frames_dir, fps, out_dir, name, alpha):
    src = ["-framerate", fps, "-i", frames_dir / "f_%04d.png"]
    files = {}
    ffmpeg(*src, "-c:v", "libx264", "-preset", "slow", "-crf", 14, "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_dir / f"{name}.mp4")
    files["mp4"] = out_dir / f"{name}.mp4"
    ffmpeg(*src, "-vf", "fps=15,scale='min(360,iw)':-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
           "-loop", 0, out_dir / f"{name}.gif")
    files["gif"] = out_dir / f"{name}.gif"
    if alpha:
        ffmpeg(*src, "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", 0, "-crf", 18, "-auto-alt-ref", 0, out_dir / f"{name}_alpha.webm")
        ffmpeg(*src, "-c:v", "prores_ks", "-profile:v", 4444, "-pix_fmt", "yuva444p10le", out_dir / f"{name}_alpha.mov")
        files["webm"], files["mov"] = out_dir / f"{name}_alpha.webm", out_dir / f"{name}_alpha.mov"
    return files


# ------------------------------------------------------------------ model export


def export_model(ctx, out_dir, name, formats):
    ctx.pivot.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bm, mats = bmesh.new(), []
    for ob in ctx.model_objects:
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
        me.transform(ob.matrix_world)
        start = len(bm.faces)
        bm.from_mesh(me)
        remap = {}
        for i, m in enumerate(me.materials):
            if m is not None:
                if m not in mats:
                    mats.append(m)
                remap[i] = mats.index(m)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[start:]:
            f.material_index = remap.get(f.material_index, 0)
        bpy.data.meshes.remove(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])

    def temp_object(scale):
        b = bm.copy()
        b.transform(Matrix.Scale(scale, 4))
        mesh = bpy.data.meshes.new(name)
        b.to_mesh(mesh)
        b.free()
        for m in mats:
            mesh.materials.append(m)
        ob = bpy.data.objects.new(name, mesh)
        kit.link(ob)
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        return ob

    def drop(ob):
        mesh = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(mesh)

    unit = ctx.meta.get("unit", "")
    files = {}
    for fmt in formats:
        path = out_dir / f"{name}.{fmt}"
        scale = 0.001 if (fmt == "glb" and unit == "mm") else 1.0   # glTF is meters by spec; STL/OBJ keep mm
        ob = temp_object(scale)
        if fmt == "glb":
            bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True)
        elif fmt == "stl":
            bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True, ascii_format=False)
        elif fmt == "obj":
            bpy.ops.wm.obj_export(filepath=str(path), export_selected_objects=True)
        else:
            raise ValueError(f"unknown format {fmt}")
        drop(ob)
        files[fmt] = path
    expected = sum(len(f.verts) - 2 for f in bm.faces)
    bm.free()
    return files, expected


# ------------------------------------------------------------------ main


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("piece")
    ap.add_argument("--mode", choices=["check", "preview", "final"], default="preview")
    ap.add_argument("--out", help="output directory (default output/<piece>/<mode>)")
    ap.add_argument("--device", choices=["cpu", "gpu"], default="cpu")
    ap.add_argument("--samples", type=int, help="override Cycles samples")
    ap.add_argument("--size", help="override output size WxH (final mode)")
    ap.add_argument("--quick", action="store_true", help="preview: render only the first frame (fast look iteration, no loop check)")
    args = ap.parse_args()

    name, piece = load_piece(args.piece)
    meta = {**META_DEFAULTS, **piece.META}
    meta["size"] = tuple(meta["size"])
    if args.size:
        meta["size"] = tuple(int(x) for x in args.size.lower().split("x"))
    kind, fps = meta["kind"], int(meta["fps"])
    out = Path(args.out) if args.out else ROOT / "output" / name / args.mode
    out = out if out.is_absolute() else ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    if args.mode == "check":
        size, samples = scaled(meta["size"], CHECK_LONGEST), 6
    elif args.mode == "preview":
        size, samples = scaled(meta["size"], PREVIEW_LONGEST), min(int(meta["samples"]), 32)
    else:
        size, samples = meta["size"], int(meta["samples"])
    samples = args.samples or samples
    seconds = meta["turntable_seconds"] if kind == "model" else meta["seconds"]
    frames = max(2, round(seconds * fps))

    started = time.time()
    ctx = kit.new_context(meta, args.mode, size, frames, samples, args.device)
    piece.build(ctx)
    if ctx.camera is None:
        sys.exit(f"{name}: build(ctx) must create a camera with kit.camera(ctx, ...)")
    log(f"{name}: built in {time.time() - started:.1f}s ({kind}, {size[0]}x{size[1]}, {samples} samples, {frames} frames/loop, {args.device})")

    issues, report = [], {"piece": name, "mode": args.mode, "kind": kind, "size": list(size), "frames": frames, "files": {}}
    expect_alpha = bool(meta["alpha"])
    work = out / "frames"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()

    # ---- model: QA the geometry and write the exports
    if kind == "model":
        ctx.pivot.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        mesh_issues, summary = qa.mesh_checks(ctx.model_objects, bpy.context.evaluated_depsgraph_get(), meta)
        issues += mesh_issues
        report["mesh"] = summary
        export_dir = out if args.mode != "check" else Path(tempfile.mkdtemp())
        files, expected = export_model(ctx, export_dir, name, meta["formats"])
        issues += qa.export_checks(files, expected)
        if args.mode != "check":
            report["files"].update({k: str(v) for k, v in files.items()})
        log(f"mesh: {summary['tris']:,} tris, {summary['size']} {summary['unit']}; exports {', '.join(files)}")

    # ---- renders
    t0 = time.time()
    if args.mode == "check":
        path = work / "check.png"
        render(ctx, piece, meta["hero_t"], path)
        issues += qa.frame_checks(path, expect_alpha)
        report["files"]["frame"] = str(path)

    elif args.mode == "preview":
        count = 8 if kind == "model" else 6
        if args.quick:
            count = 1
        paths = []
        for i in range(count):
            p = work / f"p_{i + 1}.png"
            render(ctx, piece, i / count + (meta["hero_t"] if kind == "model" else 0), p, seed=i)
            paths.append(p)
        sheet = out / "contact_sheet.png"
        contact_sheet(paths, 1 if args.quick else 4 if kind == "model" else 3, sheet, alpha=expect_alpha)
        report["files"]["contact_sheet"] = str(sheet)
        for p in paths:
            issues += [{**i, "detail": f"{p.name}: {i['detail']}"} for i in qa.frame_checks(p, expect_alpha)]
        if kind == "motion" and not args.quick:
            step = work / "seam_step.png"
            seam = work / "seam_loop.png"
            render(ctx, piece, 1 / frames, step, seed=1)
            render(ctx, piece, 1.0, seam, seed=0)      # same grain seed as frame 1: identical if the loop is seamless
            loop_issues, stats = qa.loop_check(paths[0], step, seam)
            issues += loop_issues
            report["loop"] = stats
        log(f"rendered preview in {time.time() - t0:.0f}s")

    else:
        fdir = work
        seconds_per = None
        for i in range(frames):
            render(ctx, piece, i / frames, fdir / f"f_{i + 1:04d}.png", seed=i)
            if i == 0:
                seconds_per = time.time() - t0
            if i % 8 == 0 or i == frames - 1:
                log(f"frame {i + 1}/{frames}  ({(time.time() - t0) / (i + 1):.1f}s each)")
        issues += qa.frame_checks(fdir / "f_0001.png", expect_alpha)
        issues += qa.frame_checks(fdir / f"f_{frames // 2:04d}.png", expect_alpha)
        if kind == "motion":
            step, seam = fdir / "seam_step.png", fdir / "seam_loop.png"
            render(ctx, piece, 1 / frames, step, seed=1)
            render(ctx, piece, 1.0, seam, seed=0)
            loop_issues, stats = qa.loop_check(fdir / "f_0001.png", step, seam)
            issues += loop_issues
            report["loop"] = stats
        files = encode(fdir, fps, out, name, expect_alpha)
        issues += qa.video_checks(files["mp4"], size[0] // 2 * 2, size[1] // 2 * 2, fps, frames)
        report["files"].update({k: str(v) for k, v in files.items()})
        hero = out / "hero.png"
        shutil.copy(fdir / f"f_{max(1, int(frames * meta['hero_t'])) :04d}.png", hero)
        report["files"]["hero"] = str(hero)
        if not (out / "keep_frames").exists():
            shutil.rmtree(fdir)

    # ---- report
    fails = [i for i in issues if i["level"] == "FAIL"]
    report["issues"] = issues
    report["status"] = "FAIL" if fails else "OK"
    report["seconds"] = round(time.time() - started, 1)
    (out / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    for i in issues:
        print(f"  {i['level']}  {i['check']}: {i['detail']}")
    for k, v in report["files"].items():
        print(f"  file  {k}: {v}")
    print(f"[run] {name} {args.mode}: {report['status']} in {report['seconds']}s")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
