import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Ensure gamepilot is in path just in case
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gamepilot.session import Session

def test_save_screenshot_none(tmp_path):
    with Session(goal="test none", session_dir=tmp_path) as s:
        result = s.save_screenshot(None, "test")
        assert result is None

def test_save_screenshot_success(tmp_path):
    with Session(goal="test success", session_dir=tmp_path) as s:
        img_mock = MagicMock()

        result = s.save_screenshot(img_mock, "step_001")

        expected_path = s.screenshots_dir / "step_001.jpg"
        assert result == expected_path

        img_mock.save.assert_called_once_with(str(expected_path), format="JPEG", quality=85)

        events = s._events
        log_event = next((e for e in events if e["type"] == "screenshot_saved"), None)
        assert log_event is not None
        assert log_event["name"] == "step_001"
        assert log_event["path"] == str(expected_path)

def test_save_screenshot_failure(tmp_path):
    with Session(goal="test failure", session_dir=tmp_path) as s:
        img_mock = MagicMock()
        img_mock.save.side_effect = IOError("disk full")

        result = s.save_screenshot(img_mock, "step_002")

        assert result is None

        events = s._events
        log_event = next((e for e in events if e["type"] == "screenshot_save_failed"), None)
        assert log_event is not None
        assert log_event["name"] == "step_002"
        assert log_event["error"] == "disk full"
