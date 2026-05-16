import pytest
from unittest.mock import patch
import gamepilot.remix as remix


@pytest.fixture
def mock_paths(tmp_path):
    game_dir = tmp_path / "game_dir"
    debug_runtime = tmp_path / "debug_runtime"

    game_dir.mkdir()
    debug_runtime.mkdir()

    runtime_marker = game_dir / ".runtime_type"

    with (
        patch("gamepilot.remix.GAME_DIR", game_dir),
        patch("gamepilot.remix.DEBUG_RUNTIME", debug_runtime),
        patch("gamepilot.remix.RUNTIME_MARKER", runtime_marker),
    ):
        yield game_dir, debug_runtime, runtime_marker


def test_swap_to_debug_no_debug_runtime(mock_paths):
    game_dir, debug_runtime, runtime_marker = mock_paths
    debug_runtime.rmdir()  # remove it so it doesn't exist
    assert remix.swap_to_debug() is False


def test_swap_to_debug_no_trex(mock_paths):
    game_dir, debug_runtime, runtime_marker = mock_paths
    assert remix.swap_to_debug() is False


def test_swap_to_debug_already_debug(mock_paths):
    game_dir, debug_runtime, runtime_marker = mock_paths
    (debug_runtime / ".trex").mkdir()
    runtime_marker.write_text("debug")
    assert remix.swap_to_debug() is True
    # no backup directory created
    assert not (game_dir / ".runtime_backup_regular").exists()


def test_swap_to_debug_success(mock_paths):
    game_dir, debug_runtime, runtime_marker = mock_paths

    # Setup regular runtime files
    (game_dir / ".trex").mkdir()
    (game_dir / ".trex" / "regular.txt").write_text("regular trex")
    (game_dir / "d3d9.dll").write_text("regular d3d9")

    # Setup debug runtime files
    (debug_runtime / ".trex").mkdir()
    (debug_runtime / ".trex" / "debug.txt").write_text("debug trex")
    (debug_runtime / "d3d9.dll").write_text("debug d3d9")

    assert remix.swap_to_debug() is True

    # Check that backup was created
    backup_dir = game_dir / ".runtime_backup_regular"
    assert backup_dir.exists()
    assert (backup_dir / ".trex" / "regular.txt").exists()
    assert (backup_dir / "d3d9.dll").read_text() == "regular d3d9"

    # Check that files were replaced
    assert (game_dir / ".trex" / "debug.txt").exists()
    assert not (game_dir / ".trex" / "regular.txt").exists()
    assert (game_dir / "d3d9.dll").read_text() == "debug d3d9"

    # Check runtime marker
    assert runtime_marker.read_text() == "debug"


def test_swap_to_regular_already_regular(mock_paths):
    game_dir, debug_runtime, runtime_marker = mock_paths
    assert remix.swap_to_regular() is True


def test_swap_to_regular_no_backup(mock_paths):
    game_dir, debug_runtime, runtime_marker = mock_paths
    runtime_marker.write_text("debug")
    assert remix.swap_to_regular() is False


def test_swap_to_regular_success(mock_paths):
    game_dir, debug_runtime, runtime_marker = mock_paths
    runtime_marker.write_text("debug")

    # create backup directory
    backup_dir = game_dir / ".runtime_backup_regular"
    backup_dir.mkdir()
    (backup_dir / ".trex").mkdir()
    (backup_dir / ".trex" / "regular.txt").write_text("regular trex")
    (backup_dir / "d3d9.dll").write_text("regular d3d9")

    # setup current debug files
    (game_dir / ".trex").mkdir()
    (game_dir / ".trex" / "debug.txt").write_text("debug trex")
    (game_dir / "d3d9.dll").write_text("debug d3d9")

    assert remix.swap_to_regular() is True

    # verify debug was backed up
    debug_backup = game_dir / ".runtime_backup_debug"
    assert debug_backup.exists()
    assert (debug_backup / ".trex" / "debug.txt").exists()
    assert (debug_backup / "d3d9.dll").read_text() == "debug d3d9"

    # verify regular was restored
    assert (game_dir / ".trex" / "regular.txt").exists()
    assert not (game_dir / ".trex" / "debug.txt").exists()
    assert (game_dir / "d3d9.dll").read_text() == "regular d3d9"
    assert runtime_marker.read_text() == "regular"


def test_backup_current_already_exists(mock_paths):
    game_dir, debug_runtime, runtime_marker = mock_paths

    # Pre-create the backup dir
    backup_dir = game_dir / ".runtime_backup_regular"
    backup_dir.mkdir()
    (backup_dir / "old_file.txt").write_text("old")

    # Call swap_to_debug which triggers _backup_current("regular")
    # Setup debug runtime files
    (debug_runtime / ".trex").mkdir()

    remix.swap_to_debug()

    # Verify backup dir was recreated
    assert backup_dir.exists()
    assert not (backup_dir / "old_file.txt").exists()
