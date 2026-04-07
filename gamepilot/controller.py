"""Action execution — translates Claude's action dicts into Win32 SendInput calls."""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from livetools.gamectl import (
    send_key, send_keys, focus_hwnd, click_at, move_mouse_relative,
)


def execute_action(hwnd: int, action: dict) -> dict:
    """Execute a single action dict returned by the vision model.

    Args:
        hwnd: Game window handle.
        action: Dict with "action" and "args" keys.

    Returns:
        Result dict with "ok" and any additional info.
    """
    action_type = action.get("action", "wait")
    args = action.get("args", {})

    focus_hwnd(hwnd)

    if action_type == "key":
        name = args.get("name", "RETURN")
        result = send_key(name, hold_ms=80)
        return result

    elif action_type == "hold":
        name = args.get("name", "W")
        ms = args.get("ms", 500)
        result = send_key(name, hold_ms=ms)
        return result

    elif action_type == "click":
        x = args.get("x", 0)
        y = args.get("y", 0)
        result = click_at(hwnd, x, y)
        return result

    elif action_type == "mouse_move":
        dx = args.get("dx", 0)
        dy = args.get("dy", 0)
        result = move_mouse_relative(dx, dy)
        return result

    elif action_type == "alt_x":
        # Alt+X to toggle Remix menu — hold Alt, tap X, release Alt
        from livetools.gamectl import _make_key_input, INPUT, VK_MAP
        import ctypes
        user32 = ctypes.windll.user32

        vk_alt = VK_MAP["ALT"]
        vk_x = VK_MAP["X"]

        alt_dn = _make_key_input(vk_alt, up=False)
        x_dn = _make_key_input(vk_x, up=False)
        x_up = _make_key_input(vk_x, up=True)
        alt_up = _make_key_input(vk_alt, up=True)

        arr = (INPUT * 4)(alt_dn, x_dn, x_up, alt_up)
        user32.SendInput(4, arr, ctypes.sizeof(INPUT))
        time.sleep(0.3)
        return {"ok": True, "action": "alt_x"}

    elif action_type == "wait":
        ms = args.get("ms", 1000)
        time.sleep(ms / 1000.0)
        return {"ok": True, "action": "wait", "ms": ms}

    elif action_type == "goal_complete":
        return {"ok": True, "action": "goal_complete", "complete": True}

    else:
        print(f"[controller] Unknown action type: {action_type}")
        time.sleep(1)
        return {"ok": False, "error": f"Unknown action: {action_type}"}
