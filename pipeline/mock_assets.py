"""Placeholder asset generators (stdlib only).

The worker's --mock mode uses these so the whole pipeline (enqueue -> generate -> import -> test)
runs on any machine, including a GPU-less cloud session. Every mock asset is recorded in the ledger
as a placeholder, and the ship gate refuses to export a build that still contains one.
"""

import hashlib
import json
import math
import random
import struct
import wave
import zlib
from pathlib import Path


def _rng(seed_text: str) -> random.Random:
    return random.Random(int(hashlib.sha256(seed_text.encode()).hexdigest()[:16], 16))


def write_wav(path: Path, seed_text: str, seconds: float = 4.0, noise: bool = False) -> None:
    """A soft chord (music) or a decaying noise burst (foley)."""
    rate = 22050
    rng = _rng(seed_text)
    root = rng.choice([110.0, 130.81, 146.83, 164.81])
    freqs = [root, root * 1.25, root * 1.5]
    frames = bytearray()
    total = int(seconds * rate)
    for i in range(total):
        t = i / rate
        if noise:
            sample = (rng.random() * 2 - 1) * math.exp(-4 * t / seconds)
        else:
            sample = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
            sample *= min(1.0, t * 4, (seconds - t) * 4)  # fade in/out
        frames += struct.pack("<h", int(sample * 0.4 * 32767))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def write_png(path: Path, width: int, height: int, pixel) -> None:
    """pixel(x, y) -> (r, g, b) bytes 0-255."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter: none
        for x in range(width):
            raw.extend(pixel(x, y))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def write_pbr_set(out_dir: Path, name: str, seed_text: str, size: int = 128) -> list[Path]:
    """Base color, normal, height, roughness and metalness maps (the set CHORD produces)."""
    rng = _rng(seed_text)
    base = [rng.randint(60, 200) for _ in range(3)]
    checker = lambda x, y: ((x // 16) + (y // 16)) % 2  # noqa: E731
    maps = {
        "basecolor": lambda x, y: bytes(max(0, c - 30 * checker(x, y)) for c in base),
        "normal": lambda x, y: bytes((128, 128, 255)),
        "height": lambda x, y: bytes((255 * checker(x, y),) * 3),
        "roughness": lambda x, y: bytes((180,) * 3),
        "metalness": lambda x, y: bytes((0,) * 3),
    }
    paths = []
    for suffix, fn in maps.items():
        p = out_dir / f"{name}_{suffix}.png"
        write_png(p, size, size, fn)
        paths.append(p)
    return paths


def write_glb_cube(path: Path, seed_text: str) -> None:
    """A unit cube as binary glTF, colored from the prompt so placeholders are distinguishable."""
    rng = _rng(seed_text)
    color = [round(rng.uniform(0.2, 0.9), 3) for _ in range(3)] + [1.0]
    positions, normals, indices = [], [], []
    axes = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
    for i in range(3):
        u, v = axes[(i + 1) % 3], axes[(i + 2) % 3]
        for sign in (1, -1):
            n = tuple(sign * a for a in axes[i])
            uu, vv = (u, v) if sign > 0 else (v, u)  # keep counter-clockwise winding seen from outside
            start = len(positions)
            for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                positions.append(tuple(0.5 * (n[k] + su * uu[k] + sv * vv[k]) for k in range(3)))
                normals.append(n)
            indices += [start, start + 1, start + 2, start, start + 2, start + 3]

    pos_bytes = b"".join(struct.pack("<3f", *p) for p in positions)
    nrm_bytes = b"".join(struct.pack("<3f", *n) for n in normals)
    idx_bytes = b"".join(struct.pack("<H", i) for i in indices)
    binary = pos_bytes + nrm_bytes + idx_bytes
    binary += b"\x00" * (-len(binary) % 4)

    gltf = {
        "asset": {"version": "2.0", "generator": "3d-claude mock_assets"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": path.stem}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1}, "indices": 2, "material": 0}]}],
        "materials": [{"pbrMetallicRoughness": {"baseColorFactor": color, "metallicFactor": 0.0, "roughnessFactor": 0.8}}],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_bytes), "byteLength": len(nrm_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_bytes) + len(nrm_bytes), "byteLength": len(idx_bytes), "target": 34963},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(positions), "type": "VEC3",
             "min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5]},
            {"bufferView": 1, "componentType": 5126, "count": len(normals), "type": "VEC3"},
            {"bufferView": 2, "componentType": 5123, "count": len(indices), "type": "SCALAR"},
        ],
    }
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode()
    json_bytes += b" " * (-len(json_bytes) % 4)
    total = 12 + 8 + len(json_bytes) + 8 + len(binary)
    out = struct.pack("<III", 0x46546C67, 2, total)
    out += struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
    out += struct.pack("<II", len(binary), 0x004E4942) + binary
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)


def generate(job: dict, output: Path) -> list[Path]:
    """Make the placeholder for a job. `output` is a file path, or a directory for pbr jobs."""
    seed = job["id"] + job.get("prompt", "")
    kind = job["type"]
    if kind == "music":
        write_wav(output, seed, seconds=4.0)
    elif kind == "foley":
        write_wav(output, seed, seconds=2.0, noise=True)
    elif kind == "mesh":
        write_glb_cube(output, seed)
    elif kind == "pbr":
        return write_pbr_set(output, output.name, seed)
    else:
        raise ValueError(f"no mock generator for job type '{kind}'")
    return [output]
