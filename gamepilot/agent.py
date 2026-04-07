"""Main GamePilot agent — vision-driven game control loop."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
GAME_DIR = REPO_ROOT / "Tomb Raider Legend"

sys.path.insert(0, str(REPO_ROOT))

from gamepilot.capture import capture, image_to_bytes
from gamepilot.vision import GameState, classify_state, decide_action
from gamepilot.controller import execute_action
from gamepilot.states.handlers import pre_process
from livetools.gamectl import find_hwnd_by_exe

MAX_STEPS = 200
CAPTURE_INTERVAL = 0.5  # seconds between captures when idle


def _find_or_launch_game() -> int | None:
    """Find the TRL game window, or launch it if not running.

    Returns hwnd or None.
    """
    hwnd = find_hwnd_by_exe("trl.exe")
    if hwnd:
        print(f"[agent] Found running game (hwnd={hwnd})")
        return hwnd

    print("[agent] Game not running, launching...")
    launcher = GAME_DIR / "NvRemixLauncher32.exe"
    game_exe = GAME_DIR / "trl.exe"

    if launcher.exists():
        subprocess.Popen([str(launcher), str(game_exe)], cwd=str(GAME_DIR))
    else:
        subprocess.Popen([str(game_exe)], cwd=str(GAME_DIR))

    # Wait for window
    for _ in range(90):
        hwnd = find_hwnd_by_exe("trl.exe")
        if hwnd:
            print(f"[agent] Game window found (hwnd={hwnd})")
            return hwnd
        time.sleep(1)

    print("[agent] ERROR: Game did not start within 90s")
    return None


def run_agent(
    goal: str,
    launch: bool = True,
    max_steps: int = MAX_STEPS,
    prefer_nvidia: bool = False,
    verbose: bool = True,
) -> dict:
    """Run the vision-controlled game agent.

    Args:
        goal: Natural language goal (e.g., "navigate to gameplay and open Remix menu").
        launch: If True, launch the game if not already running.
        max_steps: Maximum number of action steps before giving up.
        prefer_nvidia: Always use NVIDIA capture instead of GDI.
        verbose: Print step-by-step progress.

    Returns:
        Result dict with "success", "steps_taken", "final_state", "history".
    """
    print("=" * 60)
    print(f"  GAMEPILOT — Vision-Controlled Game Agent")
    print(f"  Goal: {goal}")
    print("=" * 60)

    # Step 1: Find or launch game
    if launch:
        hwnd = _find_or_launch_game()
    else:
        hwnd = find_hwnd_by_exe("trl.exe")

    if not hwnd:
        return {"success": False, "error": "Game not running", "steps_taken": 0, "history": []}

    history: list[dict] = []
    consecutive_waits = 0
    last_state = GameState.UNKNOWN

    for step in range(max_steps):
        # Check game is still alive
        hwnd_check = find_hwnd_by_exe("trl.exe")
        if not hwnd_check:
            print(f"\n[agent] Step {step}: Game window lost — crashed or closed")
            return {
                "success": False,
                "error": "Game window lost",
                "steps_taken": step,
                "final_state": GameState.CRASHED.value,
                "history": history,
            }
        hwnd = hwnd_check

        # Capture screenshot
        # Use NVIDIA for gameplay/remix states where we need Remix-rendered frames
        use_nvidia = prefer_nvidia or last_state in (GameState.GAMEPLAY, GameState.REMIX_MENU)
        img = capture(hwnd, prefer_nvidia=use_nvidia)

        if img is None:
            if verbose:
                print(f"  Step {step}: Capture failed, retrying with NVIDIA...")
            img = capture(hwnd, prefer_nvidia=True)
            if img is None:
                print(f"  Step {step}: All capture methods failed")
                time.sleep(2)
                continue

        img_bytes = image_to_bytes(img)

        # Classify state
        state, details = classify_state(img_bytes)

        if verbose:
            state_changed = state != last_state
            marker = " ***" if state_changed else ""
            print(f"\n  Step {step}: State={state.value}{marker}")
            print(f"    Details: {details}")

        last_state = state

        # Pre-process: some states are handled without Claude
        pre_action = pre_process(state, hwnd)
        if pre_action:
            if verbose:
                print(f"    Auto: {pre_action.get('reasoning', '')}")
            result = execute_action(hwnd, pre_action)
            history.append(pre_action)

            if state == GameState.LOADING:
                consecutive_waits += 1
                if consecutive_waits > 20:
                    print("[agent] Loading screen persisted for 60s, may be stuck")
            else:
                consecutive_waits = 0
            continue

        # Ask Claude for action
        action = decide_action(img_bytes, state, goal, history)

        if verbose:
            print(f"    Action: {action.get('action')} {action.get('args', {})}")
            print(f"    Reason: {action.get('reasoning', '')}")

        # Check for goal completion
        if action.get("action") == "goal_complete":
            print(f"\n  GOAL COMPLETE at step {step}")
            print(f"    Reason: {action.get('reasoning', '')}")
            return {
                "success": True,
                "steps_taken": step,
                "final_state": state.value,
                "history": history,
            }

        # Execute action
        result = execute_action(hwnd, action)
        action["result"] = result
        history.append(action)

        # Brief pause between steps
        time.sleep(CAPTURE_INTERVAL)

    print(f"\n[agent] Reached max steps ({max_steps}) without completing goal")
    return {
        "success": False,
        "error": "Max steps reached",
        "steps_taken": max_steps,
        "final_state": last_state.value,
        "history": history,
    }
