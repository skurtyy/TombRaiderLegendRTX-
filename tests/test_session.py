from unittest.mock import MagicMock
from gamepilot.session import Session


def test_save_screenshot_success(tmp_path):
    with Session(goal="test", session_dir=tmp_path) as s:
        img = MagicMock()
        img.save = MagicMock()

        path = s.save_screenshot(img, "test_shot")

        assert path is not None
        assert path == s.screenshots_dir / "test_shot.jpg"
        img.save.assert_called_once_with(str(path), format="JPEG", quality=85)

        # Verify log entry
        assert any(
            e["type"] == "screenshot_saved" and e["name"] == "test_shot"
            for e in s._events
        )


def test_save_screenshot_none(tmp_path):
    with Session(goal="test", session_dir=tmp_path) as s:
        path = s.save_screenshot(None, "test_shot")
        assert path is None


def test_save_screenshot_failure(tmp_path):
    with Session(goal="test", session_dir=tmp_path) as s:
        img = MagicMock()
        img.save.side_effect = Exception("save failed")

        path = s.save_screenshot(img, "test_shot")

        assert path is None

        # Verify error log entry
        assert any(
            e["type"] == "screenshot_save_failed" and e["error"] == "save failed"
            for e in s._events
        )
