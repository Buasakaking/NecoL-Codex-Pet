"""Validate the stock-compatible portable NecoL atlas and installed package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


CELL_W, CELL_H = 192, 208
USED = [6, 8, 8, 4, 5, 8, 6, 6, 6]


def alpha_count(image: Image.Image) -> int:
    return sum(image.getchannel("A").histogram()[1:])


def residue_count(image: Image.Image) -> int:
    pixels = image.convert("RGBA").getdata()
    return sum(1 for red, green, blue, alpha in pixels if alpha == 0 and (red or green or blue))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("atlas")
    parser.add_argument("--json-out")
    args = parser.parse_args()
    path = Path(args.atlas).resolve()
    with Image.open(path) as opened:
        image = opened.convert("RGBA")
        fmt = opened.format
        mode = opened.mode
    errors: list[str] = []
    if image.size != (1536, 1872):
        errors.append(f"expected 1536x1872, got {image.size}")
    if fmt not in {"PNG", "WEBP"} or "A" not in mode:
        errors.append(f"expected alpha-capable PNG/WebP, got {fmt} {mode}")
    for row, count in enumerate(USED):
        for column in range(8):
            cell = image.crop((column * CELL_W, row * CELL_H, (column + 1) * CELL_W, (row + 1) * CELL_H))
            pixels = alpha_count(cell)
            if column < count and pixels < 50:
                errors.append(f"row {row} cell {column} is empty")
            if column >= count and pixels:
                errors.append(f"row {row} cell {column} must be transparent")
    residue = residue_count(image)
    if residue:
        errors.append(f"transparent RGB residue: {residue}")
    result = {
        "ok": not errors,
        "file": str(path),
        "format": fmt,
        "mode": mode,
        "width": image.width,
        "height": image.height,
        "portable_stock_contract": True,
        "transparent_rgb_residue_pixels": residue,
        "errors": errors,
    }
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
