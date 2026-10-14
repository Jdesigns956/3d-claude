"""Automatic checks, so Claude and CI can tell a broken piece from a good one without a person watching.

Every check returns a list of issues: {"level": "FAIL" | "WARN", "check": str, "detail": str}.
FAIL means don't deliver. WARN means look at it. Visual taste is not checkable here; that is what the
contact sheet is for (Claude can read it as an image and judge it against docs/STYLE_BIBLE.md).
"""

import json
import struct
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


def issue(level, check, detail):
    return {"level": level, "check": check, "detail": detail}


# ------------------------------------------------------------------ images and loops


def load(path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32) / 255.0


def frame_checks(path, expect_alpha=False) -> list:
    a = load(path)
    rgb, alpha = a[..., :3], a[..., 3]
    luma = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    out = []
    if expect_alpha:
        coverage = float((alpha > 0.5).mean())
        if alpha.min() > 0.99:
            out.append(issue("FAIL", "alpha", "transparency was requested but every pixel is opaque"))
        elif coverage < 0.005:
            out.append(issue("FAIL", "alpha", f"subject covers only {coverage:.2%} of the frame"))
        visible = luma[alpha > 0.5]
        if visible.size and visible.std() < 0.01:
            out.append(issue("FAIL", "blank", "the visible subject has no tonal variation"))
    else:
        if luma.std() < 0.01:
            out.append(issue("FAIL", "blank", f"frame is flat (luma std {luma.std():.4f})"))
        if luma.mean() < 0.01:
            out.append(issue("FAIL", "black", "frame is black"))
        if luma.mean() > 0.97:
            out.append(issue("FAIL", "white", "frame is blown out"))
        clipped = float((luma > 0.985).mean())
        if clipped > 0.25:
            out.append(issue("WARN", "clipping", f"{clipped:.0%} of the frame is clipped white; lower exposure or light power"))
    return out


def mean_abs_diff(path_a, path_b) -> float:
    return float(np.abs(load(path_a) - load(path_b)).mean())


def loop_check(first, second, loop_point) -> tuple:
    """first = frame 1, second = frame 2, loop_point = the frame after the last (t=1.0). Returns (issues, stats)."""
    step = mean_abs_diff(first, second)
    seam = mean_abs_diff(first, loop_point)
    stats = {"step_diff": round(step, 5), "seam_diff": round(seam, 5)}
    out = []
    if seam > max(0.002, 0.05 * step):
        out.append(issue("FAIL", "loop", f"not seamless: the loop point differs from frame 1 by {seam:.4f} "
                                         f"(one normal step is {step:.4f}). Make every animated value periodic over t in [0,1)"))
    if step < 0.0004:
        out.append(issue("WARN", "motion", f"almost nothing moves between frames (step diff {step:.5f})"))
    return out, stats


# ------------------------------------------------------------------ video


def probe_video(path) -> dict:
    res = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                          "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames,codec_name,pix_fmt",
                          "-of", "json", str(path)], capture_output=True, text=True)
    return json.loads(res.stdout)["streams"][0]


def video_checks(path, width, height, fps, frames) -> list:
    s = probe_video(path)
    out = []
    if (int(s["width"]), int(s["height"])) != (width, height):
        out.append(issue("FAIL", "dimensions", f"{path.name} is {s['width']}x{s['height']}, expected {width}x{height}"))
    num, den = (int(x) for x in s["r_frame_rate"].split("/"))
    if abs(num / den - fps) > 0.01:
        out.append(issue("FAIL", "fps", f"{path.name} is {num / den:g} fps, expected {fps}"))
    if int(s["nb_read_frames"]) != frames:
        out.append(issue("FAIL", "frames", f"{path.name} has {s['nb_read_frames']} frames, expected {frames}"))
    return out


# ------------------------------------------------------------------ meshes (need bpy)


def mesh_stats(ob, depsgraph) -> dict:
    import bmesh
    import bpy

    ev = ob.evaluated_get(depsgraph)
    me = bpy.data.meshes.new_from_object(ev, depsgraph=depsgraph)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(ob.matrix_world)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    tris = sum(len(f.verts) - 2 for f in bm.faces)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    nonmanifold = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    loose_verts = sum(1 for v in bm.verts if not v.link_edges)
    degenerate = sum(1 for f in bm.faces if f.calc_area() < 1e-10)

    volume = 0.0
    for f in bm.faces:
        v = [x.co for x in f.verts]
        for i in range(1, len(v) - 1):
            volume += v[0].dot(v[i].cross(v[i + 1])) / 6.0

    coords = [v.co for v in bm.verts] or [(0, 0, 0)]
    lo = [min(c[i] for c in coords) for i in range(3)]
    hi = [max(c[i] for c in coords) for i in range(3)]
    has_uv = bool(me.uv_layers)
    bm.free()
    bpy.data.meshes.remove(me)
    return {"name": ob.name, "tris": tris, "open_edges": boundary, "nonmanifold_edges": nonmanifold, "loose_verts": loose_verts,
            "degenerate_faces": degenerate, "signed_volume": volume, "bbox_min": lo, "bbox_max": hi,
            "size": [h - l for h, l in zip(hi, lo)], "uv": has_uv}


def mesh_checks(objects, depsgraph, meta) -> tuple:
    stats = [mesh_stats(o, depsgraph) for o in objects]
    out = []
    printable = bool(meta.get("printable"))
    max_tris = int(meta.get("max_tris", 250_000))
    total = sum(s["tris"] for s in stats)
    if not stats:
        return [issue("FAIL", "empty", "the piece registered no model objects (append them to ctx.model_objects)")], stats
    if total > max_tris:
        out.append(issue("FAIL", "tri_budget", f"{total:,} triangles exceeds the {max_tris:,} budget (META max_tris)"))
    for s in stats:
        if s["open_edges"] or s["nonmanifold_edges"]:
            out.append(issue("FAIL" if printable else "WARN", "watertight",
                             f"{s['name']}: {s['open_edges']} open and {s['nonmanifold_edges']} non-manifold edges"
                             + ("" if printable else " (fine for display, not for printing; set META printable=True to enforce)")))
        elif s["signed_volume"] < 0:
            out.append(issue("FAIL", "normals", f"{s['name']}: inside-out (negative volume); flip its normals"))
        if s["loose_verts"]:
            out.append(issue("WARN", "loose", f"{s['name']}: {s['loose_verts']} loose vertices"))
        if s["degenerate_faces"]:
            out.append(issue("WARN", "degenerate", f"{s['name']}: {s['degenerate_faces']} zero-area faces"))
    lo = [min(s["bbox_min"][i] for s in stats) for i in range(3)]
    hi = [max(s["bbox_max"][i] for s in stats) for i in range(3)]
    unit = meta.get("unit", "")
    size = [h - l for h, l in zip(hi, lo)]
    if printable and unit == "mm" and max(size) > 250:
        out.append(issue("WARN", "size", f"{max(size):.0f} mm on the longest side is bigger than most print beds"))
    summary = {"tris": total, "objects": len(stats), "size": [round(x, 3) for x in size], "unit": unit or "units", "per_object": stats}
    return out, summary


# ------------------------------------------------------------------ exported files


def glb_triangles(path) -> int:
    data = Path(path).read_bytes()
    magic, _version, _length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError("not a GLB file")
    json_len, _kind = struct.unpack_from("<II", data, 12)
    doc = json.loads(data[20:20 + json_len])
    tris = 0
    for mesh in doc.get("meshes", []):
        for prim in mesh["primitives"]:
            if "indices" in prim:
                tris += doc["accessors"][prim["indices"]]["count"] // 3
            else:
                tris += doc["accessors"][prim["attributes"]["POSITION"]]["count"] // 3
    return tris


def stl_triangles(path) -> int:
    data = Path(path).read_bytes()
    return struct.unpack_from("<I", data, 80)[0]


def export_checks(files: dict, expected_tris: int) -> list:
    out = []
    for kind, path in files.items():
        if not path.exists() or path.stat().st_size < 100:
            out.append(issue("FAIL", "export", f"{kind} export is missing or empty: {path.name}"))
            continue
        try:
            n = glb_triangles(path) if kind == "glb" else stl_triangles(path) if kind == "stl" else None
        except Exception as exc:  # corrupted file
            out.append(issue("FAIL", "export", f"{path.name} won't parse: {exc}"))
            continue
        if n is not None and abs(n - expected_tris) > max(2, expected_tris * 0.01):
            out.append(issue("FAIL", "export", f"{path.name} has {n:,} triangles but the scene has {expected_tris:,}"))
    return out
