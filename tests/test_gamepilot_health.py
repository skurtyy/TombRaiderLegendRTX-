import sys
from unittest.mock import patch

from gamepilot.health import check_python_version, REQUIRED_PYTHON

def test_check_python_version_pass():
    # Test a version strictly greater than REQUIRED_PYTHON
    mock_version = (REQUIRED_PYTHON[0] + 1, REQUIRED_PYTHON[1], 0, 'final', 0)
    with patch("sys.version_info", mock_version):
        res = check_python_version()
        assert res.ok is True
        assert res.name == "Python version"
        assert res.message == f"{mock_version[0]}.{mock_version[1]}"

def test_check_python_version_exact():
    # Test exact REQUIRED_PYTHON match
    mock_version = (REQUIRED_PYTHON[0], REQUIRED_PYTHON[1], 0, 'final', 0)
    with patch("sys.version_info", mock_version):
        res = check_python_version()
        assert res.ok is True
        assert res.name == "Python version"
        assert res.message == f"{mock_version[0]}.{mock_version[1]}"

def test_check_python_version_fail():
    # Test a version strictly less than REQUIRED_PYTHON
    mock_version = (REQUIRED_PYTHON[0], REQUIRED_PYTHON[1] - 1, 0, 'final', 0)
    with patch("sys.version_info", mock_version):
        res = check_python_version()
        assert res.ok is False
        assert res.name == "Python version"
        assert f"{mock_version[0]}.{mock_version[1]}" in res.message
        assert f"need {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+" in res.message
