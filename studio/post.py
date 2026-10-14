"""Frame post-processing: the Y2K / weirdcore finish (bloom, chromatic aberration, vignette, grain).

Runs on each rendered PNG in place. Deterministic: grain is seeded by `seed`, so a loop's last frame
(seed 0 again) matches its first frame exactly. Transparent pieces skip bloom and vignette, because
glow baked into an alpha cut-out leaves halos on whatever it's composited over.
"""

import numpy as np
from PIL import Image, ImageFilter

DEFAULTS = {"bloom": 0.35, "bloom_threshold": 0.72, "bloom_radius": 0.012, "aberration": 0.0, "vignette": 0.2, "grain": 0.025}


def apply(path, settings: dict, seed: int = 0) -> None:
    cfg = {**DEFAULTS, **(settings or {})}
    img = Image.open(path)
    has_alpha = img.mode == "RGBA"
    alpha = img.getchannel("A") if has_alpha else None
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    h, w, _ = rgb.shape

    if cfg["aberration"] and not has_alpha:
        shift = max(1, round(cfg["aberration"] * w / 1000))
        rgb[..., 0] = np.roll(rgb[..., 0], shift, axis=1)
        rgb[..., 2] = np.roll(rgb[..., 2], -shift, axis=1)

    if cfg["bloom"] and not has_alpha:
        luma = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        mask = np.clip((luma - cfg["bloom_threshold"]) / (1 - cfg["bloom_threshold"]), 0, 1)[..., None]
        bright = Image.fromarray((rgb * mask * 255).astype(np.uint8))
        radius = max(2.0, cfg["bloom_radius"] * w)
        glow = (np.asarray(bright.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) * 0.6
                + np.asarray(bright.filter(ImageFilter.GaussianBlur(radius * 3.5)), dtype=np.float32) * 0.4) / 255.0
        rgb = 1 - (1 - rgb) * (1 - np.clip(glow * cfg["bloom"] * 2.2, 0, 1))  # screen blend

    if cfg["vignette"] and not has_alpha:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / 1.4142
        rgb *= (1 - cfg["vignette"] * np.clip(d, 0, 1) ** 2.2)[..., None]

    if cfg["grain"]:
        rng = np.random.default_rng(seed)
        luma_noise = rng.normal(0, cfg["grain"], size=(h, w, 1)).astype(np.float32)
        rgb = rgb + luma_noise * (1 - np.abs(rgb - 0.5) * 1.2)  # less grain in pure blacks and whites

    out = Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8))
    if has_alpha:
        out.putalpha(alpha)
    out.save(path)
