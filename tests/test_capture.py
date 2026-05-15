import pytest
import sys
from unittest.mock import patch, MagicMock
from PIL import Image

import gamepilot.capture


@patch("gamepilot.capture._IS_WINDOWS", True)
@patch("gamepilot.capture.wt")
@patch("gamepilot.capture.user32")
@patch("gamepilot.capture.gdi32")
@patch("gamepilot.capture.ctypes")
@patch("gamepilot.capture.BITMAPINFO", create=True)
@patch("gamepilot.capture.BITMAPINFOHEADER", create=True)
def test_capture_window_gdi_success(
    mock_BITMAPINFOHEADER,
    mock_BITMAPINFO,
    mock_ctypes,
    mock_gdi32,
    mock_user32,
    mock_wt,
):
    with patch("gamepilot.capture._require_windows"):
        mock_rect = MagicMock()
        mock_rect.right = 100
        mock_rect.left = 0
        mock_rect.bottom = 100
        mock_rect.top = 0
        mock_wt.RECT.return_value = mock_rect

        mock_ctypes.sizeof.return_value = 40
        mock_ctypes.byref.return_value = MagicMock()

        fake_buf = bytearray([255, 255, 255, 255] * 10000)
        mock_ctypes.create_string_buffer.return_value = fake_buf

        img = gamepilot.capture.capture_window_gdi(12345)

        assert img is not None
        assert img.size == (100, 100)
        assert img.mode == "RGB"

        mock_user32.GetClientRect.assert_called_once()
        mock_user32.GetDC.assert_called_once_with(12345)
        mock_user32.PrintWindow.assert_called_once()
        mock_gdi32.GetDIBits.assert_called_once()
        mock_user32.ReleaseDC.assert_called_once()


@patch("gamepilot.capture._IS_WINDOWS", True)
@patch("gamepilot.capture.wt")
@patch("gamepilot.capture.user32")
@patch("gamepilot.capture.ctypes")
def test_capture_window_gdi_invalid_size(mock_ctypes, mock_user32, mock_wt):
    with patch("gamepilot.capture._require_windows"):
        mock_rect = MagicMock()
        mock_rect.right = 0
        mock_rect.left = 0
        mock_rect.bottom = 0
        mock_rect.top = 0
        mock_wt.RECT.return_value = mock_rect

        img = gamepilot.capture.capture_window_gdi(12345)
        assert img is None


@patch("gamepilot.capture._IS_WINDOWS", True)
@patch("gamepilot.capture.wt")
@patch("gamepilot.capture.user32")
@patch("gamepilot.capture.gdi32")
@patch("gamepilot.capture.ctypes")
@patch("gamepilot.capture.BITMAPINFO", create=True)
@patch("gamepilot.capture.BITMAPINFOHEADER", create=True)
def test_capture_window_gdi_black_screen(
    mock_BITMAPINFOHEADER,
    mock_BITMAPINFO,
    mock_ctypes,
    mock_gdi32,
    mock_user32,
    mock_wt,
):
    with patch("gamepilot.capture._require_windows"):
        mock_rect = MagicMock()
        mock_rect.right = 100
        mock_rect.left = 0
        mock_rect.bottom = 100
        mock_rect.top = 0
        mock_wt.RECT.return_value = mock_rect

        mock_ctypes.sizeof.return_value = 40
        mock_ctypes.byref.return_value = MagicMock()

        fake_buf = bytearray([1, 1, 1, 255] * 10000)
        mock_ctypes.create_string_buffer.return_value = fake_buf

        img = gamepilot.capture.capture_window_gdi(12345)
        assert img is None


def test_require_windows_fails_on_linux():
    with patch("gamepilot.capture._IS_WINDOWS", False):
        with pytest.raises(RuntimeError, match="requires Windows"):
            gamepilot.capture._require_windows("test_func")


def test_require_windows_passes_on_win32():
    with patch("gamepilot.capture._IS_WINDOWS", True):
        gamepilot.capture._require_windows("test_func")


@patch("gamepilot.capture.capture_window_gdi")
@patch("gamepilot.capture.capture_nvidia")
def test_capture_fallback(mock_capture_nvidia, mock_capture_window_gdi):
    mock_img = MagicMock()

    # Try GDI first, it succeeds
    mock_capture_window_gdi.return_value = mock_img
    res = gamepilot.capture.capture(123)
    assert res == mock_img
    mock_capture_window_gdi.assert_called_once_with(123)
    mock_capture_nvidia.assert_not_called()

    mock_capture_window_gdi.reset_mock()
    mock_capture_nvidia.reset_mock()

    # Try GDI first, it fails, fallback to NVIDIA
    mock_capture_window_gdi.return_value = None
    mock_capture_nvidia.return_value = mock_img
    res = gamepilot.capture.capture(123)
    assert res == mock_img
    mock_capture_window_gdi.assert_called_once_with(123)
    mock_capture_nvidia.assert_called_once_with(123)

    mock_capture_window_gdi.reset_mock()
    mock_capture_nvidia.reset_mock()

    # Prefer NVIDIA, bypass GDI
    mock_capture_nvidia.return_value = mock_img
    res = gamepilot.capture.capture(123, prefer_nvidia=True)
    assert res == mock_img
    mock_capture_window_gdi.assert_not_called()
    mock_capture_nvidia.assert_called_once_with(123)


def test_image_to_bytes():
    img = Image.new("RGB", (2000, 1000), color="white")
    res = gamepilot.capture.image_to_bytes(img, max_size=1000)

    assert isinstance(res, bytes)
    assert len(res) > 0
    import io

    reloaded = Image.open(io.BytesIO(res))
    assert reloaded.size == (1000, 500)
    assert reloaded.format == "JPEG"


@patch.dict(sys.modules, {"livetools.gamectl": MagicMock()})
def test_capture_nvidia_success():
    with patch("gamepilot.capture._IS_WINDOWS", True):
        with patch("gamepilot.capture._require_windows"):
            with patch("gamepilot.capture._get_nvidia_dir") as mock_get_nvidia_dir:
                with patch("time.time", return_value=1000.0):
                    with patch("time.sleep"):
                        mock_dir = MagicMock()
                        mock_dir.exists.return_value = True

                        mock_file1 = MagicMock()
                        mock_file1.suffix = ".png"
                        mock_file1.stat.return_value.st_mtime = 900.0  # old

                        mock_file2 = MagicMock()
                        mock_file2.suffix = ".jpg"
                        mock_file2.stat.return_value.st_mtime = 1001.0  # new

                        mock_dir.iterdir.return_value = [mock_file1, mock_file2]
                        mock_get_nvidia_dir.return_value = mock_dir

                        with patch("PIL.Image.open") as mock_open:
                            mock_img = MagicMock()
                            mock_open.return_value.convert.return_value = mock_img

                            img = gamepilot.capture.capture_nvidia(123)

                            assert img == mock_img
                            sys.modules[
                                "livetools.gamectl"
                            ].focus_hwnd.assert_called_once_with(123)
                            sys.modules[
                                "livetools.gamectl"
                            ].send_key.assert_called_once_with("]", hold_ms=50)
                            mock_open.assert_called_once_with(mock_file2)


@patch.dict(sys.modules, {"livetools.gamectl": MagicMock()})
def test_capture_nvidia_timeout():
    with patch("gamepilot.capture._IS_WINDOWS", True):
        with patch("gamepilot.capture._require_windows"):
            with patch("gamepilot.capture._get_nvidia_dir") as mock_get_nvidia_dir:
                with patch("time.time", return_value=1000.0):
                    with patch("time.sleep") as mock_sleep:
                        mock_dir = MagicMock()
                        mock_dir.exists.return_value = True

                        # Only old files
                        mock_file1 = MagicMock()
                        mock_file1.suffix = ".png"
                        mock_file1.stat.return_value.st_mtime = 900.0  # old

                        mock_dir.iterdir.return_value = [mock_file1]
                        mock_get_nvidia_dir.return_value = mock_dir

                        img = gamepilot.capture.capture_nvidia(123)

                        assert img is None
                        assert mock_sleep.call_count == 50


@patch.dict(sys.modules, {"livetools.gamectl": MagicMock()})
def test_capture_nvidia_not_exist():
    with patch("gamepilot.capture._IS_WINDOWS", True):
        with patch("gamepilot.capture._require_windows"):
            with patch("gamepilot.capture._get_nvidia_dir") as mock_get_nvidia_dir:
                with patch("time.time", return_value=1000.0):
                    with patch("time.sleep") as mock_sleep:
                        mock_dir = MagicMock()
                        mock_dir.exists.return_value = False

                        mock_get_nvidia_dir.return_value = mock_dir

                        img = gamepilot.capture.capture_nvidia(123)

                        assert img is None
                        assert mock_sleep.call_count == 50


@patch("gamepilot.capture._require_windows")
def test_get_nvidia_dir_and_other_tests(mock_req):
    gamepilot.capture.NVIDIA_SCREENSHOT_DIR = None

    mock_config_path = MagicMock()
    with patch.dict(
        sys.modules, {"config": MagicMock(NVIDIA_SCREENSHOT_DIR=mock_config_path)}
    ):
        result = gamepilot.capture._get_nvidia_dir()
        assert result is mock_config_path

        with patch.dict(
            sys.modules, {"config": MagicMock(NVIDIA_SCREENSHOT_DIR="SHOULD_NOT_USE")}
        ):
            assert gamepilot.capture._get_nvidia_dir() is mock_config_path
