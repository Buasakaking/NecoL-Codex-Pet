"""Build the NecoL Codex pet atlas from the user-supplied animation sheets."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent
OUT = ROOT / "final"
QA = ROOT / "qa"
CELL_W, CELL_H = 192, 208
ATLAS_W, ATLAS_H = CELL_W * 8, CELL_H * 9
ROW_DURATIONS = {
    # Only two unique poses are used: eyes open, then eyes closed.  The
    # remaining four atlas slots repeat the open pose for stock-client
    # compatibility; NecoL's runtime patch loops columns 0 and 1 directly.
    "idle": [1600, 110, 120, 120, 120, 320],
    "running-right": [120, 120, 120, 120, 120, 120, 120, 220],
    "running-left": [120, 120, 120, 120, 120, 120, 120, 220],
    "waving": [280, 110, 140, 320],
    "jumping": [280, 110, 140, 140, 320],
    "failed": [140, 140, 140, 140, 140, 140, 140, 240],
    "waiting": [150, 150, 150, 150, 150, 260],
    "running": [120, 120, 120, 120, 120, 220],
    "review": [280, 110, 140, 140, 140, 320],
}


def split_grid(path: Path, columns: int, rows: int) -> list[Image.Image]:
    """Split a source sheet using proportional bounds (handles non-divisible scans)."""
    image = Image.open(path).convert("RGB")
    frames: list[Image.Image] = []
    for row in range(rows):
        top = round(row * image.height / rows)
        bottom = round((row + 1) * image.height / rows)
        for column in range(columns):
            left = round(column * image.width / columns)
            right = round((column + 1) * image.width / columns)
            frames.append(image.crop((left, top, right, bottom)))
    return frames


def flood_outside(blocker: np.ndarray) -> np.ndarray:
    """Return pixels reachable from a frame edge without crossing line art."""
    height, width = blocker.shape
    outside = np.zeros((height, width), dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    def add(x: int, y: int) -> None:
        if not blocker[y, x] and not outside[y, x]:
            outside[y, x] = True
            queue.append((x, y))

    for x in range(width):
        add(x, 0)
        add(x, height - 1)
    for y in range(height):
        add(0, y)
        add(width - 1, y)

    while queue:
        x, y = queue.popleft()
        if x:
            add(x - 1, y)
        if x + 1 < width:
            add(x + 1, y)
        if y:
            add(x, y - 1)
        if y + 1 < height:
            add(x, y + 1)
    return outside


def remove_checkerboard(frame: Image.Image) -> Image.Image:
    """Remove the baked checkerboard without eating pale enclosed clothing.

    The previous luminance flood treated every connected white/grey pixel as
    background.  NecoL's face, sleeves, and dress use the same luminance, so
    the flood crossed the outline at the cropped lower edge.  Here saturated
    or dark pixels form the reliable foreground line art, a small closing
    seals anti-aliased gaps, and an edge flood fills everything enclosed by
    that art.  This preserves pale fills independent of the desk colour.
    """
    rgb = np.asarray(frame.convert("RGB"))
    value_min = rgb.min(axis=2)
    chroma = rgb.max(axis=2) - value_min
    seeds = (value_min < 222) | (chroma > 8)
    seed_image = Image.fromarray((seeds * 255).astype(np.uint8), "L")
    closed = seed_image.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))
    filled = ~flood_outside(np.asarray(closed) > 0)
    foreground = filled | seeds

    # Opening removes isolated compression speckles but is far smaller than
    # any intended line or effect at the original 362/512px source scale.
    mask = Image.fromarray((foreground * 255).astype(np.uint8), "L")
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    alpha = np.asarray(mask)
    return Image.fromarray(np.dstack((rgb, alpha)), "RGBA")


def remove_neighbour_frame_fragments(frame: Image.Image, *, min_area: int = 16) -> Image.Image:
    """Drop disconnected slivers copied across source-grid boundaries.

    The largest connected component is always the NecoL pose.  Detached
    hearts, stars, roses, and doves are retained when they are wholly inside
    the source cell; non-primary components touching an outer edge are pieces
    of the neighbouring frame and must not enter the atlas.
    """
    alpha = np.asarray(frame.getchannel("A")) > 0
    height, width = alpha.shape
    visited = np.zeros_like(alpha)
    components: list[tuple[int, bool, tuple[int, int, int, int], list[tuple[int, int]]]] = []
    for y in range(height):
        for x in range(width):
            if not alpha[y, x] or visited[y, x]:
                continue
            queue = deque([(x, y)])
            visited[y, x] = True
            pixels: list[tuple[int, int]] = []
            touches_edge = False
            min_x = max_x = x
            min_y = max_y = y
            while queue:
                cx, cy = queue.popleft()
                pixels.append((cx, cy))
                touches_edge |= cx == 0 or cy == 0 or cx == width - 1 or cy == height - 1
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)
                for nx, ny in (
                    (cx - 1, cy - 1), (cx, cy - 1), (cx + 1, cy - 1),
                    (cx - 1, cy),                     (cx + 1, cy),
                    (cx - 1, cy + 1), (cx, cy + 1), (cx + 1, cy + 1),
                ):
                    if 0 <= nx < width and 0 <= ny < height and alpha[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((nx, ny))
            components.append((len(pixels), touches_edge, (min_x, min_y, max_x + 1, max_y + 1), pixels))

    if not components:
        return frame
    primary = max(range(len(components)), key=lambda index: components[index][0])
    keep = np.zeros_like(alpha)
    for index, (area, touches_edge, bbox, pixels) in enumerate(components):
        near_vertical_edge = bbox[0] < 12 or bbox[2] > width - 12
        if index != primary and (area < min_area or touches_edge or near_vertical_edge):
            continue
        for x, y in pixels:
            keep[y, x] = True
    cleaned = frame.copy()
    cleaned.putalpha(Image.fromarray((keep * 255).astype(np.uint8), "L"))
    return cleaned


def fit_to_cell(frame: Image.Image, *, baseline: int = CELL_H - 6) -> Image.Image:
    """Keep each original pose centred and fully visible inside one Codex atlas cell."""
    alpha = frame.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return Image.new("RGBA", (CELL_W, CELL_H))
    sprite = frame.crop(bbox)
    scale = min((CELL_W - 12) / sprite.width, (CELL_H - 12) / sprite.height)
    resized = sprite.resize(
        (max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale))),
        Image.Resampling.LANCZOS,
    )
    cell = Image.new("RGBA", (CELL_W, CELL_H))
    cell.alpha_composite(resized, ((CELL_W - resized.width) // 2, baseline - resized.height))
    return cell


def fit_registered_groups(
    source_frames: list[Image.Image],
    *,
    reference_frame: Image.Image,
    group_size: int = 4,
    baseline: int = CELL_H - 6,
) -> list[Image.Image]:
    """Register a multi-row action to the idle eye scale and body baseline.

    Detached dove/effect bounds cannot determine character scale: as the dove
    flies away they make NecoL shrink.  The two blue eyes are the stable visual
    ruler in open-eye frames.  Each four-frame source row gets one eye-derived
    scale; closed-eye anchors are interpolated from their neighbors.  The
    character baseline stays fixed while remote effects may approach the cell
    edge instead of zooming the character.
    """
    if not source_frames or len(source_frames) % group_size:
        raise ValueError("Registered frame count must be a non-zero multiple of group_size.")

    def eye_pair(frame: Image.Image) -> tuple[tuple[float, float], tuple[float, float]] | None:
        rgba = np.asarray(frame)
        red = rgba[:, :, 0].astype(np.int16)
        green = rgba[:, :, 1].astype(np.int16)
        blue = rgba[:, :, 2].astype(np.int16)
        mask = (
            (rgba[:, :, 3] > 0)
            & (blue > 130)
            & (red < 170)
            & (blue - red > 25)
            & (blue - green > 0)
        )
        height, width = mask.shape
        visited = np.zeros_like(mask)
        components: list[tuple[int, float, float]] = []
        for y in range(height):
            for x in range(width):
                if not mask[y, x] or visited[y, x]:
                    continue
                queue = deque([(x, y)])
                visited[y, x] = True
                xs: list[int] = []
                ys: list[int] = []
                while queue:
                    cx, cy = queue.popleft()
                    xs.append(cx)
                    ys.append(cy)
                    for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                        if (
                            0 <= nx < width
                            and 0 <= ny < height
                            and mask[ny, nx]
                            and not visited[ny, nx]
                        ):
                            visited[ny, nx] = True
                            queue.append((nx, ny))
                if len(xs) >= 40:
                    components.append((len(xs), float(np.mean(xs)), float(np.mean(ys))))
        if len(components) < 2:
            return None
        eyes = sorted(components, reverse=True)[:2]
        centres = sorted(((item[1], item[2]) for item in eyes), key=lambda point: point[0])
        return centres[0], centres[1]

    def split_primary_and_effects(frame: Image.Image) -> tuple[Image.Image, Image.Image]:
        alpha = np.asarray(frame.getchannel("A")) > 0
        height, width = alpha.shape
        visited = np.zeros_like(alpha)
        components: list[list[tuple[int, int]]] = []
        for y in range(height):
            for x in range(width):
                if not alpha[y, x] or visited[y, x]:
                    continue
                queue = deque([(x, y)])
                visited[y, x] = True
                pixels: list[tuple[int, int]] = []
                while queue:
                    cx, cy = queue.popleft()
                    pixels.append((cx, cy))
                    for nx, ny in (
                        (cx - 1, cy - 1), (cx, cy - 1), (cx + 1, cy - 1),
                        (cx - 1, cy),                     (cx + 1, cy),
                        (cx - 1, cy + 1), (cx, cy + 1), (cx + 1, cy + 1),
                    ):
                        if (
                            0 <= nx < width
                            and 0 <= ny < height
                            and alpha[ny, nx]
                            and not visited[ny, nx]
                        ):
                            visited[ny, nx] = True
                            queue.append((nx, ny))
                components.append(pixels)
        primary_index = max(range(len(components)), key=lambda index: len(components[index]))
        primary_mask = np.zeros_like(alpha)
        effects_mask = np.zeros_like(alpha)
        for index, pixels in enumerate(components):
            target = primary_mask if index == primary_index else effects_mask
            for x, y in pixels:
                target[y, x] = True
        primary = frame.copy()
        effects = frame.copy()
        primary.putalpha(Image.fromarray((primary_mask * 255).astype(np.uint8), "L"))
        effects.putalpha(Image.fromarray((effects_mask * 255).astype(np.uint8), "L"))
        return primary, effects

    reference_eyes = eye_pair(reference_frame)
    if reference_eyes is None:
        raise ValueError("The idle reference does not contain two detectable open eyes.")
    target_mid_x = (reference_eyes[0][0] + reference_eyes[1][0]) / 2
    target_separation = float(
        np.hypot(
            reference_eyes[1][0] - reference_eyes[0][0],
            reference_eyes[1][1] - reference_eyes[0][1],
        )
    )

    fitted: list[Image.Image] = []
    for start in range(0, len(source_frames), group_size):
        group = source_frames[start : start + group_size]
        known: dict[int, tuple[float, float]] = {}
        separations: list[float] = []
        for index, frame in enumerate(group):
            eyes = eye_pair(frame)
            if eyes is None:
                continue
            known[index] = ((eyes[0][0] + eyes[1][0]) / 2, (eyes[0][1] + eyes[1][1]) / 2)
            separations.append(float(np.hypot(eyes[1][0] - eyes[0][0], eyes[1][1] - eyes[0][1])))
        if not known:
            raise ValueError("An action group has no open-eye frame for registration.")
        scale = target_separation / float(np.median(separations))

        def anchor(index: int) -> tuple[float, float]:
            if index in known:
                return known[index]
            before = max((value for value in known if value < index), default=None)
            after = min((value for value in known if value > index), default=None)
            if before is None:
                return known[after]  # type: ignore[index]
            if after is None:
                return known[before]
            ratio = (index - before) / (after - before)
            return (
                known[before][0] + (known[after][0] - known[before][0]) * ratio,
                known[before][1] + (known[after][1] - known[before][1]) * ratio,
            )

        for index, frame in enumerate(group):
            bbox = frame.getchannel("A").getbbox()
            if bbox is None:
                raise ValueError("Cannot register an empty action frame.")
            source_mid_x, _ = anchor(index)
            primary, effects = split_primary_and_effects(frame)
            resized_primary = primary.resize(
                (max(1, round(frame.width * scale)), max(1, round(frame.height * scale))),
                Image.Resampling.LANCZOS,
            )
            resized_effects = effects.resize(resized_primary.size, Image.Resampling.LANCZOS)
            x = round(target_mid_x - source_mid_x * scale)
            y = round(baseline - bbox[3] * scale)
            cell = Image.new("RGBA", (CELL_W, CELL_H))
            cell.alpha_composite(resized_primary, (x, y))

            # Detached birds, hearts, and sparkles keep their relative layout
            # unless that would crop them.  Clamp the effect group inward
            # without moving or rescaling NecoL herself.
            effect_bbox = resized_effects.getchannel("A").getbbox()
            if effect_bbox is not None:
                effect_x = x
                effect_y = y
                min_x = 4 - effect_bbox[0]
                max_x = CELL_W - 4 - effect_bbox[2]
                min_y = 4 - effect_bbox[1]
                max_y = CELL_H - 4 - effect_bbox[3]
                if min_x <= max_x:
                    effect_x = min(max(effect_x, min_x), max_x)
                if min_y <= max_y:
                    effect_y = min(max(effect_y, min_y), max_y)
                cell.alpha_composite(resized_effects, (effect_x, effect_y))
            fitted.append(cell)
    return fitted


def frames(filename: str, columns: int, rows: int, *, baseline: int = CELL_H - 6) -> list[Image.Image]:
    return [
        fit_to_cell(remove_neighbour_frame_fragments(remove_checkerboard(frame)), baseline=baseline)
        for frame in split_grid(SOURCE / filename, columns, rows)
    ]


def cleaned_source_frames(filename: str, columns: int, rows: int) -> list[Image.Image]:
    """Return original-resolution foreground frames before any resizing."""
    return [
        remove_neighbour_frame_fragments(remove_checkerboard(frame))
        for frame in split_grid(SOURCE / filename, columns, rows)
    ]


def find_bow_anchor(frame: Image.Image) -> tuple[float, float, int]:
    """Locate the central lower pink bow used to register garment patches."""
    rgba = np.asarray(frame)
    alpha = rgba[:, :, 3] > 0
    bbox = frame.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("Cannot register an empty NecoL frame.")
    red = rgba[:, :, 0].astype(np.int16)
    green = rgba[:, :, 1].astype(np.int16)
    blue = rgba[:, :, 2].astype(np.int16)
    yy, xx = np.indices(alpha.shape)
    pink = (
        alpha
        & (red > 165)
        & (green > 85)
        & (blue > 85)
        & (red - green > 16)
        & (red - blue > 6)
        & (xx >= bbox[0] + (bbox[2] - bbox[0]) * 0.30)
        & (xx <= bbox[0] + (bbox[2] - bbox[0]) * 0.70)
        & (yy >= bbox[1] + (bbox[3] - bbox[1]) * 0.52)
    )
    ys, xs = np.where(pink)
    if xs.size < 12:
        raise ValueError("Could not locate NecoL's central bow for garment registration.")
    return float(np.median(xs)), float(np.median(ys)), int(np.percentile(ys, 90))


def make_registered_garment_patch(reference: Image.Image) -> tuple[Image.Image, tuple[float, float, int]]:
    """Extract original idle pixels strictly below the registered bow."""
    anchor = find_bow_anchor(reference)
    centre_x, centre_y, bow_bottom = anchor
    alpha = np.asarray(reference.getchannel("A")) > 0
    keep = np.zeros_like(alpha)
    patch_top = max(0, round(centre_y - 72))
    for y in range(patch_top, reference.height):
        xs = np.flatnonzero(alpha[y])
        if not xs.size:
            continue
        runs: list[tuple[int, int]] = []
        start = previous = int(xs[0])
        for value in xs[1:]:
            value = int(value)
            if value != previous + 1:
                runs.append((start, previous + 1))
                start = value
            previous = value
        runs.append((start, previous + 1))
        left, right = min(
            runs,
            key=lambda run: 0 if run[0] <= centre_x < run[1] else min(abs(centre_x - run[0]), abs(centre_x - run[1])),
        )
        left = max(left, round(centre_x - 72))
        right = min(right, round(centre_x + 72))
        if left < right:
            keep[y, left:right] = alpha[y, left:right]
    patch = reference.copy()
    patch.putalpha(Image.fromarray((keep * 255).astype(np.uint8), "L"))
    return patch, anchor


def repair_cropped_garment(
    action: Image.Image,
    garment_patch: Image.Image,
    reference_anchor: tuple[float, float, int],
) -> Image.Image:
    """Continue a cropped dove torso with aligned original idle pixels."""
    action_anchor = find_bow_anchor(action)
    dx = round(action_anchor[0] - reference_anchor[0])
    dy = round(action_anchor[1] - reference_anchor[1])
    underlay = Image.new("RGBA", action.size)
    underlay.alpha_composite(garment_patch, (dx, dy))

    # Match only pale garment fill to the action's lower-clothing colour.
    action_rgba = np.asarray(action)
    action_alpha = action_rgba[:, :, 3] > 0
    centre = round(action_anchor[0])
    central = action_alpha[:, max(0, centre - 100) : min(action.width, centre + 100)]
    ys = np.flatnonzero(central.any(axis=1))
    if ys.size:
        bottom = int(ys[-1])
        band = np.zeros_like(action_alpha)
        band[max(0, bottom - 36) : bottom + 1, max(0, centre - 90) : min(action.width, centre + 90)] = True
        rgb = action_rgba[:, :, :3]
        chroma = rgb.max(axis=2) - rgb.min(axis=2)
        samples = rgb[band & action_alpha & (rgb.min(axis=2) > 170) & (chroma < 55)]
        if samples.size:
            target = np.median(samples, axis=0)
            underlay_rgba = np.asarray(underlay).copy()
            underlay_rgb = underlay_rgba[:, :, :3]
            underlay_alpha = underlay_rgba[:, :, 3] > 0
            underlay_chroma = underlay_rgb.max(axis=2) - underlay_rgb.min(axis=2)
            pale = underlay_alpha & (underlay_rgb.min(axis=2) > 170) & (underlay_chroma < 55)
            if pale.any():
                source = np.median(underlay_rgb[pale], axis=0)
                adjusted = np.clip(underlay_rgb[pale].astype(np.float32) + (target - source), 0, 255)
                underlay_rgb[pale] = adjusted.astype(np.uint8)
                underlay = Image.fromarray(underlay_rgba, "RGBA")

    result = Image.new("RGBA", action.size)
    result.alpha_composite(underlay)
    overlay_rgba = np.asarray(action).copy()
    overlay_alpha = overlay_rgba[:, :, 3]
    seam_start = min(action.height, action_anchor[2] + 4)
    seam_end = min(action.height, seam_start + 16)
    left = max(0, round(action_anchor[0] - 145))
    right = min(action.width, round(action_anchor[0] + 135))
    if seam_start < seam_end and left < right:
        for y in range(seam_start, seam_end):
            factor = (seam_end - y - 1) / max(1, seam_end - seam_start)
            overlay_alpha[y, left:right] = np.round(overlay_alpha[y, left:right] * factor).astype(np.uint8)
        overlay_alpha[seam_end:, left:right] = 0
    overlay = Image.fromarray(overlay_rgba, "RGBA")
    result.alpha_composite(overlay)
    return result


def clear_outer_cell_slivers(frame: Image.Image, *, margin: int = 10) -> Image.Image:
    """Clear source-grid bleed confined to the outer edge of a fitted cell."""
    cleaned = frame.copy()
    alpha = np.asarray(cleaned.getchannel("A")).copy()
    alpha[:, :margin] = 0
    alpha[:, -margin:] = 0
    cleaned.putalpha(Image.fromarray(alpha, "L"))
    return cleaned


def save_preview(rows: list[tuple[str, list[Image.Image]]]) -> None:
    thumb_w, thumb_h = 96, 104
    sheet = Image.new("RGBA", (thumb_w * 8, thumb_h * 9), (236, 236, 236, 255))
    for row_index, (_, row_frames) in enumerate(rows):
        for column, frame in enumerate(row_frames):
            thumbnail = frame.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            sheet.alpha_composite(thumbnail, (column * thumb_w, row_index * thumb_h))
    sheet.convert("RGB").save(QA / "contact-sheet.png")


def normalize_transparent_pixels(image: Image.Image) -> Image.Image:
    """Codex validation requires transparent pixels to carry no hidden RGB residue."""
    result = image.copy()
    pixels = result.load()
    for y in range(result.height):
        for x in range(result.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                pixels[x, y] = (0, 0, 0, 0)
    return result


def save_gif_previews(rows: list[tuple[str, list[Image.Image]]]) -> None:
    preview_dir = QA / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    for name, row_frames in rows:
        row_frames[0].save(
            preview_dir / f"{name}.gif",
            save_all=True,
            append_images=row_frames[1:],
            duration=ROW_DURATIONS[name],
            loop=0,
            disposal=2,
            optimize=False,
        )


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)

    # The source strip offers six eyelid stages, but intermediate half-blinks
    # read as jitter at pet size.  Keep only the stable open and fully closed
    # poses.  Six cells remain populated because the v1 Codex atlas contract
    # addresses all six idle columns even though NecoL has two unique frames.
    idle_sources = cleaned_source_frames("新待机.png", 6, 1)
    idle_open = fit_to_cell(idle_sources[1])
    idle_closed = fit_to_cell(idle_sources[3])
    idle = [idle_open, idle_closed, idle_open, idle_open, idle_open, idle_open]
    chips = frames("吃薯片.png", 3, 2)
    failed = frames("失败.png", 4, 2)
    drag = frames("左拖拽和右拖拽.png", 7, 2)

    def idle_state(frame_count: int) -> list[Image.Image]:
        """Populate a stock state with only the same open/closed idle poses."""
        if frame_count < 2:
            raise ValueError("An idle-like state needs at least two frames.")
        return [idle_open, idle_closed] + [idle_open] * (frame_count - 2)

    # The Codex contract has nine fixed rows. Repeated final frames fill the required eighth drag slot.
    rows: list[tuple[str, list[Image.Image]]] = [
        ("idle", idle),
        ("running-right", drag[:7] + [drag[6]]),
        ("running-left", drag[7:] + [drag[-1]]),
        # Hover, greeting, and completion deliberately remain ordinary idle.
        # This removes all dove behavior and keeps the package runtime-free.
        ("waving", idle_state(4)),
        ("jumping", idle_state(5)),
        ("failed", failed),
        ("waiting", chips),
        ("running", chips),
        ("review", idle_state(6)),
    ]

    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H))
    for row_index, (_, row_frames) in enumerate(rows):
        if len(row_frames) > 8:
            raise ValueError("A Codex atlas row cannot exceed eight frames.")
        for column, frame in enumerate(row_frames):
            atlas.alpha_composite(frame, (column * CELL_W, row_index * CELL_H))

    atlas = normalize_transparent_pixels(atlas)
    atlas.save(OUT / "spritesheet.png")
    atlas.save(OUT / "spritesheet.webp", lossless=True, method=6, exact=True)
    save_preview(rows)
    save_gif_previews(rows)

    manifest = {
        "id": "necol",
        "displayName": "NecoL",
        "description": "Portable NecoL with two-frame idle, snack-work, failure, and drag animations.",
        "spritesheetPath": "spritesheet.webp",
    }
    (OUT / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (QA / "state-mapping.json").write_text(
        json.dumps({name: len(row_frames) for name, row_frames in rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    build()
