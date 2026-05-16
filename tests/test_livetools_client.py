from unittest.mock import patch, MagicMock

from livetools.client import is_target_running

class MockCtypesNoWindll:
    @property
    def windll(self):
        raise AttributeError("no windll on unix")

class MockKernel32:
    def __init__(self, open_process_return):
        self.OpenProcess = MagicMock(return_value=open_process_return)
        self.CloseHandle = MagicMock()

class MockWindll:
    def __init__(self, open_process_return):
        self.kernel32 = MockKernel32(open_process_return)

class MockCtypesWindows:
    def __init__(self, open_process_return=123):
        self.windll = MockWindll(open_process_return)

def test_is_target_running_none_pid():
    assert is_target_running(None) is False

def test_is_target_running_windows_success():
    mock_ctypes = MockCtypesWindows(open_process_return=123)
    with patch.dict("sys.modules", {"ctypes": mock_ctypes}):
        assert is_target_running(1234) is True
        mock_ctypes.windll.kernel32.OpenProcess.assert_called_once_with(
            0x00100000, False, 1234
        )
        mock_ctypes.windll.kernel32.CloseHandle.assert_called_once_with(123)

def test_is_target_running_windows_failure():
    mock_ctypes = MockCtypesWindows(open_process_return=0)
    with patch.dict("sys.modules", {"ctypes": mock_ctypes}):
        assert is_target_running(1234) is False
        mock_ctypes.windll.kernel32.OpenProcess.assert_called_once_with(
            0x00100000, False, 1234
        )
        mock_ctypes.windll.kernel32.CloseHandle.assert_not_called()

def test_is_target_running_unix_success():
    with patch.dict("sys.modules", {"ctypes": MockCtypesNoWindll()}):
        with patch("os.kill") as mock_kill:
            mock_kill.return_value = None
            assert is_target_running(1234) is True
            mock_kill.assert_called_once_with(1234, 0)

def test_is_target_running_unix_oserror():
    with patch.dict("sys.modules", {"ctypes": MockCtypesNoWindll()}):
        with patch("os.kill") as mock_kill:
            mock_kill.side_effect = OSError("No such process")
            assert is_target_running(1234) is False
            mock_kill.assert_called_once_with(1234, 0)

def test_is_target_running_unix_processlookuperror():
    with patch.dict("sys.modules", {"ctypes": MockCtypesNoWindll()}):
        with patch("os.kill") as mock_kill:
            mock_kill.side_effect = ProcessLookupError("No such process")
            assert is_target_running(1234) is False
            mock_kill.assert_called_once_with(1234, 0)
