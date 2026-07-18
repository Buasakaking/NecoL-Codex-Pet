"""Regression check for NecoL's former transparent torso bands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


CELL_W, CELL_H = 192, 208
ROWS = {
    0: ("idle", 6),
    3: ("greeting-idle", 4),
    4: ("hover-idle", 5),
    6: ("chips-waiting", 6),
    7: ("chips-running", 6),
}


def longest_internal_empty_band(alpha: np.ndarray) -> tuple[int, int] | None:
    """Find a transparent horizontal core band bracketed by sprite pixels."""
    core = alpha[:, 70:122] > 0
    occupied = core.any(axis=1)
    ys = np.flatnonzero(occupied)
    if ys.size < 2:
        return None
    top, bottom = int(ys[0]), int(ys[-1])
    best: tuple[int, int] | None = None
    start: int | None = None
    for y in range(top, bottom + 2):
        empty = y <= bottom and not occupied[y]
        if empty and start is None:
            start = y
        elif not empty and start is not None:
            if y - start >= 4 and occupied[:start].any() and occupied[y:].any():
                if best is None or y - start > best[1] - best[0]:
                    best = (start, y)
            start = None
    return best


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("atlas")
    parser.add_argument("--json-out")
    args = parser.parse_args()

    path = Path(args.atlas).resolve()
    atlas = Image.open(path).convert("RGBA")
    errors: list[str] = []
    checked: list[dict[str, object]] = []
    for row, (name, count) in ROWS.items():
        for column in range(count):
            cell = atlas.crop(
                (column * CELL_W, row * CELL_H, (column + 1) * CELL_W, (row + 1) * CELL_H)
            )
            alpha = np.asarray(cell.getchannel("A"))
            band = longest_internal_empty_band(alpha)
            checked.append({"row": row, "state": name, "frame": column + 1, "empty_band": band})
            if band is not None:
                errors.append(f"{name} frame {column + 1} has internal transparent band y={band[0]}..{band[1] - 1}")

    result = {"ok": not errors, "atlas": str(path), "checked": checked, "errors": errors}
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
