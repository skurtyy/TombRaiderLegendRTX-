import sys
import ctypes
from unittest.mock import MagicMock

# Mock PIL for Linux
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()

# Mock windll for Linux
if not hasattr(ctypes, 'windll'):
    ctypes.windll = MagicMock()
if not hasattr(ctypes, 'WINFUNCTYPE'):
    ctypes.WINFUNCTYPE = MagicMock()

from gamepilot.agent import _detect_stuck  # noqa: E402


def test_detect_stuck_empty_history():
    assert not _detect_stuck([], threshold=3)


def test_detect_stuck_less_than_threshold():
    history = [
        {"action": "click", "args": {"x": 10}},
        {"action": "click", "args": {"x": 10}}
    ]
    assert not _detect_stuck(history, threshold=3)


def test_detect_stuck_all_same():
    history = [
        {"action": "click", "args": {"x": 10}},
        {"action": "click", "args": {"x": 10}},
        {"action": "click", "args": {"x": 10}}
    ]
    assert _detect_stuck(history, threshold=3)


def test_detect_stuck_different_actions():
    history = [
        {"action": "click", "args": {"x": 10}},
        {"action": "move", "args": {"x": 10}},
        {"action": "click", "args": {"x": 10}}
    ]
    assert not _detect_stuck(history, threshold=3)


def test_detect_stuck_different_args():
    history = [
        {"action": "click", "args": {"x": 10}},
        {"action": "click", "args": {"x": 20}},
        {"action": "click", "args": {"x": 10}}
    ]
    assert not _detect_stuck(history, threshold=3)


def test_detect_stuck_more_than_threshold_stuck():
    history = [
        {"action": "move", "args": {"y": 5}},
        {"action": "click", "args": {"x": 10}},
        {"action": "click", "args": {"x": 10}},
        {"action": "click", "args": {"x": 10}}
    ]
    assert _detect_stuck(history, threshold=3)


def test_detect_stuck_more_than_threshold_not_stuck():
    history = [
        {"action": "click", "args": {"x": 10}},
        {"action": "click", "args": {"x": 10}},
        {"action": "click", "args": {"x": 10}},
        {"action": "move", "args": {"y": 5}}
    ]
    assert not _detect_stuck(history, threshold=3)


def test_detect_stuck_missing_args():
    history = [
        {"action": "wait"},
        {"action": "wait"},
        {"action": "wait"}
    ]
    assert _detect_stuck(history, threshold=3)


def test_detect_stuck_missing_action_and_args():
    history = [
        {}, {}, {}
    ]
    assert _detect_stuck(history, threshold=3)


def test_detect_stuck_default_threshold():
    # assuming STUCK_THRESHOLD is 5 as seen in agent.py
    history = [{"action": "wait"}] * 5
    assert _detect_stuck(history)

    history_short = [{"action": "wait"}] * 4
    assert not _detect_stuck(history_short)
