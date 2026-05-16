import json
from unittest.mock import patch
from gamepilot.session import Session

def test_write_summary(tmp_path):
    with patch("time.monotonic") as mock_time:
        mock_time.return_value = 100.0

        # We need to test the write_summary output
        s = Session(goal="Test goal", session_dir=tmp_path, dry_run=True)
        s.step_count = 5
        s._events = [{"type": "event1"}, {"type": "event2"}]

        result = {
            "success": True,
            "steps_taken": 4, # override step_count
            "final_state": "completed",
            "error": "some error"
        }

        mock_time.return_value = 105.5
        path = s.write_summary(result)

        assert path.exists()
        assert path.name == "summary.json"

        with open(path) as f:
            data = json.load(f)

        assert data["goal"] == "Test goal"
        assert data["success"] is True
        assert data["steps_taken"] == 4
        assert data["final_state"] == "completed"
        assert data["error"] == "some error"
        assert data["duration_s"] == 5.5
        assert data["dry_run"] is True
        assert data["event_count"] == 2

        s.close()

def test_write_summary_defaults(tmp_path):
    with patch("time.monotonic") as mock_time:
        mock_time.return_value = 200.0

        s = Session(goal="Another goal", session_dir=tmp_path, dry_run=False)
        s.step_count = 10
        s._events = [{"type": "start"}]

        # Empty result
        result = {}

        mock_time.return_value = 210.0
        path = s.write_summary(result)

        with open(path) as f:
            data = json.load(f)

        assert data["goal"] == "Another goal"
        assert data["success"] is False # default
        assert data["steps_taken"] == 10 # from self.step_count
        assert data["final_state"] == "unknown" # default
        assert "error" in data
        assert data["error"] is None
        assert data["duration_s"] == 10.0
        assert data["dry_run"] is False
        assert data["event_count"] == 1

        s.close()
