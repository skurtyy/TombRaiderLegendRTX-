from unittest.mock import patch
import pytest

from gamepilot.health import check_platform

def test_check_platform_windows():
    with patch("gamepilot.health.IS_WINDOWS", True):
        result = check_platform()
        assert result.ok is True
        assert result.name == "Platform"
        assert result.message == "Windows"

def test_check_platform_non_windows():
    with patch("gamepilot.health.IS_WINDOWS", False), patch("sys.platform", "linux"):
        result = check_platform()
        assert result.ok is False
        assert result.name == "Platform"
        assert result.fatal is True
        assert "gamepilot requires Windows" in result.message
        assert result.message.startswith("linux")
