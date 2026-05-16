import sys
import pytest
from unittest.mock import patch
from gamepilot.health import check_platform

def test_check_platform_windows():
    with patch("gamepilot.health.IS_WINDOWS", True):
        result = check_platform()
        assert result.ok is True
        assert result.message == "Windows"
        assert result.name == "Platform"
        # Since it passes, fatal is still default True but its value doesn't matter much. Let's not assert on it unless necessary.

def test_check_platform_non_windows():
    with patch("gamepilot.health.IS_WINDOWS", False):
        with patch("sys.platform", "linux"):
            result = check_platform()
            assert result.ok is False
            assert "linux" in result.message
            assert result.name == "Platform"
            assert result.fatal is True
