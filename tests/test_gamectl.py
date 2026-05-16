import json
import pytest
import ctypes
from unittest.mock import MagicMock

# Mock ctypes properties specific to Windows for Linux testing environment
if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
if not hasattr(ctypes, "WINFUNCTYPE"):
    ctypes.WINFUNCTYPE = MagicMock()

from livetools.gamectl import load_macros


def test_load_macros_file_not_found():
    with pytest.raises(FileNotFoundError, match="Macro file not found:"):
        load_macros("nonexistent_macro_file.json")


def test_load_macros_non_dict_json(tmp_path):
    p = tmp_path / "macros.json"
    p.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    with pytest.raises(ValueError, match="Macro file must be a JSON object"):
        load_macros(p)


def test_load_macros_success(tmp_path):
    p = tmp_path / "macros.json"
    data = {
        "macro1": {"description": "Test macro 1", "steps": []},
        "macro2": {"description": "Test macro 2", "steps": ["step1"]},
    }
    p.write_text(json.dumps(data), encoding="utf-8")

    result = load_macros(p)
    assert result == data
