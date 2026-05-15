import pytest
from unittest.mock import MagicMock, patch
import PIL.Image

import gamepilot.capture as cap

def test_capture_window_gdi_not_windows(monkeypatch):
    monkeypatch.setattr(cap, "_IS_WINDOWS", False)
    with pytest.raises(RuntimeError, match=r"capture_window_gdi\(\) requires Windows"):
        cap.capture_window_gdi(1234)

def test_capture_window_gdi_success(monkeypatch):
    monkeypatch.setattr(cap, "_IS_WINDOWS", True)

    mock_wt = MagicMock()
    mock_ctypes = MagicMock()
    mock_user32 = MagicMock()
    mock_gdi32 = MagicMock()

    monkeypatch.setattr(cap, "wt", mock_wt, raising=False)
    monkeypatch.setattr(cap, "ctypes", mock_ctypes, raising=False)
    monkeypatch.setattr(cap, "user32", mock_user32, raising=False)
    monkeypatch.setattr(cap, "gdi32", mock_gdi32, raising=False)

    # Mocking BITMAPINFO since it might not be defined if _IS_WINDOWS was False on import
    mock_BITMAPINFO = MagicMock()
    mock_BITMAPINFOHEADER = MagicMock()
    monkeypatch.setattr(cap, "BITMAPINFO", mock_BITMAPINFO, raising=False)
    monkeypatch.setattr(cap, "BITMAPINFOHEADER", mock_BITMAPINFOHEADER, raising=False)

    mock_rect = MagicMock()
    mock_rect.right = 100
    mock_rect.left = 0
    mock_rect.bottom = 100
    mock_rect.top = 0
    mock_wt.RECT.return_value = mock_rect

    # White image -> mean > 2.0
    mock_ctypes.create_string_buffer.return_value = b'\xff' * (100 * 100 * 4)

    img = cap.capture_window_gdi(1234)
    assert img is not None
    assert isinstance(img, PIL.Image.Image)
    assert img.size == (100, 100)

    # Check calls
    mock_user32.GetClientRect.assert_called_once()
    mock_user32.GetDC.assert_called_once_with(1234)
    mock_gdi32.CreateCompatibleDC.assert_called_once()
    mock_gdi32.CreateCompatibleBitmap.assert_called_once()
    mock_gdi32.SelectObject.assert_called_once()
    mock_user32.PrintWindow.assert_called_once()
    mock_gdi32.GetDIBits.assert_called_once()
    mock_gdi32.DeleteObject.assert_called_once()
    mock_gdi32.DeleteDC.assert_called_once()
    mock_user32.ReleaseDC.assert_called_once()

def test_capture_window_gdi_black_frame(monkeypatch):
    monkeypatch.setattr(cap, "_IS_WINDOWS", True)

    mock_wt = MagicMock()
    mock_ctypes = MagicMock()
    mock_user32 = MagicMock()
    mock_gdi32 = MagicMock()

    monkeypatch.setattr(cap, "wt", mock_wt, raising=False)
    monkeypatch.setattr(cap, "ctypes", mock_ctypes, raising=False)
    monkeypatch.setattr(cap, "user32", mock_user32, raising=False)
    monkeypatch.setattr(cap, "gdi32", mock_gdi32, raising=False)

    mock_BITMAPINFO = MagicMock()
    mock_BITMAPINFOHEADER = MagicMock()
    monkeypatch.setattr(cap, "BITMAPINFO", mock_BITMAPINFO, raising=False)
    monkeypatch.setattr(cap, "BITMAPINFOHEADER", mock_BITMAPINFOHEADER, raising=False)

    mock_rect = MagicMock()
    mock_rect.right = 100
    mock_rect.left = 0
    mock_rect.bottom = 100
    mock_rect.top = 0
    mock_wt.RECT.return_value = mock_rect

    # Black image -> mean < 2.0
    mock_ctypes.create_string_buffer.return_value = b'\x00' * (100 * 100 * 4)

    img = cap.capture_window_gdi(1234)
    assert img is None

def test_capture_window_gdi_invalid_dimensions(monkeypatch):
    monkeypatch.setattr(cap, "_IS_WINDOWS", True)

    mock_wt = MagicMock()
    mock_ctypes = MagicMock()
    mock_user32 = MagicMock()
    mock_gdi32 = MagicMock()

    monkeypatch.setattr(cap, "wt", mock_wt, raising=False)
    monkeypatch.setattr(cap, "ctypes", mock_ctypes, raising=False)
    monkeypatch.setattr(cap, "user32", mock_user32, raising=False)
    monkeypatch.setattr(cap, "gdi32", mock_gdi32, raising=False)

    mock_rect = MagicMock()
    mock_rect.right = 0
    mock_rect.left = 0
    mock_rect.bottom = 0
    mock_rect.top = 0
    mock_wt.RECT.return_value = mock_rect

    img = cap.capture_window_gdi(1234)
    assert img is None

def test_capture_window_gdi_returns_none_when_width_or_height_zero(monkeypatch):
    monkeypatch.setattr(cap, "_IS_WINDOWS", True)

    mock_wt = MagicMock()
    mock_ctypes = MagicMock()
    mock_user32 = MagicMock()
    mock_gdi32 = MagicMock()

    monkeypatch.setattr(cap, "wt", mock_wt, raising=False)
    monkeypatch.setattr(cap, "ctypes", mock_ctypes, raising=False)
    monkeypatch.setattr(cap, "user32", mock_user32, raising=False)
    monkeypatch.setattr(cap, "gdi32", mock_gdi32, raising=False)

    mock_rect = MagicMock()
    mock_rect.right = 100
    mock_rect.left = 0
    mock_rect.bottom = 0
    mock_rect.top = 0
    mock_wt.RECT.return_value = mock_rect

    img = cap.capture_window_gdi(1234)
    assert img is None
