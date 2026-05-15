import sys
import ctypes
import pytest
import json
from pathlib import Path

# Since gamectl requires Windows-specific ctypes (windll, wintypes), we should
# patch sys.modules to mock ctypes when importing livetools.gamectl on Linux.
from unittest.mock import MagicMock

# Create a clean mock structure that doesn't permanently pollute the global ctypes module
mock_ctypes = MagicMock()
mock_ctypes.windll = MagicMock()
mock_wintypes = MagicMock()
mock_wintypes.WORD = ctypes.c_uint16
mock_wintypes.DWORD = ctypes.c_uint32
mock_wintypes.LONG = ctypes.c_long
mock_wintypes.BOOL = ctypes.c_bool
mock_wintypes.HWND = ctypes.c_void_p
mock_wintypes.LPARAM = ctypes.c_void_p
mock_wintypes.HANDLE = ctypes.c_void_p

class DummyPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
mock_wintypes.POINT = DummyPoint

mock_ctypes.wintypes = mock_wintypes

def mock_winfunctype(*args, **kwargs):
    return MagicMock()
mock_ctypes.WINFUNCTYPE = mock_winfunctype

# Inject the mocked ctypes into sys.modules
original_ctypes = sys.modules.get("ctypes")
original_wintypes = sys.modules.get("ctypes.wintypes")
sys.modules["ctypes"] = mock_ctypes
sys.modules["ctypes.wintypes"] = mock_wintypes

try:
    from livetools.gamectl import load_macros
finally:
    # Restore original modules to avoid polluting other tests
    if original_ctypes:
        sys.modules["ctypes"] = original_ctypes
    else:
        del sys.modules["ctypes"]

    if original_wintypes:
        sys.modules["ctypes.wintypes"] = original_wintypes
    else:
        del sys.modules["ctypes.wintypes"]

def test_load_macros_success(tmp_path: Path):
    macro_file = tmp_path / "macros.json"
    valid_data = {
        "macro1": {"description": "test", "steps": "WAIT:1000"},
        "macro2": {"steps": "A B C"}
    }
    macro_file.write_text(json.dumps(valid_data), encoding="utf-8")

    result = load_macros(macro_file)
    assert result == valid_data

def test_load_macros_file_not_found(tmp_path: Path):
    missing_file = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError, match="Macro file not found:"):
        load_macros(missing_file)

def test_load_macros_invalid_json(tmp_path: Path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_macros(bad_file)

def test_load_macros_not_dict(tmp_path: Path):
    list_file = tmp_path / "list.json"
    list_file.write_text('["not", "a", "dict"]', encoding="utf-8")

    with pytest.raises(ValueError, match="Macro file must be a JSON object"):
        load_macros(list_file)

def test_load_macros_with_string_path(tmp_path: Path):
    macro_file = tmp_path / "macros.json"
    valid_data = {"macro1": {"steps": "WAIT:1000"}}
    macro_file.write_text(json.dumps(valid_data), encoding="utf-8")

    result = load_macros(str(macro_file))
    assert result == valid_data
