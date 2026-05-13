import sys
from unittest.mock import patch
from gamepilot.health import check_python_version, REQUIRED_PYTHON

def test_check_python_version_ok():
    with patch('sys.version_info', (REQUIRED_PYTHON[0], REQUIRED_PYTHON[1], 0)):
        result = check_python_version()
        assert result.ok is True
        assert result.name == "Python version"
        assert result.message == f"{REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}"

def test_check_python_version_newer():
    with patch('sys.version_info', (REQUIRED_PYTHON[0], REQUIRED_PYTHON[1] + 1, 0)):
        result = check_python_version()
        assert result.ok is True
        assert result.message == f"{REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1] + 1}"

def test_check_python_version_older():
    with patch('sys.version_info', (REQUIRED_PYTHON[0], REQUIRED_PYTHON[1] - 1, 0)):
        result = check_python_version()
        assert result.ok is False
        assert result.message == f"{REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1] - 1} (need {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+)"

def test_check_python_version_older_major():
    with patch('sys.version_info', (REQUIRED_PYTHON[0] - 1, REQUIRED_PYTHON[1], 0)):
        result = check_python_version()
        assert result.ok is False
        assert result.message == f"{REQUIRED_PYTHON[0] - 1}.{REQUIRED_PYTHON[1]} (need {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+)"
