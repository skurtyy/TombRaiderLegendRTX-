import sys
from unittest.mock import patch
import pytest

from gamepilot.health import check_platform

def test_check_platform_windows():
    with patch("gamepilot.health.IS_WINDOWS", True):
        result = check_platform()
        assert result.ok is True
        assert result.message == "Windows"
        assert result.name == "Platform"

def test_check_platform_non_windows():
    with patch("gamepilot.health.IS_WINDOWS", False), patch("gamepilot.health.sys.platform", "linux"):
        result = check_platform()
        assert result.ok is False
        assert result.fatal is True
        assert result.name == "Platform"
        assert "linux — gamepilot requires Windows" in result.message
