import sys
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Mock ctypes for Linux compatibility since gamectl uses ctypes.windll
sys.modules["ctypes"] = MagicMock()
sys.modules["ctypes.wintypes"] = MagicMock()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from livetools.gamectl import load_macros  # noqa: E402


def test_load_macros_success(tmp_path):
    # Setup valid JSON macro file
    macro_data = {"test_macro": {"description": "A test macro", "steps": []}}
    p = tmp_path / "macros.json"
    p.write_text(json.dumps(macro_data), encoding="utf-8")

    # Test valid load
    result = load_macros(p)
    assert result == macro_data


def test_load_macros_not_found():
    # Test loading a non-existent file
    with pytest.raises(FileNotFoundError, match="Macro file not found"):
        load_macros("non_existent_file.json")


def test_load_macros_invalid_json(tmp_path):
    # Setup file with invalid JSON
    p = tmp_path / "invalid.json"
    p.write_text("{invalid json", encoding="utf-8")

    # Test invalid json parsing
    with pytest.raises(json.JSONDecodeError):
        load_macros(p)


def test_load_macros_non_dict(tmp_path):
    # Setup file with valid JSON that is not a dictionary (e.g., a list)
    p = tmp_path / "list.json"
    p.write_text(json.dumps([{"step": 1}]), encoding="utf-8")

    # Test valid JSON but not a dictionary
    with pytest.raises(ValueError, match="Macro file must be a JSON object"):
        load_macros(p)
