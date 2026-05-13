# flake8: noqa: E501
from unittest.mock import patch
from gamepilot.health import check_python_version, REQUIRED_PYTHON, CheckResult


def test_check_python_version_pass_exact():
    with patch("gamepilot.health.sys") as mock_sys:
        mock_sys.version_info = (REQUIRED_PYTHON[0], REQUIRED_PYTHON[1], 0)
        result = check_python_version()
        assert result.ok is True
        assert result.name == "Python version"
        assert result.message == f"{REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}"
        assert result.fatal is True


def test_check_python_version_pass_higher():
    with patch("gamepilot.health.sys") as mock_sys:
        mock_sys.version_info = (REQUIRED_PYTHON[0], REQUIRED_PYTHON[1] + 1, 2)
        result = check_python_version()
        assert result.ok is True
        assert result.name == "Python version"
        assert result.message == f"{REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1] + 1}"
        assert result.fatal is True


def test_check_python_version_fail_lower():
    with patch("gamepilot.health.sys") as mock_sys:
        mock_sys.version_info = (REQUIRED_PYTHON[0], REQUIRED_PYTHON[1] - 1, 5)
        result = check_python_version()
        assert result.ok is False
        assert result.name == "Python version"
        assert (
            result.message
            == f"{REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1] - 1} (need {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+)"
        )
        assert result.fatal is True


def test_check_python_version_fail_major():
    with patch("gamepilot.health.sys") as mock_sys:
        mock_sys.version_info = (REQUIRED_PYTHON[0] - 1, 10, 0)
        result = check_python_version()
        assert result.ok is False
        assert result.name == "Python version"
        assert (
            result.message
            == f"{REQUIRED_PYTHON[0] - 1}.10 (need {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+)"
        )
        assert result.fatal is True


def test_checkresult_repr_pass():
    result = CheckResult("Test", True, "message")
    assert repr(result) == "[PASS] Test: message"


def test_checkresult_repr_fail():
    result = CheckResult("Test", False, "error", fatal=True)
    assert repr(result) == "[FAIL] Test: error"


def test_checkresult_repr_warn():
    result = CheckResult("Test", False, "warning", fatal=False)
    assert repr(result) == "[WARN] Test: warning"
