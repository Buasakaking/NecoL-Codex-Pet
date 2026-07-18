"""Apply the minimal generic Codex work/wait animation loop policy.

This patch adds no pet id, hover state, completion state, or NecoL-specific
branch.  It only keeps the stock ``running`` and ``waiting`` rows looping
while their React state remains active.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_ROOT = ROOT / "runtime_patch" / "source-26_715_3651"
BACKUP_ROOT = ROOT / "runtime_patch" / "work-loop-source-backup"
MANIFEST_PATH = ROOT / "runtime_patch" / "work-loop-patch.json"

OVERLAY_OLD_SIGNATURE = (
    "function xt({avatar:e,avatarMenuItems:t,debugWindowBorderVisible:n=!1,"
    "interactiveRegionRef:r,isDragging:i=!1,isNotificationTrayOpen:a=!0,"
    "restrictedSurface:o,layout:s,mascotLayout:c=s.mascot,mascotStyle:l,"
    "mascotDragState:d,mascotResizeHandle:f,notifications:p,"
)
OVERLAY_NEW_SIGNATURE = OVERLAY_OLD_SIGNATURE + "forceRunning:zz=!1,"
OVERLAY_OLD_STATE = "state:O.mascotState,style:l,transientState:d"
OVERLAY_NEW_STATE = "state:zz?`running`:O.mascotState,style:l,transientState:d"
OVERLAY_OLD_CALL = "(0,bn.jsx)(xt,{avatar:e,avatarMenuItems:"
OVERLAY_NEW_CALL = "(0,bn.jsx)(xt,{avatar:e,forceRunning:z,avatarMenuItems:"

OLD = (
    "function A(e,t){let n=z[e];if(t)return{frames:[n[0]],loopStartIndex:null};"
    "if(e===`idle`)return{frames:R,loopStartIndex:0};let r=[...n,...n,...n];"
    "return{frames:[...r,...R],loopStartIndex:r.length}}"
)
NEW = (
    "function A(e,t){let n=z[e];if(t)return{frames:[n[0]],loopStartIndex:null};"
    "if(e===`idle`)return{frames:R,loopStartIndex:0};"
    "if(e===`running`||e===`waiting`)return{frames:n,loopStartIndex:0};"
    "let r=[...n,...n,...n];return{frames:[...r,...R],loopStartIndex:r.length}}"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def avatar_asset(source_root: Path) -> Path:
    assets = source_root / "webview" / "assets"
    matches = sorted(assets.glob("codex-avatar-*.js"))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one codex-avatar asset, found {len(matches)}")
    return matches[0]


def overlay_asset(source_root: Path) -> Path:
    assets = source_root / "webview" / "assets"
    matches = sorted(assets.glob("avatar-overlay-page-*.js"))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one avatar overlay page asset, found {len(matches)}")
    return matches[0]


def apply(source_root: Path) -> dict[str, object]:
    path = avatar_asset(source_root)
    overlay = overlay_asset(source_root)
    backup_dir = BACKUP_ROOT / source_root.name
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / path.name
    if not backup.exists():
        shutil.copy2(path, backup)
    text = path.read_text(encoding="utf-8")
    if NEW not in text:
        count = text.count(OLD)
        if count != 1:
            raise RuntimeError(f"{path.name}: expected one stock animation anchor, found {count}")
        path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8", newline="")
    overlay_text = overlay.read_text(encoding="utf-8")
    if OVERLAY_NEW_SIGNATURE not in overlay_text:
        replacements = (
            (OVERLAY_OLD_SIGNATURE, OVERLAY_NEW_SIGNATURE),
            (OVERLAY_OLD_STATE, OVERLAY_NEW_STATE),
            (OVERLAY_OLD_CALL, OVERLAY_NEW_CALL),
        )
        for old, new in replacements:
            count = overlay_text.count(old)
            if count != 1:
                raise RuntimeError(f"{overlay.name}: expected one overlay anchor, found {count}")
            overlay_text = overlay_text.replace(old, new, 1)
        overlay.write_text(overlay_text, encoding="utf-8", newline="")
    result = {
        "ok": True,
        "patch": "generic-running-waiting-loop-v1",
        "source_root": str(source_root),
        "file": path.name,
        "overlay_file": overlay.name,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "pet_specific_states": False,
    }
    MANIFEST_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def verify(source_root: Path) -> dict[str, object]:
    path = avatar_asset(source_root)
    overlay = overlay_asset(source_root)
    text = path.read_text(encoding="utf-8")
    overlay_text = overlay.read_text(encoding="utf-8")
    return {
        "ok": NEW in text and OVERLAY_NEW_SIGNATURE in overlay_text and OVERLAY_NEW_STATE in overlay_text and OVERLAY_NEW_CALL in overlay_text and "necol-" not in text and "custom:necol" not in text and "custom:necol" not in overlay_text,
        "file": path.name,
        "overlay_file": overlay.name,
        "sha256": sha256(path),
        "generic_loop_marker": NEW in text,
        "generic_active_work_marker": OVERLAY_NEW_STATE in overlay_text,
        "necol_state_markers": "necol-" in text or "custom:necol" in text,
    }


def revert(source_root: Path) -> dict[str, object]:
    path = avatar_asset(source_root)
    backup = BACKUP_ROOT / source_root.name / path.name
    if not backup.is_file():
        raise FileNotFoundError(backup)
    shutil.copy2(backup, path)
    return {"ok": True, "reverted": str(path), "sha256": sha256(path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--apply", action="store_true")
    action.add_argument("--verify", action="store_true")
    action.add_argument("--revert", action="store_true")
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    if args.apply:
        result = apply(source_root)
    elif args.verify:
        result = verify(source_root)
    else:
        result = revert(source_root)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
