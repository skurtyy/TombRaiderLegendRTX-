"""State-specific logic that runs before/after Claude's action decision.

Each handler can:
- Pre-process: handle the state without calling Claude (e.g., auto-dismiss setup dialog)
- Post-process: react to action results (e.g., detect goal completion)
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gamepilot.vision import GameState  # noqa: E402


def handle_setup_dialog() -> dict | None:
    """Auto-dismiss the TRL setup dialog using existing Win32 automation.

    Returns an action dict if handled (no Claude call needed), or None
    to fall through to Claude.
    """
    try:
        sys.path.insert(0, str(REPO_ROOT / "patches" / "TombRaiderLegend"))
        from run import dismiss_setup_dialog
        if dismiss_setup_dialog():
            return {
                "action": "wait",
                "args": {"ms": 3000},
                "reasoning": "Setup dialog auto-dismissed, waiting for game to proceed",
            }
    except Exception as e:
        print(f"[states] Setup dialog dismiss failed: {e}")

    return None


def handle_crashed(hwnd: int) -> dict:
    """Handle a crashed/missing game window."""
    return {
        "action": "wait",
        "args": {"ms": 2000},
        "reasoning": "Game appears crashed or unresponsive",
    }


def pre_process(state: GameState, hwnd: int) -> dict | None:
    """Run state-specific logic before calling Claude.

    Returns an action dict to execute without calling Claude,
    or None to proceed with the normal Claude decision flow.
    """
    if state == GameState.SETUP_DIALOG:
        return handle_setup_dialog()

    if state == GameState.CRASHED:
        return handle_crashed(hwnd)

    if state == GameState.LOADING:
        # No need to call Claude for loading screens
        return {
            "action": "wait",
            "args": {"ms": 3000},
            "reasoning": "Loading screen detected, waiting",
        }

    return None
