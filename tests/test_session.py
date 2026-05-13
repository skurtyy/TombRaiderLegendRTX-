import json
import pytest
import time

from gamepilot.session import Session


@pytest.fixture
def mock_time(monkeypatch):
    monkeypatch.setattr(time, "monotonic", lambda: 1000.0)


@pytest.fixture
def session_dir(tmp_path):
    return tmp_path / "test_session"


def test_write_summary_success(session_dir, mock_time):
    session = Session(goal="test goal", session_dir=session_dir, dry_run=False)
    session.step_count = 5

    # Mocking _events for event_count
    session._events = [{"type": "start"}, {"type": "action"}]

    result = {
        "success": True,
        "final_state": "in_game",
    }

    path = session.write_summary(result)

    assert path.exists()
    assert path.name == "summary.json"

    with open(path, "r") as f:
        summary = json.load(f)

    assert summary["goal"] == "test goal"
    assert summary["success"] is True
    assert summary["steps_taken"] == 5
    assert summary["final_state"] == "in_game"
    assert summary["error"] is None
    assert (
        summary["duration_s"] == 0.0
    )  # because monotonic is mocked to return 1000.0 and start time is 1000.0
    assert summary["dry_run"] is False
    assert summary["event_count"] == 2


def test_write_summary_failure_with_error(session_dir, mock_time):
    session = Session(goal="test goal", session_dir=session_dir, dry_run=True)
    session.step_count = 10

    result = {
        "success": False,
        "steps_taken": 8,  # Should override step_count
        "final_state": "main_menu",
        "error": "Failed to load game",
    }

    path = session.write_summary(result)

    with open(path, "r") as f:
        summary = json.load(f)

    assert summary["goal"] == "test goal"
    assert summary["success"] is False
    assert summary["steps_taken"] == 8
    assert summary["final_state"] == "main_menu"
    assert summary["error"] == "Failed to load game"
    assert summary["dry_run"] is True


def test_write_summary_empty_result(session_dir, mock_time):
    session = Session(goal="test goal", session_dir=session_dir)

    path = session.write_summary({})

    with open(path, "r") as f:
        summary = json.load(f)

    assert summary["success"] is False
    assert summary["steps_taken"] == 0
    assert summary["final_state"] == "unknown"
    assert summary["error"] is None
