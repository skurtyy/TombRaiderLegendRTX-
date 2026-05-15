import json
from unittest.mock import patch
import sys

sys.path.insert(0, ".")

from livetools.client import read_state


def test_read_state_non_existent(tmp_path):
    with patch("livetools.client.STATE_FILE", tmp_path / "non_existent.json"):
        assert read_state() is None


def test_read_state_valid_json(tmp_path):
    state_file = tmp_path / ".state.json"
    state_data = {"pid": 1234, "status": "running"}
    state_file.write_text(json.dumps(state_data))

    with patch("livetools.client.STATE_FILE", state_file):
        assert read_state() == state_data


def test_read_state_invalid_json(tmp_path):
    state_file = tmp_path / ".state.json"
    state_file.write_text("invalid json {")

    with patch("livetools.client.STATE_FILE", state_file):
        assert read_state() is None
