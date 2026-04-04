"""Differential frame capture — identify which draw calls vanish at distance."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GAME_DIR = REPO_ROOT / "Tomb Raider Legend"
TRACER_DLL = REPO_ROOT / "graphics" / "directx" / "dx9" / "tracer" / "bin" / "d3d9.dll"
TRACER_INI = REPO_ROOT / "graphics" / "directx" / "dx9" / "tracer" / "bin" / "proxy.ini"
MACROS_FILE = Path(__file__).resolve().parent / "macros.json"
OUTPUT_DIR = Path(__file__).resolve().parent / "diagnostic_captures"

sys.path.insert(0, str(REPO_ROOT))


@dataclass
class MissingDraw:
    """A draw call present in near-frame but absent in far-frame."""
    seq_near: int
    method: str
    prim_count: int
    vtx_decl_hash: str
    texture_ptrs: list[str]
    caller_addrs: list[str]
    start_vertex: int
    num_vertices: int


def _fingerprint_draw(rec: dict) -> str:
    """Create a stable fingerprint for a draw call based on its geometry identity.

    Uses only geometry-shape properties that are stable across separate game
    launches. Texture pointers are excluded — they are process-specific
    addresses that differ between sessions.
    """
    args = rec.get("args", {})
    method = rec.get("method", "")

    parts = [
        method,
        str(args.get("PrimitiveType", "")),
        str(args.get("PrimitiveCount", "")),
        str(args.get("NumVertices", "")),
        str(args.get("StartIndex", "")),
    ]

    # Vertex declaration elements describe the vertex format, not a pointer
    vtx_decl = rec.get("vertex_decl_elements", "")
    if vtx_decl:
        parts.append(str(vtx_decl))

    return "|".join(parts)


def _extract_draw_calls(jsonl_path: Path) -> list[dict]:
    """Extract all draw calls from a JSONL frame capture."""
    draws = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            method = rec.get("method", "")
            if method in ("DrawIndexedPrimitive", "DrawPrimitive"):
                draws.append(rec)
    return draws


def _deploy_tracer() -> Path | None:
    """Deploy the dx9 tracer DLL to the game directory. Returns backup path."""
    from autopatch.safety import backup_game_dll

    if not TRACER_DLL.exists():
        print(f"[diagnose] ERROR: Tracer DLL not found: {TRACER_DLL}")
        return None

    backup_path = backup_game_dll()
    shutil.copy2(TRACER_DLL, GAME_DIR / "d3d9.dll")

    # Write tracer config
    ini_content = "[Trace]\nCaptureFrames=1\nCaptureInit=0\n"
    (GAME_DIR / "proxy.ini").write_text(ini_content)

    print(f"[diagnose] Deployed tracer DLL to {GAME_DIR.name}/")
    return backup_path


def _restore_proxy() -> None:
    """Restore the proxy DLL after tracer capture."""
    from autopatch.safety import restore_game_dll
    restore_game_dll()

    # Restore proxy.ini from proxy source
    proxy_ini = REPO_ROOT / "proxy" / "proxy.ini"
    if proxy_ini.exists():
        shutil.copy2(proxy_ini, GAME_DIR / "proxy.ini")
    print("[diagnose] Restored proxy DLL")


def _launch_and_capture(macro_name: str) -> Path | None:
    """Launch game, run macro, trigger capture, return JSONL path."""
    from livetools.gamectl import find_hwnd_by_exe, send_keys, load_macros

    game_exe = GAME_DIR / "trl.exe"

    # Kill any existing game instance
    subprocess.run(["taskkill", "/f", "/im", "trl.exe"], capture_output=True)
    time.sleep(2)

    # Clean previous capture files
    for f in ["dxtrace_capture.trigger", "dxtrace_frame.jsonl", "dxtrace_progress.txt"]:
        p = GAME_DIR / f
        if p.exists():
            p.unlink()

    # Launch trl.exe directly — tracer captures native D3D9 calls,
    # Remix launcher is not needed and would interfere.
    print(f"[diagnose] Launching game for '{macro_name}' capture...")
    subprocess.Popen([str(game_exe)], cwd=str(GAME_DIR))

    # Wait for game window, handling the setup dialog that appears when
    # the game detects a different d3d9.dll (tracer vs proxy).
    hwnd = None
    setup_dismissed = False
    for i in range(90):
        # Try dismissing setup dialog first (game shows it before main window)
        if not setup_dismissed:
            try:
                sys.path.insert(0, str(REPO_ROOT / "patches" / "TombRaiderLegend"))
                from run import dismiss_setup_dialog
                if dismiss_setup_dialog():
                    setup_dismissed = True
                    print("[diagnose] Setup dialog dismissed")
            except Exception:
                pass

        hwnd = find_hwnd_by_exe("trl.exe")
        if hwnd and setup_dismissed:
            break
        # After dialog is dismissed, the main window may take a moment
        if hwnd and i > 10:
            break
        time.sleep(1)

    if not hwnd:
        print("[diagnose] ERROR: Game window not found after 90s")
        return None

    print("[diagnose] Game window found. Waiting 25s for level to load...")
    time.sleep(25)

    # Run position macro
    macros = load_macros(str(MACROS_FILE))
    if macro_name in macros:
        steps = macros[macro_name]["steps"]
        print(f"[diagnose] Running macro '{macro_name}' ({len(steps)} steps)...")
        send_keys(hwnd, " ".join(steps), delay_ms=0)
    else:
        print(f"[diagnose] WARNING: Macro '{macro_name}' not found, using raw position")

    time.sleep(2)

    # Trigger capture
    trigger_path = GAME_DIR / "dxtrace_capture.trigger"
    trigger_path.write_text("frames=1\n")
    print("[diagnose] Capture triggered, waiting for completion...")

    # Wait for capture to complete
    jsonl_path = GAME_DIR / "dxtrace_frame.jsonl"
    for _ in range(60):
        time.sleep(1)
        if jsonl_path.exists() and jsonl_path.stat().st_size > 1000:
            # Check if trigger file was consumed
            if not trigger_path.exists():
                break
    time.sleep(2)

    # Kill game
    subprocess.run(["taskkill", "/f", "/im", "trl.exe"], capture_output=True)
    time.sleep(2)

    if not jsonl_path.exists():
        print("[diagnose] ERROR: No capture file produced")
        return None

    print(f"[diagnose] Capture complete: {jsonl_path.stat().st_size / 1024:.1f} KB")
    return jsonl_path


def diff_frames(near_jsonl: Path, far_jsonl: Path) -> list[MissingDraw]:
    """Diff two frame captures to find draws present near but absent far.

    Args:
        near_jsonl: JSONL from near-stage capture.
        far_jsonl: JSONL from far-stage capture.

    Returns:
        List of draw calls that appear in near but not in far.
    """
    near_draws = _extract_draw_calls(near_jsonl)
    far_draws = _extract_draw_calls(far_jsonl)

    # Build fingerprint sets
    far_fingerprints = {_fingerprint_draw(d) for d in far_draws}

    missing = []
    for draw in near_draws:
        fp = _fingerprint_draw(draw)
        if fp not in far_fingerprints:
            args = draw.get("args", {})
            missing.append(MissingDraw(
                seq_near=draw.get("seq", 0),
                method=draw.get("method", ""),
                prim_count=args.get("PrimitiveCount", 0),
                vtx_decl_hash=str(draw.get("vertex_decl_elements", "")),
                texture_ptrs=[str(t) for t in draw.get("textures", [])[:4]],
                caller_addrs=[hex(a) for a in draw.get("backtrace", [])[:5]],
                start_vertex=args.get("StartVertex", 0),
                num_vertices=args.get("NumVertices", 0),
            ))

    print(f"[diagnose] Near draws: {len(near_draws)}, Far draws: {len(far_draws)}, "
          f"Missing at distance: {len(missing)}")
    return missing


def run_diagnostic() -> dict:
    """Run the full diagnostic: deploy tracer, capture near/far, diff, restore.

    Returns:
        Dictionary with diagnostic results including missing draws and their
        caller addresses.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Deploy tracer
    backup = _deploy_tracer()
    if backup is None:
        return {"error": "Failed to deploy tracer"}

    try:
        # Step 2: Near-stage capture
        near_jsonl = _launch_and_capture("near_stage")
        if near_jsonl:
            near_dest = OUTPUT_DIR / "near_frame.jsonl"
            shutil.copy2(near_jsonl, near_dest)
            near_jsonl.unlink()
        else:
            return {"error": "Near capture failed"}

        # Step 3: Far-stage capture
        far_jsonl = _launch_and_capture("far_stage")
        if far_jsonl:
            far_dest = OUTPUT_DIR / "far_frame.jsonl"
            shutil.copy2(far_jsonl, far_dest)
            far_jsonl.unlink()
        else:
            return {"error": "Far capture failed"}

    finally:
        # Step 4: Restore proxy
        _restore_proxy()

    # Step 5: Diff
    missing = diff_frames(near_dest, far_dest)

    # Collect unique caller addresses from missing draws
    caller_set: set[str] = set()
    for m in missing:
        caller_set.update(m.caller_addrs)

    result = {
        "near_frame": str(near_dest),
        "far_frame": str(far_dest),
        "total_missing_draws": len(missing),
        "missing_draws": [asdict(m) for m in missing[:50]],  # cap for readability
        "unique_caller_addrs": sorted(caller_set),
    }

    # Save diagnostic report
    report_path = OUTPUT_DIR / "diagnostic_report.json"
    report_path.write_text(json.dumps(result, indent=2))
    print(f"[diagnose] Report saved: {report_path}")

    return result
