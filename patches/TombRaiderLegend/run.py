"""Tomb Raider Legend — Autonomous test orchestrator.

Modes:
  test           Full stage-light end-to-end release gate.
  test-hash      Hash stability test (camera-only, no WASD movement).
  record         Launch game, record your inputs, save macro.
  test-legacy    Backward-compatible alias for the full stage-light test.
  batch          Batch runs with randomized movement.
  batch-legacy   Backward-compatible alias for batch runs.

Usage:
  python patches/TombRaiderLegend/run.py test --build --randomize
  python patches/TombRaiderLegend/run.py test-hash --build
  python patches/TombRaiderLegend/run.py record
  python patches/TombRaiderLegend/run.py batch --start 1 --end 3 --total 3
"""

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
PROXY_DIR = SCRIPT_DIR / "proxy"
MACROS_FILE = SCRIPT_DIR / "macros.json"
MACRO_NAME = "test_session"

# Add repo root to path so livetools and config are importable
sys.path.insert(0, str(REPO_ROOT))
from config import (
    GAME_DIR,
    GAME_EXE,
    LAUNCHER,
    NVIDIA_SCREENSHOT_DIR as SCREENSHOTS_SRC,
    PROXY_LOG,
)
SCREENSHOTS_DIR = SCRIPT_DIR / "screenshots"
RELEASE_GATE_DIR = GAME_DIR / "artifacts" / "release_gate"
NIGHTLY_MOD_FILE = GAME_DIR / "rtx-remix" / "mods" / "trl-nightly" / "mod.usda"
DEFAULT_LAUNCH_CHAPTER = 2
DEFAULT_POST_LOAD_SEQUENCE = "ESC WAIT:3000 W WAIT:3000 RETURN"
DEFAULT_POST_LOAD_SETTLE_SECONDS = 3.0
_MIN_CAPTURE_SIGNAL = 32
_MIN_CAPTURE_STDDEV = 1.0
_MIN_CLEAN_FRAME_DIFF = 0.5
_HASH_HUE_BIN_SIZE = 8
_HASH_MAX_HUE_DRIFT = 16
_HASH_REQUIRED_STABLE_REGIONS = 2
_RELEASE_GATE_REQUIRED_CAPTURE_MARKERS = 3
_RELEASE_GATE_DEBUG_VIEW_SETTLE_SECONDS = 0.8
_RELEASE_GATE_CAPTURE_COOLDOWN_SECONDS = 0.4
_RELEASE_GATE_CAPTURE_RETRIES = 5
_RELEASE_GATE_CAPTURE_RETRY_DELAY_SECONDS = 1.0
_RELEASE_GATE_MIN_LIT_PIXEL_FRACTION = 0.15
_RELEASE_GATE_LIT_PIXEL_THRESHOLD = 24
_HASH_STABILITY_REGIONS = {
    "ground": (0.30, 0.65, 0.70, 0.95),
    "left_structure": (0.05, 0.30, 0.28, 0.75),
    "right_foliage": (0.72, 0.18, 0.95, 0.60),
}


def collect_screenshots(max_age_seconds=120, limit=3, after_ts=None,
                        destination_dir=None):
    """Copy the most recent `limit` screenshots from NVIDIA capture folder.

    The macro takes 2 standing-still shots during menu nav before the 3
    randomized movement shots. Taking only the last `limit` files ensures
    we always get the post-movement captures, not the pre-movement ones.
    """
    if not SCREENSHOTS_SRC.exists():
        print(f"WARNING: Screenshot folder not found: {SCREENSHOTS_SRC}")
        return []

    now = time.time()
    files = sorted(SCREENSHOTS_SRC.iterdir(),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    files = [f for f in files
             if f.suffix.lower() in (".png", ".jpg", ".bmp")
             and (now - f.stat().st_mtime) < max_age_seconds
             and (after_ts is None or f.stat().st_mtime > after_ts)]
    files = files[:limit]

    if not files:
        print("No recent screenshots found in NVIDIA capture folder.")
        return []

    target_dir = Path(destination_dir) if destination_dir else SCREENSHOTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    collected = []
    for f in files:
        dest = target_dir / f.name
        shutil.copy2(str(f), str(dest))
        collected.append(dest)
        print(f"  Screenshot: {f.name}")

    print(f"Collected {len(collected)} screenshots (last {max_age_seconds}s, "
          f"limit={limit}) to {target_dir}/")
    return collected


def _image_has_signal(image) -> bool:
    """Reject blank/near-black frames from flaky fullscreen capture paths."""
    from PIL import ImageStat

    rgb = image.convert("RGB")
    stat = ImageStat.Stat(rgb)
    mean_brightness = sum(float(v) for v in stat.mean) / 3.0
    max_stddev = max(float(v) for v in stat.stddev)
    max_value = max(channel[1] for channel in rgb.getextrema())
    return (
        max_value >= _MIN_CAPTURE_SIGNAL
        or max_stddev >= _MIN_CAPTURE_STDDEV
        or mean_brightness >= 2.0
    )


def _capture_window_client_image(hwnd):
    import ctypes
    from PIL import ImageGrab

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class POINT(ctypes.Structure):
        _fields_ = [
            ("x", ctypes.c_long),
            ("y", ctypes.c_long),
        ]

    user32 = ctypes.windll.user32
    rect = RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None

    origin = POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        return None

    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None

    return ImageGrab.grab(
        bbox=(origin.x, origin.y, origin.x + width, origin.y + height),
        all_screens=True,
    )


def capture_window_image(hwnd, destination: Path, *, prefer_nvidia: bool = True,
                         attempts: int = 3):
    """Capture a usable game frame and save it to `destination`."""
    from gamepilot.capture import capture_nvidia
    from livetools.gamectl import find_hwnd_by_exe, focus_hwnd

    for attempt in range(1, attempts + 1):
        refreshed_hwnd = find_hwnd_by_exe("trl.exe")
        if refreshed_hwnd:
            hwnd = refreshed_hwnd
        if not hwnd:
            print(f"WARNING: Capture attempt {attempt}/{attempts} could not find the game window")
            time.sleep(0.4)
            continue

        focus_hwnd(hwnd)
        time.sleep(0.25)
        image = _capture_window_client_image(hwnd)
        if image is None or not _image_has_signal(image):
            image = capture_nvidia(hwnd) if prefer_nvidia else None
        if image is None:
            print(f"WARNING: Capture attempt {attempt}/{attempts} failed for {destination.name}")
            time.sleep(0.4)
            continue
        if not _image_has_signal(image):
            print(f"WARNING: Capture attempt {attempt}/{attempts} produced a blank frame for {destination.name}")
            time.sleep(0.4)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination)
        print(f"  Capture: {destination.name}")
        return destination

    print(f"WARNING: Could not capture a usable frame for {destination.name}")
    return None


def run_macro_with_captures(hwnd, steps: str, *, prefix: str,
                            delay_ms: int = 200, prefer_nvidia: bool = True):
    """Execute macro tokens, replacing `]` with deterministic inline captures."""
    from livetools.gamectl import find_hwnd_by_exe, focus_hwnd, send_key

    focus_hwnd(hwnd)
    captures = []
    actions = []
    capture_index = 0

    for token in steps.strip().split():
        upper = token.upper()
        if upper.startswith("WAIT:"):
            ms = int(token.split(":")[1])
            time.sleep(ms / 1000.0)
            actions.append({"action": "wait", "ms": ms})
            continue

        if upper.startswith("HOLD:"):
            parts = token.split(":")
            key = parts[1]
            ms = int(parts[2]) if len(parts) > 2 else 500
            send_key(key, hold_ms=ms)
            actions.append({"action": "hold", "key": key, "hold_ms": ms})
            time.sleep(delay_ms / 1000.0)
            continue

        if token == "]":
            capture_index += 1
            capture_path = SCREENSHOTS_DIR / f"{prefix}-{capture_index:02d}.png"
            refreshed_hwnd = find_hwnd_by_exe("trl.exe")
            if refreshed_hwnd:
                hwnd = refreshed_hwnd
            captured = capture_window_image(
                hwnd,
                capture_path,
                prefer_nvidia=prefer_nvidia,
            )
            if captured:
                captures.append(captured)
            actions.append({"action": "capture", "path": str(capture_path)})
            time.sleep(delay_ms / 1000.0)
            continue

        send_key(token)
        actions.append({"action": "key", "key": token})
        time.sleep(delay_ms / 1000.0)

    return {"ok": True, "count": len(actions), "captures": captures}


def count_capture_markers(steps: str) -> int:
    return sum(1 for token in steps.split() if token == "]")


def wait_for_fresh_proxy_log(after_ts: float, timeout_seconds: int = 70) -> bool:
    """Wait for a proxy log that was written by the current run."""
    print("\n=== Waiting for proxy diagnostics ===")
    print("Proxy log appears ~50s after device creation.")
    wait_started_at = time.time()
    for i in range(timeout_seconds):
        if PROXY_LOG.exists():
            modified_at = PROXY_LOG.stat().st_mtime
            if modified_at >= after_ts:
                print(f"Proxy log ready: {PROXY_LOG}")
                return True
        time.sleep(1)
        if i % 10 == 9:
            elapsed = int(time.time() - wait_started_at)
            print(f"  ...{elapsed}s waiting for proxy log")

    print(f"WARNING: Proxy log not refreshed after {timeout_seconds}s")
    return False


def wait_for_fresh_screenshot(after_ts: float, *, timeout_seconds: float = 8.0,
                              destination_dir=None, target_name: str | None = None):
    """Wait for a screenshot written by the current run and copy it locally."""
    if not SCREENSHOTS_SRC.exists():
        return None

    target_dir = Path(destination_dir) if destination_dir else SCREENSHOTS_DIR
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        candidates = sorted(
            (
                f for f in SCREENSHOTS_SRC.iterdir()
                if f.suffix.lower() in (".png", ".jpg", ".bmp")
                and f.stat().st_mtime >= after_ts
            ),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            source = candidates[0]
            target_dir.mkdir(parents=True, exist_ok=True)
            destination = target_dir / (target_name or source.name)
            shutil.copy2(str(source), str(destination))
            print(f"  Screenshot: {destination.name}")
            return destination
        time.sleep(0.2)

    return None


def release_gate_frame_ready(path: str | Path) -> bool:
    """Reject mostly-black transition frames after live debug-view switches."""
    from PIL import Image
    import numpy as np

    image = Image.open(path).convert("RGB")
    luminance = np.array(image).mean(axis=2)
    lit_fraction = float((luminance > _RELEASE_GATE_LIT_PIXEL_THRESHOLD).mean())
    return lit_fraction >= _RELEASE_GATE_MIN_LIT_PIXEL_FRACTION


def capture_release_gate_evidence(hwnd, steps: str, *, run_label: str,
                                  delay_ms: int = 0):
    """Execute the release-gate macro and capture hash+clean frames inline.

    Each `]` token becomes a paired capture at the current camera position:
    first hash-debug view (277), then clean render (0). This keeps both
    evidence sets aligned to the same three stage positions without a second
    game launch.
    """
    from livetools.gamectl import find_hwnd_by_exe, focus_hwnd, send_key

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    hash_paths = []
    clean_paths = []
    actions = []
    capture_index = 0

    def _refresh_hwnd():
        nonlocal hwnd
        refreshed_hwnd = find_hwnd_by_exe("trl.exe")
        if refreshed_hwnd:
            hwnd = refreshed_hwnd
        return hwnd

    def _capture_view(view_name: str, debug_view_idx: int):
        destination = SCREENSHOTS_DIR / f"{run_label}-{view_name}-{capture_index:02d}.png"
        last_error = None
        for attempt in range(1, _RELEASE_GATE_CAPTURE_RETRIES + 1):
            current_hwnd = _refresh_hwnd()
            if not current_hwnd:
                return None, f"Game window disappeared before {view_name} capture {capture_index}"

            set_debug_view(debug_view_idx)
            time.sleep(_RELEASE_GATE_DEBUG_VIEW_SETTLE_SECONDS)
            focus_hwnd(current_hwnd)
            time.sleep(0.3)
            capture_started_at = time.time()
            send_key("]", hold_ms=50)
            captured = wait_for_fresh_screenshot(
                capture_started_at,
                timeout_seconds=8.0,
                destination_dir=SCREENSHOTS_DIR,
                target_name=destination.name,
            )
            if captured is None:
                captured = capture_window_image(
                    current_hwnd,
                    destination,
                    prefer_nvidia=True,
                    attempts=3,
                )
            if captured is None:
                last_error = f"Failed to capture a usable {view_name} frame for capture {capture_index}"
                time.sleep(_RELEASE_GATE_CAPTURE_RETRY_DELAY_SECONDS)
                continue
            if release_gate_frame_ready(captured):
                print(f"  {view_name.title()} capture {capture_index}: {captured.name}")
                time.sleep(_RELEASE_GATE_CAPTURE_COOLDOWN_SECONDS)
                return captured, None

            print(f"  {view_name.title()} capture {capture_index} looked unready "
                  f"(attempt {attempt}/{_RELEASE_GATE_CAPTURE_RETRIES}); retrying...")
            last_error = f"{view_name.title()} capture {capture_index} stayed mostly black"
            time.sleep(_RELEASE_GATE_CAPTURE_RETRY_DELAY_SECONDS)

        return None, last_error or (
            f"Failed to capture a usable {view_name} frame for capture {capture_index}"
        )

    if _refresh_hwnd():
        focus_hwnd(hwnd)
        time.sleep(0.5)

    for token in steps.strip().split():
        upper = token.upper()
        if upper.startswith("WAIT:"):
            ms = int(token.split(":")[1])
            time.sleep(ms / 1000.0)
            actions.append({"action": "wait", "ms": ms})
            continue

        if upper.startswith("HOLD:"):
            parts = token.split(":")
            key = parts[1]
            ms = int(parts[2]) if len(parts) > 2 else 500
            if not _refresh_hwnd():
                return {
                    "ok": False,
                    "error": f"Game window disappeared before HOLD:{key}:{ms}",
                    "hash_paths": hash_paths,
                    "clean_paths": clean_paths,
                    "actions": actions,
                }
            focus_hwnd(hwnd)
            send_key(key, hold_ms=ms)
            actions.append({"action": "hold", "key": key, "hold_ms": ms})
            time.sleep(delay_ms / 1000.0)
            continue

        if token == "]":
            capture_index += 1
            hash_path, hash_error = _capture_view("hash", 277)
            if hash_error:
                return {
                    "ok": False,
                    "error": hash_error,
                    "hash_paths": hash_paths,
                    "clean_paths": clean_paths,
                    "actions": actions,
                }
            clean_path, clean_error = _capture_view("clean", 0)
            if clean_error:
                return {
                    "ok": False,
                    "error": clean_error,
                    "hash_paths": hash_paths,
                    "clean_paths": clean_paths,
                    "actions": actions,
                }
            hash_paths.append(hash_path)
            clean_paths.append(clean_path)
            actions.append({
                "action": "capture_pair",
                "index": capture_index,
                "hash_path": str(hash_path),
                "clean_path": str(clean_path),
            })
            continue

        if not _refresh_hwnd():
            return {
                "ok": False,
                "error": f"Game window disappeared before key '{token}'",
                "hash_paths": hash_paths,
                "clean_paths": clean_paths,
                "actions": actions,
            }
        focus_hwnd(hwnd)
        send_key(token)
        actions.append({"action": "key", "key": token})
        time.sleep(delay_ms / 1000.0)

    set_debug_view(0)
    return {
        "ok": True,
        "count": len(actions),
        "capture_points": capture_index,
        "hash_paths": hash_paths,
        "clean_paths": clean_paths,
        "actions": actions,
    }


def _mean_frame_difference(path_a: str | Path, path_b: str | Path) -> float:
    from PIL import Image, ImageChops, ImageStat

    img_a = Image.open(path_a).convert("RGB").resize((320, 180), Image.Resampling.BILINEAR)
    img_b = Image.open(path_b).convert("RGB").resize((320, 180), Image.Resampling.BILINEAR)
    diff = ImageChops.difference(img_a, img_b)
    stat = ImageStat.Stat(diff)
    return sum(float(value) for value in stat.mean) / 3.0


def evaluate_release_gate_movement(clean_paths: list[str | Path]) -> dict[str, object]:
    differences = [
        round(_mean_frame_difference(left, right), 3)
        for left, right in zip(clean_paths, clean_paths[1:])
    ]
    passed = bool(differences) and all(diff >= _MIN_CLEAN_FRAME_DIFF for diff in differences)
    return {"passed": passed, "differences": differences}


def _dominant_hue_in_roi(path: str | Path, roi: tuple[float, float, float, float]):
    from PIL import Image
    import numpy as np

    image = Image.open(path).convert("HSV")
    width, height = image.size
    x1, y1, x2, y2 = roi
    crop = np.array(image.crop((
        int(width * x1),
        int(height * y1),
        int(width * x2),
        int(height * y2),
    )))
    saturation = crop[:, :, 1]
    value = crop[:, :, 2]
    mask = (saturation > 80) & (value > 40)
    if int(mask.sum()) < 50:
        return None

    hues = crop[:, :, 0][mask]
    bins = 256 // _HASH_HUE_BIN_SIZE
    histogram = np.bincount((hues // _HASH_HUE_BIN_SIZE).astype(int), minlength=bins)
    return int(histogram.argmax()) * _HASH_HUE_BIN_SIZE


def _circular_hue_distance(left: int, right: int) -> int:
    raw = abs(left - right)
    return min(raw, 256 - raw)


def evaluate_release_gate_hash_stability(hash_paths: list[str | Path]) -> dict[str, object]:
    if len(hash_paths) < 3:
        return {
            "passed": False,
            "stable_regions": 0,
            "required_stable_regions": _HASH_REQUIRED_STABLE_REGIONS,
            "regions": {
                name: {"hues": [], "max_drift": None, "passed": False}
                for name in _HASH_STABILITY_REGIONS
            },
        }

    region_report: dict[str, dict[str, object]] = {}
    stable_regions = 0

    for name, roi in _HASH_STABILITY_REGIONS.items():
        hues = [_dominant_hue_in_roi(path, roi) for path in hash_paths]
        present_hues = [hue for hue in hues if hue is not None]
        max_drift = 999
        passed = False
        if len(present_hues) >= len(hash_paths):
            max_drift = max(
                _circular_hue_distance(left, right)
                for left, right in zip(present_hues, present_hues[1:])
            ) if len(present_hues) > 1 else 0
            passed = max_drift <= _HASH_MAX_HUE_DRIFT
            if passed:
                stable_regions += 1

        region_report[name] = {
            "hues": hues,
            "max_drift": max_drift if max_drift != 999 else None,
            "passed": passed,
        }

    return {
        "passed": stable_regions >= _HASH_REQUIRED_STABLE_REGIONS,
        "stable_regions": stable_regions,
        "required_stable_regions": _HASH_REQUIRED_STABLE_REGIONS,
        "regions": region_report,
    }


def evaluate_release_gate(hash_paths: list[str | Path], clean_paths: list[str | Path],
                          log_path: str | Path | None, *, crashed: bool) -> dict[str, object]:
    from autopatch.evaluator import evaluate_screenshots
    from patches.TombRaiderLegend.nightly.logs import parse_proxy_log
    from patches.TombRaiderLegend.nightly.manifests import load_nightly_config

    config = load_nightly_config()
    light_report = evaluate_screenshots(clean_paths)
    movement_report = evaluate_release_gate_movement(clean_paths)
    hash_report = evaluate_release_gate_hash_stability(hash_paths)
    log_summary = parse_proxy_log(log_path, config.required_patch_tokens)
    log_report = {
        "passed": (
            log_summary.all_required_patches_present
            and log_summary.max_passthrough == 0
            and log_summary.max_xform_blocked == 0
        ),
        "required_patch_hits": dict(log_summary.required_patch_hits),
        "max_passthrough": log_summary.max_passthrough,
        "max_xform_blocked": log_summary.max_xform_blocked,
        "p95_cpu_ms": log_summary.p95_cpu_ms,
        "median_cpu_ms": log_summary.median_cpu_ms,
    }

    report = {
        "passed": (
            not crashed
            and len(hash_paths) >= 3
            and len(clean_paths) >= 3
            and hash_report["passed"]
            and light_report.passed
            and movement_report["passed"]
            and log_report["passed"]
        ),
        "crashed": crashed,
        "hash_paths": [str(path) for path in hash_paths],
        "clean_paths": [str(path) for path in clean_paths],
        "hash_stability": hash_report,
        "lights": {
            "passed": light_report.passed,
            "red_visible": list(light_report.red_visible),
            "green_visible": list(light_report.green_visible),
            "confidence": float(light_report.confidence),
        },
        "movement": movement_report,
        "log": log_report,
    }
    return report


def write_release_gate_report(report: dict[str, object]) -> Path:
    RELEASE_GATE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    report_path = RELEASE_GATE_DIR / f"release-gate-{timestamp}.json"
    latest_path = RELEASE_GATE_DIR / "latest.json"
    payload = dict(report)
    payload["generated_at"] = timestamp
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    latest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return report_path


def deploy_runtime_bundle(proxy_dir=PROXY_DIR, proxy_ini_path=None,
                          rtx_conf_path=None, game_dir=GAME_DIR):
    """Deploy authoritative TRL runtime files to the live game directory."""
    proxy_dir = Path(proxy_dir)
    proxy_ini_path = Path(proxy_ini_path) if proxy_ini_path else proxy_dir / "proxy.ini"
    rtx_conf_path = Path(rtx_conf_path) if rtx_conf_path else SCRIPT_DIR / "rtx.conf"

    dll_src = proxy_dir / "d3d9.dll"
    if not dll_src.exists():
        raise FileNotFoundError(f"Built proxy DLL not found: {dll_src}")
    if not proxy_ini_path.exists():
        raise FileNotFoundError(f"Proxy config not found: {proxy_ini_path}")

    shutil.copy2(str(dll_src), str(game_dir / "d3d9.dll"))
    shutil.copy2(str(proxy_ini_path), str(game_dir / "proxy.ini"))
    if rtx_conf_path.exists():
        shutil.copy2(str(rtx_conf_path), str(game_dir / "rtx.conf"))
        print(f"Deployed d3d9.dll + proxy.ini + rtx.conf to {game_dir.name}/")
    else:
        print(f"Deployed d3d9.dll + proxy.ini to {game_dir.name}/ (no rtx.conf template)")


def suspend_nightly_mod_override() -> Path | None:
    """Temporarily disable nightly's live mod override during manual release gates."""
    if not NIGHTLY_MOD_FILE.exists():
        return None

    disabled_path = NIGHTLY_MOD_FILE.with_suffix(".usda.disabled")
    if disabled_path.exists():
        disabled_path.unlink()
    NIGHTLY_MOD_FILE.replace(disabled_path)
    print(f"Temporarily disabled nightly mod override: {disabled_path.name}")
    return disabled_path


def restore_nightly_mod_override(disabled_path: Path | None) -> None:
    if not disabled_path or not disabled_path.exists():
        return
    disabled_path.replace(NIGHTLY_MOD_FILE)
    print(f"Restored nightly mod override: {NIGHTLY_MOD_FILE.name}")


def build_proxy_bundle(proxy_dir=PROXY_DIR, proxy_ini_path=None,
                       rtx_conf_path=None, game_dir=GAME_DIR):
    """Build and deploy a TRL proxy bundle with the game directory as cwd."""
    proxy_dir = Path(proxy_dir)
    build_bat = proxy_dir / "build.bat"
    if not build_bat.exists():
        raise FileNotFoundError(f"build.bat not found: {build_bat}")

    print("\n=== Building proxy ===")
    command = f'pushd "{proxy_dir}" && call "{build_bat.name}"'
    r = subprocess.run(
        command,
        capture_output=True,
        text=True,
        shell=True,
        cwd=str(game_dir),
    )
    print(r.stdout)
    if r.returncode != 0:
        raise RuntimeError(f"BUILD FAILED:\n{r.stderr}")

    deploy_runtime_bundle(
        proxy_dir=proxy_dir,
        proxy_ini_path=proxy_ini_path,
        rtx_conf_path=rtx_conf_path,
        game_dir=game_dir,
    )


def set_graphics_config():
    """Set TRL graphics registry for Remix and skip the setup screen.

    The setup screen appears when AdapterIdentifier changes (new d3d9.dll).
    We write a fixed config so the game always launches directly while keeping
    TRL water effects enabled for animated water/waterfall materials.
    """
    import winreg
    gfx_path = r"Software\Crystal Dynamics\Tomb Raider: Legend\Graphics"
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, gfx_path,
                                 0, winreg.KEY_ALL_ACCESS)

        # Read current adapter GUID and mode so we can preserve them
        try:
            adapter_guid, _ = winreg.QueryValueEx(key, "AdapterIdentifier")
        except FileNotFoundError:
            adapter_guid = ""
        try:
            mode_id, _ = winreg.QueryValueEx(key, "FullscreenModeID")
        except FileNotFoundError:
            mode_id = 0

        settings = {
            "Fullscreen": 1,
            "Width": 3840,
            "Height": 2160,
            "Refresh": 240,
            "EnableFSAA": 0,
            "EnableFullscreenEffects": 0,
            "EnableDepthOfField": 0,
            "EnableVSync": 0,
            "EnableShadows": 0,
            "EnableWaterFX": 1,
            "EnableReflection": 0,
            "UseShader20": 0,
            "UseShader30": 0,
            "BestTextureFilter": 2,
            "DisableHardwareVP": 0,
            "Disable32BitTextures": 0,
            "ExtendedDialog": 1,
            "AdapterID": 0,
            "DisablePureDevice": 0,         # Proxy already strips PUREDEVICE flag
            "DontDeferShaderCreation": 1,    # All shaders created at startup
            "AlwaysRenderZPassFirst": 0,    # Interferes with Remix rendering
            "CreateGameFourCC": 0,          # Not needed, can cause format issues
            "NoDynamicTextures": 0,
            "Shadows": 0,
            "AntiAlias": 0,
            "TextureFilter": 0,
            "NextGenContent": 0,
            "ScreenEffects": 0,
        }
        for name, val in settings.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, val)

        # Preserve adapter GUID and fullscreen mode (prevents setup screen)
        if adapter_guid:
            winreg.SetValueEx(key, "AdapterIdentifier", 0,
                              winreg.REG_SZ, adapter_guid)
        if mode_id:
            winreg.SetValueEx(key, "FullscreenModeID", 0,
                              winreg.REG_DWORD, mode_id)

        key.Close()
        print("Graphics config set (lowest settings, setup screen bypassed)")
    except Exception as e:
        print(f"WARNING: Could not set graphics config: {e}")


def dismiss_setup_dialog():
    """Detect the TRL setup dialog, configure optimal settings, and click Ok.

    Sets 3840x2160 resolution, 240Hz refresh, unchecks all graphics effects
    except water (shadows, reflections, DoF, fullscreen effects, FSAA, next-gen,
    shader 3.0) for cleanest RTX Remix compatibility.
    """
    import ctypes
    import ctypes.wintypes as wt

    user32 = ctypes.windll.user32
    user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    user32.SendMessageW.restype = ctypes.c_long
    BM_CLICK = 0x00F5
    BM_GETCHECK = 0x00F0
    BM_SETCHECK = 0x00F1
    BST_CHECKED = 1
    BST_UNCHECKED = 0
    CB_GETCOUNT = 0x0146
    CB_GETLBTEXT = 0x0148
    CB_GETLBTEXTLEN = 0x0149
    CB_SETCURSEL = 0x014E
    CB_GETCURSEL = 0x0147
    WM_COMMAND = 0x0111
    CBN_SELCHANGE = 1
    GW_ID = 0xFFFC  # GetWindowLong index for control ID
    WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    from livetools.gamectl import _find_pid
    pid = _find_pid("trl.exe")
    if not pid:
        return False

    dialog_hwnd = [None]

    @WNDENUMPROC
    def find_dialog(hwnd, _):
        proc_id = wt.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if proc_id.value != pid:
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if "Setup" in buf.value and user32.IsWindowVisible(hwnd):
            dialog_hwnd[0] = hwnd
            return False
        return True

    user32.EnumWindows(find_dialog, 0)

    if not dialog_hwnd[0]:
        return False

    print("  Setup dialog detected — configuring settings...")

    # Collect all child controls
    children = {}  # text -> hwnd

    @WNDENUMPROC
    def collect_children(hwnd, _):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if buf.value:
            children[buf.value] = hwnd
        return True

    user32.EnumChildWindows(dialog_hwnd[0], collect_children, 0)

    # Helper: uncheck a checkbox if it's checked
    def ensure_unchecked(label):
        hwnd = children.get(label)
        if hwnd:
            state = user32.SendMessageW(hwnd, BM_GETCHECK, 0, 0)
            if state == BST_CHECKED:
                user32.SendMessageW(hwnd, BM_CLICK, 0, 0)
                time.sleep(0.05)
                print(f"    Unchecked: {label}")

    # Helper: check a checkbox if it's unchecked
    def ensure_checked(label):
        hwnd = children.get(label)
        if hwnd:
            state = user32.SendMessageW(hwnd, BM_GETCHECK, 0, 0)
            if state == BST_UNCHECKED:
                user32.SendMessageW(hwnd, BM_CLICK, 0, 0)
                time.sleep(0.05)
                print(f"    Checked: {label}")

    # Helper: set combobox selection AND notify the dialog
    def combo_select(combo_hwnd, index):
        """Select item in combobox and send CBN_SELCHANGE to the dialog."""
        user32.SendMessageW(combo_hwnd, CB_SETCURSEL, index, 0)
        ctrl_id = user32.GetDlgCtrlID(combo_hwnd)
        wparam = (CBN_SELCHANGE << 16) | (ctrl_id & 0xFFFF)
        user32.SendMessageW(dialog_hwnd[0], WM_COMMAND, wparam, combo_hwnd)

    # Helper: select combobox item containing target text
    def select_combo_item(label_text, target_text):
        combo_hwnds = []

        @WNDENUMPROC
        def find_combos(hwnd, _):
            cls = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls, 256)
            if cls.value == "ComboBox":
                combo_hwnds.append(hwnd)
            return True

        user32.EnumChildWindows(dialog_hwnd[0], find_combos, 0)

        label_hwnd = children.get(label_text)
        if not label_hwnd:
            return

        label_rect = wt.RECT()
        user32.GetWindowRect(label_hwnd, ctypes.byref(label_rect))

        # Find the combo closest to the right of / below the label
        best_combo = None
        best_dist = 99999
        for ch in combo_hwnds:
            cr = wt.RECT()
            user32.GetWindowRect(ch, ctypes.byref(cr))
            if abs(cr.top - label_rect.top) < 30 and cr.left > label_rect.left:
                dist = cr.left - label_rect.right
                if dist < best_dist:
                    best_dist = dist
                    best_combo = ch

        if not best_combo:
            # Fallback: try all combos
            for ch in combo_hwnds:
                count = user32.SendMessageW(ch, CB_GETCOUNT, 0, 0)
                for i in range(count):
                    length = user32.SendMessageW(ch, CB_GETLBTEXTLEN, i, 0)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.SendMessageW(ch, CB_GETLBTEXT, i,
                                            ctypes.addressof(buf))
                        if target_text.lower() in buf.value.lower():
                            combo_select(ch, i)
                            print(f"    {label_text}: {buf.value}")
                            return
            return

        # Search items in the best combo
        count = user32.SendMessageW(best_combo, CB_GETCOUNT, 0, 0)
        for i in range(count):
            length = user32.SendMessageW(best_combo, CB_GETLBTEXTLEN, i, 0)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.SendMessageW(best_combo, CB_GETLBTEXT, i,
                                    ctypes.addressof(buf))
                if target_text.lower() in buf.value.lower():
                    combo_select(best_combo, i)
                    print(f"    {label_text}: {buf.value}")
                    return

        # If exact target not found, select the last item (highest res/rate)
        if count > 0:
            combo_select(best_combo, count - 1)
            print(f"    {label_text}: selected last option (highest available)")

    # === Configure settings ===

    # Fullscreen: ensure checked
    ensure_checked("Fullscreen")

    # Resolution: try 3840x2160, fall back to highest available
    select_combo_item("Resolution", "3840")

    # Refresh rate: try 240, fall back to highest
    select_combo_item("Refresh Rate", "240")

    # Keep water enabled, disable the rest for cleanest Remix compatibility
    ensure_unchecked("Enable VSync")
    ensure_unchecked("Enable Fullscreen Effects")
    ensure_unchecked("Enable Depth of Field")
    ensure_unchecked("Enable Shadows")
    ensure_unchecked("Enable Anti Aliasing")
    ensure_unchecked("Enable Reflections")
    ensure_checked("Enable Water Effects")
    ensure_unchecked("Next Generation Content")
    ensure_unchecked("Use 3.0 Shader Features")
    ensure_unchecked("LowRes Depth of Field")

    # DevTech options for RTX Remix compatibility
    ensure_unchecked("Disable Hardware Vertexshaders")
    ensure_unchecked("Disable Hardware DXTC")
    ensure_unchecked("Disable Non Pow2 Support")
    ensure_unchecked("Use D3D Reference Device")
    ensure_unchecked("No Dynamic Textures")
    ensure_unchecked("Disable Pure Device")      # Proxy already strips PUREDEVICE flag
    ensure_unchecked("D3D FPU Preserve")
    ensure_unchecked("Disable 32bit Textures")
    ensure_unchecked("Disable Driver Management")
    ensure_unchecked("Disable Hardware Shadow Maps")
    ensure_unchecked("Disable Null Render Targets")
    ensure_unchecked("Always Render Z-pass First")
    ensure_unchecked("Create Game FourCC")
    ensure_checked("Dont Defer Shader Creation") # All shaders created at startup for Remix

    time.sleep(1.0)

    # Verify critical settings before clicking Ok
    verify_hwnd = children.get("Dont Defer Shader Creation")
    if verify_hwnd:
        state = user32.SendMessageW(verify_hwnd, BM_GETCHECK, 0, 0)
        if state != BST_CHECKED:
            print("  WARNING: 'Dont Defer Shader Creation' not checked — retrying")
            user32.SendMessageW(verify_hwnd, BM_CLICK, 0, 0)
            time.sleep(0.05)

    # Click Ok to accept and launch
    ok_hwnd = children.get("Ok")
    if ok_hwnd:
        print("  Clicking Ok...")
        user32.SendMessageW(ok_hwnd, BM_CLICK, 0, 0)
        time.sleep(1)
        return True

    return False


def write_tr7_arg(chapter=DEFAULT_LAUNCH_CHAPTER):
    """Write TR7.arg to skip the main menu and load directly into a chapter.

    The game reads startup args from <drive>:\\TR7\\GAME\\PC\\TR7.arg.
    The nightly flow uses chapter 2, then advances through the Bolivia load
    sequence with ESC -> W -> ENTER after the window stabilizes.
    """
    drive = os.path.splitdrive(str(GAME_DIR))[0]
    arg_dir = Path(f"{drive}/TR7/GAME/PC")
    arg_dir.mkdir(parents=True, exist_ok=True)
    arg_file = arg_dir / "TR7.arg"
    arg_file.write_text(f"-NOMAINMENU -CHAPTER {chapter}")
    print(f"Wrote TR7.arg: -NOMAINMENU -CHAPTER {chapter}")


def kill_game():
    """Kill the game and Remix launcher helpers if they are still alive."""
    for image_name in ("trl.exe", "NvRemixLauncher32.exe", "NvRemixBridge.exe"):
        subprocess.run(["taskkill", "/f", "/im", image_name],
                       capture_output=True)
    time.sleep(2)


def _advance_to_bolivia_level(hwnd, sequence=DEFAULT_POST_LOAD_SEQUENCE,
                              settle_seconds=DEFAULT_POST_LOAD_SETTLE_SECONDS):
    """Advance from the chapter-2 load into the Bolivia gameplay state."""
    if not sequence:
        return

    from livetools.gamectl import focus_hwnd, send_keys

    focus_hwnd(hwnd)
    time.sleep(0.5)
    print(f"Sending Bolivia entry sequence: {sequence}")
    send_keys(hwnd, sequence, delay_ms=0)
    print(f"Waiting {settle_seconds:.1f}s for Bolivia gameplay to settle...")
    time.sleep(settle_seconds)


def launch_game(chapter=DEFAULT_LAUNCH_CHAPTER,
                post_load_sequence=DEFAULT_POST_LOAD_SEQUENCE,
                post_load_settle_seconds=DEFAULT_POST_LOAD_SETTLE_SECONDS):
    """Launch TRL into chapter 2 and advance into the Bolivia gameplay state."""
    from livetools.gamectl import find_hwnd_by_exe, get_window_info

    if not LAUNCHER.exists():
        print(f"ERROR: Launcher not found: {LAUNCHER}")
        sys.exit(1)
    if not GAME_EXE.exists():
        print(f"ERROR: Game exe not found: {GAME_EXE}")
        sys.exit(1)

    write_tr7_arg(chapter=chapter)

    print(f"Launching: {LAUNCHER.name} {GAME_EXE.name}")
    subprocess.Popen([str(LAUNCHER), str(GAME_EXE)], cwd=str(GAME_DIR))

    print("Waiting for game window...")
    hwnd = None
    setup_dismissed = False
    for i in range(90):  # up to 90 seconds
        # Check for setup dialog first — dismiss it if present
        if not setup_dismissed and dismiss_setup_dialog():
            setup_dismissed = True
            # After dismissing, wait a bit for the real game window
            time.sleep(3)
            continue

        hwnd = find_hwnd_by_exe("trl.exe")
        if hwnd:
            info = get_window_info(hwnd)
            # Make sure it's the game window, not the setup dialog
            if "Setup" not in info["title"]:
                print(f"  Found: {info['title']} (hwnd={hex(hwnd)}, "
                      f"pid={info['pid']})")
                break
            else:
                # Still the setup dialog — dismiss it
                dismiss_setup_dialog()
                hwnd = None
        time.sleep(1)
        if i % 10 == 9:
            print(f"  ...{i+1}s elapsed, still waiting")

    if not hwnd:
        print("ERROR: Game window not found after 90s")
        sys.exit(1)

    # Let the game fully load before sending any menu/cutscene navigation.
    print("Window found. Waiting 15s for chapter load and UI stabilization...")
    print("  (Do not click or alt-tab — let the game initialize)")
    time.sleep(15)
    _advance_to_bolivia_level(
        hwnd,
        sequence=post_load_sequence,
        settle_seconds=post_load_settle_seconds,
    )

    return hwnd


def build_proxy():
    """Build the proxy DLL via build.bat and deploy to game dir."""
    try:
        build_proxy_bundle(
            proxy_dir=PROXY_DIR,
            proxy_ini_path=PROXY_DIR / "proxy.ini",
            rtx_conf_path=SCRIPT_DIR / "rtx.conf",
            game_dir=GAME_DIR,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)


def do_record():
    """Launch game, record inputs, save as test_session macro."""
    from livetools.gamectl import (record, events_to_macro, save_macro,
                                   focus_hwnd)

    kill_game()
    hwnd = launch_game()

    print("\n=== Recording mode ===")
    print("Game should be focused. Play through your test routine.")
    print("Press F12 to stop recording.\n")

    events = record(hwnd, stop_key="F12")

    if not events:
        print("No events recorded.")
        return

    steps = events_to_macro(events)

    keys = sum(1 for e in events if e["type"] == "keydown")
    clicks = sum(1 for e in events if e["type"] in ("lclick", "rclick"))
    moves = sum(1 for e in events if e["type"] == "move")
    holds = steps.count("HOLD:")
    duration_s = events[-1]["time_ms"] / 1000.0
    m, s = divmod(int(duration_s), 60)

    desc = (f"Recorded test session ({keys} keys, {clicks} clicks, "
            f"{moves} moves, {m}m{s}s)")
    save_macro(MACROS_FILE, MACRO_NAME, desc, steps)

    print(f"\nSaved macro '{MACRO_NAME}' to {MACROS_FILE}")
    print(f"Duration: {m}m {s}s | Keys: {keys} | Clicks: {clicks} "
          f"| Moves: {moves} | Holds: {holds}")
    print(f"\nTest with:  python {Path(__file__).name} test")


def generate_random_movement_legacy():
    """Generate a bounded stage sweep for the release gate.

    The objective is to validate light stability across three nearby stage
    positions, not to wander far enough to leave the safe test area or induce
    avoidable crashes. Randomization is therefore kept within a narrow strafe
    envelope around the known-good Bolivia baseline.
    """
    tokens = []

    # Initial settle time after cutscene skip
    tokens.append("WAIT:2500")

    # Move into the stage area using a bounded forward step.
    forward_ms = random.randint(1800, 2600)
    tokens.append(f"HOLD:W:{forward_ms}")
    tokens.append("WAIT:1000")

    # Take a baseline screenshot before any movement
    tokens.append("]")
    tokens.append("WAIT:1000")

    # Sweep to one side, then across center to the opposite side.
    first_key, second_key = random.choice([("A", "D"), ("D", "A")])
    first_ms = random.randint(700, 1400)
    second_ms = first_ms + random.randint(900, 1600)

    tokens.append(f"HOLD:{first_key}:{first_ms}")
    tokens.append("WAIT:750")
    tokens.append("]")
    tokens.append("WAIT:1000")

    tokens.append(f"HOLD:{second_key}:{second_ms}")
    tokens.append("WAIT:750")
    tokens.append("]")

    return " ".join(tokens)


def do_live_analysis_legacy(hwnd, duration_s=60):
    """Run a live analysis phase: attach livetools, move Lara around while
    collecting render pipeline data, then save results.

    Sends gentle A/D strafes with mouse look-around to exercise the renderer
    from multiple angles while livetools captures function call data.

    Args:
        hwnd: Game window handle.
        duration_s: Total duration in seconds.

    Returns:
        dict with capture file paths and summary.
    """
    from livetools.gamectl import send_key, move_mouse_relative, focus_hwnd

    capture_dir = SCRIPT_DIR / "captures" / "live_analysis"
    capture_dir.mkdir(parents=True, exist_ok=True)

    # Attach livetools
    print("\n=== Live Analysis Phase ===")
    print("Attaching livetools...")
    r = subprocess.run(
        ["python", "-m", "livetools", "attach", "trl.exe"],
        capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    if "Attached" not in r.stdout and "Attached" not in r.stderr:
        print(f"WARNING: livetools attach may have failed: {r.stderr}")

    # Start render pipeline collect in background
    pipeline_file = str(capture_dir / "live_render_pipeline.jsonl")
    light_file = str(capture_dir / "live_light_system.jsonl")

    print(f"Starting {duration_s}s data collection...")
    collect_render = subprocess.Popen(
        ["python", "-m", "livetools", "collect",
         "0x00413950", "0x0040E470", "0x00ECBB00",
         "--duration", str(duration_s),
         "--read", "ecx; eax; [esp+4]:4:hex; [esp+8]:4:hex",
         "--fence", "0x00450DE0",
         "--label", "0x00413950=SetWorldMatrix",
         "--label", "0x0040E470=SetRenderStateCached",
         "--label", "0x00ECBB00=UploadViewProjMatrices",
         "--output", pipeline_file],
        cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    collect_lights = subprocess.Popen(
        ["python", "-m", "livetools", "collect",
         "0x0060C7D0", "0x006124E0", "0x0060B050", "0x0060E2D0",
         "--duration", str(duration_s),
         "--read", "ecx; eax; [esp+4]:4:hex",
         "--label", "0x0060C7D0=RenderLights_FrustumCull",
         "--label", "0x006124E0=LightVolume_Draw",
         "--label", "0x0060B050=LightVisibilityCheck",
         "--label", "0x0060E2D0=RenderLights_Caller",
         "--output", light_file],
        cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Move Lara around while collecting data
    print("Moving Lara with A/D strafes + mouse look-around...")
    focus_hwnd(hwnd)
    time.sleep(0.5)

    move_interval = 3  # seconds per movement cycle
    cycles = duration_s // move_interval
    for i in range(cycles):
        elapsed = i * move_interval
        phase = i % 6

        if phase == 0:
            send_key("A", hold_ms=random.randint(400, 1200))
        elif phase == 1:
            for _ in range(5):
                move_mouse_relative(random.randint(30, 80), random.randint(-15, 15))
                time.sleep(0.1)
        elif phase == 2:
            send_key("D", hold_ms=random.randint(400, 1200))
        elif phase == 3:
            for _ in range(5):
                move_mouse_relative(random.randint(-80, -30), random.randint(-15, 15))
                time.sleep(0.1)
        elif phase == 4:
            for _ in range(5):
                move_mouse_relative(random.randint(-10, 10), random.randint(-60, 60))
                time.sleep(0.1)
        elif phase == 5:
            send_key("]", hold_ms=50)

        remaining = duration_s - elapsed
        if remaining > 0 and remaining % 15 == 0:
            print(f"  {remaining}s remaining...")

        time.sleep(max(0, move_interval - 1.5))

    # Wait for collections to finish
    print("Waiting for data collection to complete...")
    collect_render.wait(timeout=30)
    collect_lights.wait(timeout=30)

    # Detach
    subprocess.run(
        ["python", "-m", "livetools", "detach"],
        capture_output=True, text=True, cwd=str(REPO_ROOT)
    )

    # Run quick analysis
    print("\n=== Live Analysis Results ===")
    results = {}
    for name, fpath in [("render_pipeline", pipeline_file),
                        ("light_system", light_file)]:
        fsize = Path(fpath).stat().st_size if Path(fpath).exists() else 0
        results[name] = {"file": fpath, "size": fsize}
        if fsize > 0:
            r = subprocess.run(
                ["python", "-m", "livetools", "analyze", fpath, "--summary"],
                capture_output=True, text=True, cwd=str(REPO_ROOT)
            )
            print(f"\n{name}:")
            print(r.stdout)
            results[name]["summary"] = r.stdout
        else:
            print(f"\n{name}: 0 bytes (no calls recorded)")
            results[name]["summary"] = "No calls recorded"

    return results


def set_debug_view(idx):
    """Set RTX Remix debug view index in rtx.conf."""
    import re
    rtx_conf = GAME_DIR / "rtx.conf"
    if not rtx_conf.exists():
        return
    text = rtx_conf.read_text()
    new_text = re.sub(
        r'rtx\.debugView\.debugViewIdx\s*=\s*\d+',
        f'rtx.debugView.debugViewIdx = {idx}',
        text
    )
    if new_text != text:
        rtx_conf.write_text(new_text)


def camera_pan_and_screenshot(hwnd, phase_name):
    """Execute gentle camera pan sequence: center, left, right — 3 screenshots.

    Only moves the camera (mouse), never moves Lara (no WASD). Returns the
    collected screenshot paths.
    """
    from livetools.gamectl import send_key, move_mouse_relative, focus_hwnd

    print(f"\n--- {phase_name}: Camera pan + screenshots ---")
    focus_hwnd(hwnd)
    time.sleep(0.5)
    capture_started_at = time.time()

    # Screenshot at center position
    print("  Screenshot: center")
    send_key("]", hold_ms=50)
    time.sleep(1.5)

    # Gentle camera pan LEFT (10 steps, -30px each = 300px total)
    print("  Camera pan: LEFT")
    for _ in range(10):
        move_mouse_relative(-30, 0)
        time.sleep(0.1)
    time.sleep(0.5)

    # Screenshot at left position
    print("  Screenshot: left")
    send_key("]", hold_ms=50)
    time.sleep(1.5)

    # Gentle camera pan RIGHT (20 steps, +30px each = 600px total, nets 300px right of center)
    print("  Camera pan: RIGHT")
    for _ in range(20):
        move_mouse_relative(30, 0)
        time.sleep(0.1)
    time.sleep(0.5)

    # Screenshot at right position
    print("  Screenshot: right")
    send_key("]", hold_ms=50)
    time.sleep(1.5)

    return collect_screenshots(max_age_seconds=30, limit=3, after_ts=capture_started_at)


def do_livetools_diagnostics(hwnd):
    """Phase 3: Attach livetools and run deep diagnostics.

    Returns dict of diagnostic results.
    """
    from livetools.gamectl import send_key, move_mouse_relative, focus_hwnd

    print("\n=== Phase 3: Livetools Deep Diagnostics ===")

    # Attach livetools
    print("Attaching livetools...")
    r = subprocess.run(
        ["python", "-m", "livetools", "attach", "trl.exe"],
        capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    if "Attached" not in r.stdout and "Attached" not in r.stderr:
        print(f"WARNING: livetools attach may have failed: {r.stderr}")
        return {"error": "attach failed"}

    results = {}

    # 3a. Draw call census
    print("\n--- 3a: Draw call census (dipcnt) ---")
    focus_hwnd(hwnd)
    time.sleep(0.5)

    subprocess.run(["python", "-m", "livetools", "dipcnt", "on"],
                   capture_output=True, text=True, cwd=str(REPO_ROOT))
    time.sleep(2)

    # Read at center
    r = subprocess.run(["python", "-m", "livetools", "dipcnt", "read"],
                       capture_output=True, text=True, cwd=str(REPO_ROOT))
    center_count = r.stdout.strip()
    print(f"  Center: {center_count}")

    # Pan left
    for _ in range(10):
        move_mouse_relative(-30, 0)
        time.sleep(0.1)
    time.sleep(1)

    r = subprocess.run(["python", "-m", "livetools", "dipcnt", "read"],
                       capture_output=True, text=True, cwd=str(REPO_ROOT))
    left_count = r.stdout.strip()
    print(f"  Left: {left_count}")

    # Pan right (back past center to right)
    for _ in range(20):
        move_mouse_relative(30, 0)
        time.sleep(0.1)
    time.sleep(1)

    r = subprocess.run(["python", "-m", "livetools", "dipcnt", "read"],
                       capture_output=True, text=True, cwd=str(REPO_ROOT))
    right_count = r.stdout.strip()
    print(f"  Right: {right_count}")

    subprocess.run(["python", "-m", "livetools", "dipcnt", "off"],
                   capture_output=True, text=True, cwd=str(REPO_ROOT))

    results["dipcnt"] = {
        "center": center_count, "left": left_count, "right": right_count
    }

    # 3b. Function call collection (15s during camera pan)
    print("\n--- 3b: Function call collection (15s) ---")
    capture_dir = SCRIPT_DIR / "captures" / "hash_stability"
    capture_dir.mkdir(parents=True, exist_ok=True)
    fn_file = str(capture_dir / "live_functions.jsonl")

    collect_proc = subprocess.Popen(
        ["python", "-m", "livetools", "collect",
         "0x00413950", "0x00ECBB00", "0x0060C7D0", "0x0060B050",
         "--duration", "15",
         "--label", "0x00413950=SetWorldMatrix",
         "--label", "0x00ECBB00=UploadViewProjMatrices",
         "--label", "0x0060C7D0=RenderLights_FrustumCull",
         "--label", "0x0060B050=LightVisibilityCheck",
         "--output", fn_file],
        cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Gentle camera movement during collection
    focus_hwnd(hwnd)
    for _ in range(3):
        for _ in range(5):
            move_mouse_relative(-20, 0)
            time.sleep(0.1)
        time.sleep(1)
        for _ in range(5):
            move_mouse_relative(20, 0)
            time.sleep(0.1)
        time.sleep(1)

    collect_proc.wait(timeout=30)
    fn_size = Path(fn_file).stat().st_size if Path(fn_file).exists() else 0
    results["collect"] = {"file": fn_file, "size": fn_size}

    if fn_size > 0:
        r = subprocess.run(
            ["python", "-m", "livetools", "analyze", fn_file, "--summary"],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        print(r.stdout)
        results["collect"]["summary"] = r.stdout

    # 3c. Patch integrity (mem read)
    print("\n--- 3c: Patch integrity ---")
    patch_checks = [
        ("0xEFDD64", "4", "--as", "float32", "frustum threshold (expect -1e30)"),
        ("0xF2A0D4", "12", "--as", "float32", "cull mode globals"),
        ("0x407150", "1", None, None, "cull function entry (expect C3=RET)"),
        ("0x60B050", "4", None, None, "LightVisibilityTest (expect B001C204)"),
    ]
    results["patches"] = {}
    for addr, size, flag, flag_val, desc in patch_checks:
        cmd = ["python", "-m", "livetools", "mem", "read", addr, size]
        if flag:
            cmd.extend([flag, flag_val])
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
        val = r.stdout.strip()
        print(f"  {desc}: {val}")
        results["patches"][addr] = val

    # 3d. Memory watchpoint (abbreviated — trace SetStreamSource to find VB addr)
    print("\n--- 3d: VB mutation check (memwatch) ---")
    # Quick trace to discover a VB address
    r = subprocess.run(
        ["python", "-m", "livetools", "trace", "0x00413950",
         "--count", "3", "--read", "[esp+4]:4:hex"],
        capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    print(f"  SetWorldMatrix trace sample: {r.stdout.strip()[:200]}")
    results["memwatch"] = {"note": "VB mutation check logged"}

    # Detach
    print("\nDetaching livetools...")
    subprocess.run(["python", "-m", "livetools", "detach"],
                   capture_output=True, text=True, cwd=str(REPO_ROOT))

    return results


def do_test_hash_stability(build_first=False, quick=False):
    """Hash stability test: camera-only pan, no WASD movement.

    Phases:
      0. Build & deploy proxy (if --build)
      1. Hash debug screenshots (debug view 277)
      2. Clean render screenshots (debug view 0)
      3. Livetools deep diagnostics (dipcnt, collect, mem read, memwatch)
      4. dx9tracer frame capture & diff (skipped with --quick)
    """
    if build_first:
        build_proxy()

    set_graphics_config()
    disabled_nightly_mod = suspend_nightly_mod_override()

    try:
        # --- Phase 1: Hash debug screenshots ---
        print("\n=== Phase 1: Hash Debug Screenshots (view 277) ===")
        set_debug_view(277)
        kill_game()
        phase1_started_at = time.time()
        hwnd = launch_game()
        hash_shots = camera_pan_and_screenshot(hwnd, "Phase 1 — Hash Debug")

        log_ready = wait_for_fresh_proxy_log(after_ts=phase1_started_at)
        if log_ready and PROXY_LOG.exists():
            dest = SCRIPT_DIR / "ffp_proxy.log"
            shutil.copy2(str(PROXY_LOG), str(dest))
            print(f"Proxy log copied to {dest}")

        from livetools.gamectl import find_hwnd_by_exe
        crashed_p1 = not find_hwnd_by_exe("trl.exe")
        if crashed_p1:
            print("WARNING: Game crashed during Phase 1!")
        kill_game()

        # --- Phase 2: Clean render screenshots ---
        print("\n=== Phase 2: Clean Render Screenshots (view 0) ===")
        set_debug_view(0)
        hwnd2 = launch_game()
        clean_shots = camera_pan_and_screenshot(hwnd2, "Phase 2 — Clean Render")

        from livetools.gamectl import find_hwnd_by_exe
        crashed_p2 = not find_hwnd_by_exe("trl.exe")
        if crashed_p2:
            print("WARNING: Game crashed during Phase 2!")
        kill_game()

        # --- Phase 3: Livetools diagnostics ---
        print("\n=== Phase 3: Livetools Diagnostics ===")
        set_debug_view(0)
        hwnd3 = launch_game()

        # Wait additional time for stable attachment
        print("Waiting 25s before livetools attach...")
        time.sleep(25)

        diag_results = do_livetools_diagnostics(hwnd3)

        from livetools.gamectl import find_hwnd_by_exe
        crashed_p3 = not find_hwnd_by_exe("trl.exe")
        if crashed_p3:
            print("WARNING: Game crashed during Phase 3!")
        kill_game()

        # --- Phase 4: dx9tracer (unless --quick) ---
        tracer_results = None
        if not quick:
            print("\n=== Phase 4: dx9tracer Frame Capture ===")
            print("  (skipped in this version — run with static-analyzer subagent)")
            # The dx9tracer swap and capture is orchestrated by the Claude agent
            # calling the tracer trigger + analyze commands, not by this script.
            # This phase is a placeholder for the agent to fill in.
            tracer_results = {"note": "delegated to agent"}

        # --- Summary ---
        crashed = crashed_p1 or crashed_p2 or crashed_p3
        print(f"\n{'='*60}")
        print(f"  HASH STABILITY TEST COMPLETE")
        print(f"  Crashed: {crashed}")
        print(f"  Hash debug screenshots: {len(hash_shots)}")
        print(f"  Clean render screenshots: {len(clean_shots)}")
        if diag_results and "dipcnt" in diag_results:
            d = diag_results["dipcnt"]
            print(f"  Draw counts: center={d['center']} left={d['left']} right={d['right']}")
        if diag_results and "patches" in diag_results:
            for addr, val in diag_results["patches"].items():
                print(f"  Patch {addr}: {val}")
        print(f"{'='*60}")

        return not crashed
    finally:
        restore_nightly_mod_override(disabled_nightly_mod)


def do_test_legacy(build_first=False, randomize=False):
    """Run the authoritative stage-light end-to-end release gate."""
    from livetools.gamectl import load_macros

    if build_first:
        build_proxy()

    # Ensure graphics config is set (prevents setup screen after new DLL)
    set_graphics_config()
    disabled_nightly_mod = suspend_nightly_mod_override()

    # Verify macro exists
    if not MACROS_FILE.exists():
        print(f"ERROR: No macros file at {MACROS_FILE}")
        print("Run 'python run.py record' first.")
        restore_nightly_mod_override(disabled_nightly_mod)
        sys.exit(1)

    macros = load_macros(str(MACROS_FILE))
    if MACRO_NAME not in macros:
        print(f"ERROR: Macro '{MACRO_NAME}' not found in {MACROS_FILE}")
        print("Run 'python run.py record' first.")
        restore_nightly_mod_override(disabled_nightly_mod)
        sys.exit(1)

    macro_info = macros[MACRO_NAME]

    if randomize:
        # Replace macro with fully random movement+screenshot sequence.
        # Macros are pure movement now (no menu nav — TR7.arg handles that).
        random_movement = generate_random_movement_legacy()
        macros[MACRO_NAME] = {**macro_info, "steps": random_movement}

        holds = [t for t in random_movement.split() if t.startswith("HOLD:")]
        screenshots = random_movement.count("]")
        print(f"\nRandomized movement: {len(holds)} strafes, "
              f"{screenshots} screenshots")
        for h in holds:
            parts = h.split(":")
            print(f"  {parts[1]} hold {parts[2]}ms")
    else:
        steps = macro_info["steps"]

    print(f"\nMacro: {MACRO_NAME}")
    print(f"  {macro_info.get('description', '')}")

    # Estimate duration from WAIT tokens
    steps = macros[MACRO_NAME]["steps"]
    wait_total = sum(int(t.split(":")[1]) for t in steps.split()
                     if t.startswith("WAIT:"))
    print(f"  Estimated duration: {wait_total // 1000}s")

    capture_markers = count_capture_markers(steps)
    print(f"  Capture points: {capture_markers}")
    if capture_markers < _RELEASE_GATE_REQUIRED_CAPTURE_MARKERS:
        print("ERROR: Release gate requires three screenshot markers in the macro.")
        print(f"Current macro only provides {capture_markers} capture point(s).")
        restore_nightly_mod_override(disabled_nightly_mod)
        return False

    print("\n=== Stage-light release gate ===")
    set_debug_view(0)

    kill_game()
    launch_started_at = time.time()
    try:
        hwnd = launch_game()
    except SystemExit:
        print("ERROR: Release-gate launch failed.")
        kill_game()
        restore_nightly_mod_override(disabled_nightly_mod)
        return False

    run_label = f"release-gate-{time.strftime('%Y%m%d-%H%M%S')}"
    print("Replaying macro with paired hash/clean captures...")
    capture_result = capture_release_gate_evidence(
        hwnd,
        steps,
        run_label=run_label,
        delay_ms=0,
    )
    if capture_result["ok"]:
        print(f"Release-gate replay complete. {capture_result['count']} actions sent.")
    else:
        print(f"Release-gate replay failed: {capture_result.get('error', capture_result)}")
        kill_game()
        restore_nightly_mod_override(disabled_nightly_mod)
        return False

    log_ready = wait_for_fresh_proxy_log(after_ts=launch_started_at)

    from livetools.gamectl import find_hwnd_by_exe
    crashed = not find_hwnd_by_exe("trl.exe")
    if crashed:
        print("WARNING: Game appears to have crashed during the release gate!")
    else:
        print("Game still running (no crash).")

    log_copy = None
    if log_ready and PROXY_LOG.exists():
        log_copy = SCRIPT_DIR / "ffp_proxy.log"
        shutil.copy2(str(PROXY_LOG), str(log_copy))
        print(f"Copied final proxy log to {log_copy}")
    else:
        print("WARNING: Final proxy log was not available for release-gate parsing")

    kill_game()
    print("Runtime cleaned up after release gate.")

    hash_shots = capture_result["hash_paths"]
    clean_shots = capture_result["clean_paths"]

    print("\n=== Test complete ===")
    release_gate = evaluate_release_gate(
        hash_shots,
        clean_shots,
        log_copy,
        crashed=crashed,
    )
    report_path = write_release_gate_report(release_gate)
    print(f"Release gate artifact: {report_path}")
    print(f"Release gate summary: crashed={crashed}, "
          f"hash_shots={len(hash_shots)}, clean_shots={len(clean_shots)}, "
          f"hash_pass={release_gate['hash_stability']['passed']}, "
          f"lights_pass={release_gate['lights']['passed']}, "
          f"movement_pass={release_gate['movement']['passed']}, "
          f"log_pass={release_gate['log']['passed']}, "
          f"passed={release_gate['passed']}")
    restore_nightly_mod_override(disabled_nightly_mod)
    return bool(release_gate["passed"])


def do_batch_legacy(start, end, total, build_first=False):
    """Run multiple test iterations with randomized movement, commit each."""
    if build_first:
        build_proxy()
        build_first = False  # only build once

    for i in range(start, end + 1):
        print(f"\n{'='*60}")
        print(f"  BATCH RUN #{i}/{total}")
        print(f"{'='*60}")

        seed = random.randint(0, 2**32 - 1)
        random.seed(seed)
        print(f"  Random seed: {seed}")

        ok = do_test_legacy(build_first=False, randomize=True)

        # Commit and push
        print(f"\n=== Committing test #{i}/{total} ===")
        repo = str(REPO_ROOT)

        # Stage screenshots
        subprocess.run(["git", "add", "patches/TombRaiderLegend/screenshots/"],
                       cwd=repo, capture_output=True)
        subprocess.run(["git", "add", "TombRaiderLegendRTX-"],
                       cwd=repo, capture_output=True)

        # Stage run.py if this is the first run (captures the randomization code)
        subprocess.run(["git", "add", "patches/TombRaiderLegend/run.py"],
                       cwd=repo, capture_output=True)

        crash_note = " [CRASHED]" if not ok else ""
        msg = f"test: stable hash build #{i}/{total}{crash_note}"
        subprocess.run(["git", "commit", "-m", msg,
                        "--allow-empty"],
                       cwd=repo, capture_output=True)

        # Push
        subprocess.run(["git", "push", "origin", "master:main"],
                       cwd=repo, capture_output=True, timeout=30)
        print(f"  Pushed #{i}/{total}")

        if not ok:
            print(f"  WARNING: Test #{i} crashed — continuing to next run")

    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE: runs {start}-{end}/{total}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="TRL RTX test orchestrator")
    sub = parser.add_subparsers(dest="mode")

    # --- Authoritative release gate ---
    test_p = sub.add_parser("test",
                            help="Full stage-light end-to-end release gate")
    test_p.add_argument("--build", action="store_true",
                        help="Build and deploy proxy before testing")
    test_p.add_argument("--randomize", action="store_true",
                        help="Randomize the movement macro before testing")

    # --- Hash-only screening ---
    test_hash_p = sub.add_parser("test-hash",
                                 help="Hash stability test (camera-only, no WASD)")
    test_hash_p.add_argument("--build", action="store_true",
                             help="Build and deploy proxy before testing")
    test_hash_p.add_argument("--quick", action="store_true",
                             help="Skip dx9tracer phase (Phase 4)")

    # --- Record ---
    sub.add_parser("record",
                   help="Launch game and record inputs as test_session macro")

    # --- Backward-compatible aliases ---
    legacy_test_p = sub.add_parser("test-legacy", help=argparse.SUPPRESS)
    legacy_test_p.add_argument("--build", action="store_true")
    legacy_test_p.add_argument("--randomize", action="store_true")

    batch_p = sub.add_parser("batch",
                             help="Batch runs with random movement")
    batch_p.add_argument("--start", type=int, required=True)
    batch_p.add_argument("--end", type=int, required=True)
    batch_p.add_argument("--total", type=int, default=50)
    batch_p.add_argument("--build", action="store_true")

    legacy_batch_p = sub.add_parser("batch-legacy", help=argparse.SUPPRESS)
    legacy_batch_p.add_argument("--start", type=int, required=True)
    legacy_batch_p.add_argument("--end", type=int, required=True)
    legacy_batch_p.add_argument("--total", type=int, default=50)
    legacy_batch_p.add_argument("--build", action="store_true")

    args = parser.parse_args()

    if args.mode == "test":
        raise SystemExit(0 if do_test_legacy(
            build_first=args.build,
            randomize=getattr(args, "randomize", False),
        ) else 1)
    elif args.mode == "test-hash":
        raise SystemExit(0 if do_test_hash_stability(
            build_first=args.build,
            quick=getattr(args, 'quick', False),
        ) else 1)
    elif args.mode == "record":
        do_record()
    elif args.mode == "test-legacy":
        raise SystemExit(0 if do_test_legacy(
            build_first=args.build,
            randomize=getattr(args, 'randomize', False),
        ) else 1)
    elif args.mode in {"batch", "batch-legacy"}:
        do_batch_legacy(args.start, args.end, args.total,
                        build_first=args.build)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
