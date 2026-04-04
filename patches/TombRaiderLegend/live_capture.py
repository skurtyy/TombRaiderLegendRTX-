"""Tomb Raider Legend — Live capture script.

Launches the game, waits for it to stabilize, then triggers a dx9tracer
frame capture of ~2 minutes (7200 frames at 60fps). The tracer is a DLL
proxy that intercepts all 119 IDirect3DDevice9 methods, capturing every
call with arguments, backtraces, matrix data, shader bytecodes, etc.

Output: JSONL file in the game directory, copied to traces/.

Usage:
    python patches/TombRaiderLegend/live_capture.py
    python patches/TombRaiderLegend/live_capture.py --frames 300
    python patches/TombRaiderLegend/live_capture.py --skip-launch
"""

import argparse
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
GAME_DIR = REPO_ROOT / "Tomb Raider Legend"
TRACES_DIR = SCRIPT_DIR / "traces"

TRIGGER_FILE = GAME_DIR / "dxtrace_capture.trigger"
PROGRESS_FILE = GAME_DIR / "dxtrace_progress.txt"
JSONL_FILE = GAME_DIR / "dxtrace_frame.jsonl"
TRACER_LOG = GAME_DIR / "dxtrace_proxy.log"
TRACER_DLL_SRC = REPO_ROOT / "graphics" / "directx" / "dx9" / "tracer" / "bin" / "d3d9.dll"
TRACER_DLL_DST = GAME_DIR / "d3d9_trace.dll"

sys.path.insert(0, str(REPO_ROOT))


def launch_game():
    """Launch TRL and wait for it to be ready. Returns window hwnd."""
    from patches.TombRaiderLegend.run import launch_game as _launch, kill_game
    kill_game()
    return _launch()


def wait_for_capture(frames_target, timeout=300):
    """Monitor dx9tracer progress until capture completes or times out."""
    start = time.time()
    last_frame = -1
    last_report = 0

    while time.time() - start < timeout:
        if PROGRESS_FILE.exists():
            try:
                text = PROGRESS_FILE.read_text().strip()
                parts = text.split()
                if len(parts) >= 2:
                    frame = int(parts[0])
                    calls = int(parts[1])

                    if frame != last_frame:
                        elapsed = time.time() - start
                        fps = frame / elapsed if elapsed > 0 else 0
                        remaining = (frames_target - frame) / fps if fps > 0 else 0

                        if time.time() - last_report >= 5:
                            print(f"  [frame {frame}/{frames_target}] "
                                  f"{calls:,} calls captured "
                                  f"({fps:.0f} fps, ~{remaining:.0f}s remaining)")
                            last_report = time.time()

                        last_frame = frame

                    if frame >= frames_target:
                        print(f"  Capture complete: {frames_target} frames, "
                              f"{calls:,} calls")
                        return True
            except (ValueError, IOError):
                pass

        time.sleep(0.5)

    print(f"  WARNING: Capture timed out after {timeout}s")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="TRL live capture — dx9tracer frame capture of render pipeline")
    parser.add_argument("--frames", type=int, default=7200,
                        help="Number of frames to capture (default: 7200 = ~2min at 60fps)")
    parser.add_argument("--skip-launch", action="store_true",
                        help="Skip game launch (game already running)")
    parser.add_argument("--delay", type=int, default=30,
                        help="Seconds to wait after game loads before triggering (default: 30)")
    args = parser.parse_args()

    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Clean up previous capture files
    for f in [TRIGGER_FILE, PROGRESS_FILE, JSONL_FILE]:
        f.unlink(missing_ok=True)

    # ── Step 0: Deploy tracer DLL and patch proxy.ini ────────────────────
    if TRACER_DLL_SRC.exists():
        shutil.copy2(str(TRACER_DLL_SRC), str(TRACER_DLL_DST))
        print(f"Deployed {TRACER_DLL_DST.name} ({TRACER_DLL_SRC.stat().st_size // 1024} KB)")
    else:
        if not TRACER_DLL_DST.exists():
            print(f"ERROR: Tracer DLL not found at {TRACER_DLL_SRC}")
            print("Build it first: see graphics/directx/dx9/tracer/src/build.bat")
            sys.exit(1)

    # Patch proxy.ini to chain through tracer
    proxy_ini = GAME_DIR / "proxy.ini"
    if proxy_ini.exists():
        ini_text = proxy_ini.read_text()
        # Point FFP's Remix chain to tracer instead of d3d9_remix.dll
        if "DLLName=d3d9_remix.dll" in ini_text:
            ini_text = ini_text.replace("DLLName=d3d9_remix.dll", "DLLName=d3d9_trace.dll")
        # Add tracer sections if missing
        if "[Trace]" not in ini_text:
            ini_text += f"\n[Trace]\nCaptureFrames={args.frames}\nCaptureInit=1\n"
        if "DLL=d3d9_remix.dll" not in ini_text:
            ini_text = ini_text.replace("PreloadDLL=", "PreloadDLL=\nDLL=d3d9_remix.dll")
        proxy_ini.write_text(ini_text)
        print("Patched proxy.ini for tracer chain")

    # ── Step 1: Launch game ──────────────────────────────────────────────
    if not args.skip_launch:
        print("=== Launching Tomb Raider Legend ===")
        print("Chain: d3d9.dll (FFP) -> d3d9_trace.dll (tracer) -> d3d9_remix.dll (Remix)")
        hwnd = launch_game()
        print(f"Game ready (hwnd={hex(hwnd)})")
    else:
        print("=== Skipping launch (--skip-launch) ===")

    # ── Step 2: Wait for game to stabilize ───────────────────────────────
    print(f"\nWaiting {args.delay}s for game to fully stabilize...")
    print("  (Play through menus into gameplay before capture starts)")
    time.sleep(args.delay)

    # Check tracer loaded by looking for its log
    if TRACER_LOG.exists():
        print(f"  dx9tracer log found: {TRACER_LOG.name}")
    else:
        print("  WARNING: dx9tracer log not found — tracer may not be loaded")
        print("  Check that d3d9_trace.dll is deployed and proxy.ini chains correctly")

    # ── Step 3: Trigger capture ──────────────────────────────────────────
    est_seconds = args.frames / 60
    est_min = est_seconds / 60
    print(f"\n=== Triggering {args.frames}-frame capture ===")
    print(f"  Estimated duration: {est_min:.1f} minutes ({est_seconds:.0f}s at 60fps)")
    print(f"  Output: {JSONL_FILE.name}")
    print()

    # Write trigger file — tracer detects this on next Present() call
    TRIGGER_FILE.write_text(f"frames={args.frames}\n")
    print("  Trigger file written. Capture starting on next frame...")

    print(f"\n{'='*60}")
    print(f"  CAPTURING — keep the game focused and play normally")
    print(f"  Move around, interact, explore different areas")
    print(f"{'='*60}\n")

    # ── Step 4: Monitor progress ─────────────────────────────────────────
    timeout = int(est_seconds * 3) + 60  # generous timeout
    ok = wait_for_capture(args.frames, timeout=timeout)

    # ── Step 5: Copy results ─────────────────────────────────────────────
    if JSONL_FILE.exists():
        size_mb = JSONL_FILE.stat().st_size / (1024 * 1024)
        dest = TRACES_DIR / f"trl_capture_{timestamp}.jsonl"
        shutil.copy2(str(JSONL_FILE), str(dest))

        # Count records
        line_count = 0
        with open(dest) as f:
            for _ in f:
                line_count += 1

        print(f"\n=== Capture {'complete' if ok else 'partial'} ===")
        print(f"  Source:  {JSONL_FILE}")
        print(f"  Copied:  {dest}")
        print(f"  Size:    {size_mb:.1f} MB")
        print(f"  Records: {line_count:,}")

        # Copy tracer log too
        if TRACER_LOG.exists():
            log_dest = TRACES_DIR / f"trl_capture_{timestamp}_proxy.log"
            shutil.copy2(str(TRACER_LOG), str(log_dest))
            print(f"  Log:     {log_dest}")

        print(f"\nAnalyze with:")
        print(f"  python -m graphics.directx.dx9.tracer analyze {dest} --summary")
        print(f"  python -m graphics.directx.dx9.tracer analyze {dest} --draw-calls")
        print(f"  python -m graphics.directx.dx9.tracer analyze {dest} --render-passes")
        print(f"  python -m graphics.directx.dx9.tracer analyze {dest} --shader-map")
        print(f"  python -m graphics.directx.dx9.tracer analyze {dest} --matrix-flow")
        print(f"  python -m graphics.directx.dx9.tracer analyze {dest} --state-snapshot 0")
    else:
        print(f"\nERROR: No capture output found at {JSONL_FILE}")
        print("Possible causes:")
        print("  - d3d9_trace.dll not loaded (check proxy.ini chain)")
        print("  - Game window not focused during capture")
        print("  - Game crashed before capture started")

    # Clean up trigger/progress files
    TRIGGER_FILE.unlink(missing_ok=True)
    PROGRESS_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
