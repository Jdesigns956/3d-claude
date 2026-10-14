#!/usr/bin/env python3
"""Tile images into one labeled sheet: concept directions side by side, before/after, format variants.

  python3 studio/sheet.py docs/briefs/x/sheet.png a.png b.png c.png --labels "A  chrome lotus" "B  melt grid" "C  glass tunnel"
"""

import argparse
import math

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--labels", nargs="*", default=[])
    ap.add_argument("--cols", type=int, default=0, help="default: all in one row up to 4")
    ap.add_argument("--cell", type=int, default=540, help="height of each cell in px")
    args = ap.parse_args()

    cols = args.cols or min(4, len(args.images))
    imgs = []
    for path in args.images:
        im = Image.open(path).convert("RGB")
        imgs.append(im.resize((round(im.width * args.cell / im.height), args.cell), Image.LANCZOS))
    cell_w = max(im.width for im in imgs)
    pad, label_h = 12, 34
    rows = math.ceil(len(imgs) / cols)
    sheet = Image.new("RGB", (cols * (cell_w + pad) + pad, rows * (args.cell + label_h + pad) + pad), (16, 16, 16))
    draw = ImageDraw.Draw(sheet)
    for i, im in enumerate(imgs):
        x = pad + (i % cols) * (cell_w + pad) + (cell_w - im.width) // 2
        y = pad + (i // cols) * (args.cell + label_h + pad)
        sheet.paste(im, (x, y))
        label = args.labels[i] if i < len(args.labels) else f"{i + 1}"
        draw.text((x, y + args.cell + 10), label, fill=(235, 235, 235))
    sheet.save(args.out)
    print(f"wrote {args.out} ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
