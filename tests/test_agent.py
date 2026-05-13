import sys
from unittest.mock import MagicMock

# Mock windll before importing anything that depends on it
# Specifically, livetools.gamectl uses a lot of ctypes on windows,
# which fail on linux during import
sys.modules["livetools.gamectl"] = MagicMock()

from gamepilot.agent import _detect_stuck  # noqa: E402


def test_detect_stuck_empty_history():
    assert _detect_stuck([]) is False


def test_detect_stuck_below_threshold():
    history = [
        {"action": "move", "args": {"dir": "forward"}},
        {"action": "move", "args": {"dir": "forward"}},
    ]
    # Default threshold is 5
    assert _detect_stuck(history) is False


def test_detect_stuck_exactly_threshold_same():
    history = [{"action": "jump", "args": {}} for _ in range(5)]
    assert _detect_stuck(history) is True


def test_detect_stuck_exactly_threshold_different():
    history = [
        {"action": "move", "args": {"dir": "forward"}},
        {"action": "jump", "args": {}},
        {"action": "move", "args": {"dir": "forward"}},
        {"action": "move", "args": {"dir": "forward"}},
        {"action": "move", "args": {"dir": "forward"}},
    ]
    assert _detect_stuck(history) is False


def test_detect_stuck_above_threshold_same_recent():
    history = [
        {"action": "move", "args": {"dir": "left"}},
        {"action": "move", "args": {"dir": "right"}},
        {"action": "jump", "args": {}},
        {"action": "jump", "args": {}},
        {"action": "jump", "args": {}},
        {"action": "jump", "args": {}},
        {"action": "jump", "args": {}},
    ]
    assert _detect_stuck(history) is True


def test_detect_stuck_custom_threshold():
    history = [
        {"action": "shoot", "args": {}},
        {"action": "shoot", "args": {}},
        {"action": "shoot", "args": {}},
    ]
    # threshold 3 matches exactly
    assert _detect_stuck(history, threshold=3) is True
    # threshold 4 is larger, should be false
    assert _detect_stuck(history, threshold=4) is False


def test_detect_stuck_ignores_other_keys():
    history = [
        {"action": "move", "args": {"dir": "up"}, "reasoning": "to go up"},
        {
            "action": "move",
            "args": {"dir": "up"},
            "reasoning": "still going up",
            "extra": 1,
        },
        {"action": "move", "args": {"dir": "up"}},
        {"action": "move", "args": {"dir": "up"}, "some_key": "val"},
        {"action": "move", "args": {"dir": "up"}},
    ]
    assert _detect_stuck(history) is True
