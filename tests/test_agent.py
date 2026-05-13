import sys
from unittest.mock import MagicMock

# Only mock livetools.gamectl because it uses ctypes.windll which fails on Linux.
sys.modules["livetools.gamectl"] = MagicMock()

# fmt: off
from gamepilot.agent import _detect_stuck # noqa: E402
# fmt: on


def test_detect_stuck_empty_history():
    assert not _detect_stuck([], threshold=3)


def test_detect_stuck_below_threshold():
    history = [
        {"action": "move", "args": {"dir": "up"}},
        {"action": "move", "args": {"dir": "up"}},
    ]
    assert not _detect_stuck(history, threshold=3)


def test_detect_stuck_exact_threshold_match():
    history = [
        {"action": "move", "args": {"dir": "up"}},
        {"action": "move", "args": {"dir": "up"}},
        {"action": "move", "args": {"dir": "up"}},
    ]
    assert _detect_stuck(history, threshold=3)


def test_detect_stuck_above_threshold_match():
    history = [
        {"action": "jump", "args": {}},
        {"action": "move", "args": {"dir": "up"}},
        {"action": "move", "args": {"dir": "up"}},
        {"action": "move", "args": {"dir": "up"}},
    ]
    assert _detect_stuck(history, threshold=3)


def test_detect_stuck_different_actions():
    history = [
        {"action": "move", "args": {"dir": "up"}},
        {"action": "jump", "args": {}},
        {"action": "move", "args": {"dir": "up"}},
    ]
    assert not _detect_stuck(history, threshold=3)


def test_detect_stuck_different_args():
    history = [
        {"action": "move", "args": {"dir": "up"}},
        {"action": "move", "args": {"dir": "down"}},
        {"action": "move", "args": {"dir": "up"}},
    ]
    assert not _detect_stuck(history, threshold=3)


def test_detect_stuck_missing_args():
    # If args is missing, it should default to empty dict and match
    history = [
        {"action": "wait"},
        {"action": "wait"},
        {"action": "wait"},
    ]
    assert _detect_stuck(history, threshold=3)


def test_detect_stuck_mixed_missing_and_empty_args():
    # Missing args and empty dict should be treated the same (stringified)
    history = [
        {"action": "wait"},
        {"action": "wait", "args": {}},
        {"action": "wait"},
    ]
    assert _detect_stuck(history, threshold=3)
