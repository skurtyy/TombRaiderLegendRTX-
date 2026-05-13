from unittest.mock import patch

from gamepilot.health import check_platform

def test_check_platform_windows():
    with patch("gamepilot.health.IS_WINDOWS", True):
        result = check_platform()
        assert result.ok is True
        assert result.name == "Platform"
        assert result.message == "Windows"
        assert result.fatal is True

def test_check_platform_non_windows():
    with patch("gamepilot.health.IS_WINDOWS", False), patch("sys.platform", "linux"):
        result = check_platform()
        assert result.ok is False
        assert result.name == "Platform"
        assert "linux" in result.message
        assert result.fatal is True
