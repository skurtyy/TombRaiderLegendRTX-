import json
from unittest.mock import patch
from gamepilot.session import Session

def test_write_summary(tmp_path):
    with patch("time.monotonic") as mock_monotonic:
        mock_monotonic.side_effect = [100.0, 100.0, 105.5]

        session = Session(goal="Test goal", session_dir=tmp_path, dry_run=True)

        result = {
            "success": True,
            "steps_taken": 5,
            "final_state": "in_game",
            "error": "No error"
        }

        summary_path = session.write_summary(result)

        assert summary_path == tmp_path / "summary.json"
        assert summary_path.exists()

        summary_data = json.loads(summary_path.read_text())

        assert summary_data["goal"] == "Test goal"
        assert summary_data["success"] is True
        assert summary_data["steps_taken"] == 5
        assert summary_data["final_state"] == "in_game"
        assert summary_data["error"] == "No error"
        assert summary_data["duration_s"] == 5.5
        assert summary_data["dry_run"] is True
        assert summary_data["event_count"] == 1 # session_start event logged in init
