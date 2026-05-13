import pytest
import json
from gamepilot.session import Session


@pytest.fixture
def session_dir(tmp_path):
    return tmp_path / "test_session"


def test_write_summary(session_dir):
    with Session(goal="test goal", session_dir=session_dir) as session:
        session.step_count = 5
        session._events = [{"type": "test_event"} for _ in range(3)]

        result = {
            "success": True,
            "final_state": "completed",
        }

        # Test with partial result dictionary
        summary_path = session.write_summary(result)

        assert summary_path.exists()
        assert summary_path.name == "summary.json"

        summary_data = json.loads(summary_path.read_text())

        assert summary_data["goal"] == "test goal"
        assert summary_data["success"] is True
        assert summary_data["steps_taken"] == 5  # Fallback to session.step_count
        assert summary_data["final_state"] == "completed"
        assert summary_data["error"] is None
        assert isinstance(summary_data["duration_s"], float)
        assert summary_data["dry_run"] is False
        assert summary_data["event_count"] == 3  # Based on len(session._events)


def test_write_summary_full_result(session_dir):
    with Session(goal="test goal", session_dir=session_dir, dry_run=True) as session:
        session.step_count = 5

        result = {
            "success": False,
            "steps_taken": 10,  # Should override session.step_count
            "final_state": "failed",
            "error": "Test error message",
        }

        summary_path = session.write_summary(result)

        summary_data = json.loads(summary_path.read_text())

        assert summary_data["success"] is False
        assert summary_data["steps_taken"] == 10
        assert summary_data["final_state"] == "failed"
        assert summary_data["error"] == "Test error message"
        assert summary_data["dry_run"] is True


def test_write_summary_empty_result(session_dir):
    with Session(goal="test goal", session_dir=session_dir) as session:
        session.step_count = 2

        result = {}

        summary_path = session.write_summary(result)

        summary_data = json.loads(summary_path.read_text())

        assert summary_data["success"] is False
        assert summary_data["steps_taken"] == 2
        assert summary_data["final_state"] == "unknown"
        assert summary_data["error"] is None
