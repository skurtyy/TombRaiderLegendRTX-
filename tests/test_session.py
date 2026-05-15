import json
from unittest.mock import patch

from gamepilot.session import Session


def test_write_summary(tmp_path):
    goal = "test_goal"
    session_dir = tmp_path / "test_session"

    with patch("time.monotonic", return_value=10.0):
        with Session(goal=goal, session_dir=session_dir, dry_run=True) as session:
            session.start_time = 0.0
            session.step_count = 5
            session.log("test_event", data="test")

            result = {
                "success": True,
                "steps_taken": session.step_count,
                "final_state": "in_game",
                "error": None,
            }

            with patch("time.monotonic", return_value=12.5):
                summary_path = session.write_summary(result)

    assert summary_path.exists()
    assert summary_path.name == "summary.json"
    assert summary_path.parent == session_dir

    with open(summary_path, "r", encoding="utf-8") as f:
        summary_data = json.load(f)

    assert summary_data["goal"] == goal
    assert summary_data["success"] is True
    assert summary_data["steps_taken"] == 5
    assert summary_data["final_state"] == "in_game"
    assert summary_data["error"] is None
    assert summary_data["duration_s"] == 12.5
    assert summary_data["dry_run"] is True
    assert summary_data["event_count"] == 2  # 1 start + 1 test_event


def test_write_summary_defaults(tmp_path):
    goal = "test_goal_defaults"
    session_dir = tmp_path / "test_session_defaults"

    with patch("time.monotonic", return_value=10.0):
        with Session(goal=goal, session_dir=session_dir) as session:
            session.start_time = 0.0

            # Empty result dict, checking fallback to defaults
            result = {}

            with patch("time.monotonic", return_value=15.0):
                summary_path = session.write_summary(result)

    with open(summary_path, "r", encoding="utf-8") as f:
        summary_data = json.load(f)

    assert summary_data["goal"] == goal
    assert summary_data["success"] is False
    assert summary_data["steps_taken"] == 0
    assert summary_data["final_state"] == "unknown"
    assert summary_data["error"] is None
    assert summary_data["duration_s"] == 15.0
    assert summary_data["dry_run"] is False
