import sys
from pathlib import Path
from unittest import mock

import pytest

# Need to add repo root to sys.path to import gamepilot
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamepilot import remix


@pytest.fixture
def mock_env(tmp_path):
    """Set up a mock environment with isolated paths."""
    game_dir = tmp_path / "game"
    debug_runtime = tmp_path / "debug_runtime"

    game_dir.mkdir()
    debug_runtime.mkdir()

    runtime_marker = game_dir / ".runtime_type"

    with mock.patch("gamepilot.remix.GAME_DIR", game_dir), \
         mock.patch("gamepilot.remix.DEBUG_RUNTIME", debug_runtime), \
         mock.patch("gamepilot.remix.RUNTIME_MARKER", runtime_marker):
        yield game_dir, debug_runtime, runtime_marker


def test_get_active_runtime(mock_env):
    game_dir, debug_runtime, runtime_marker = mock_env

    # No marker
    assert remix.get_active_runtime() == "regular"

    # With marker
    runtime_marker.write_text("debug")
    assert remix.get_active_runtime() == "debug"

    runtime_marker.write_text("regular")
    assert remix.get_active_runtime() == "regular"


def test_swap_to_debug_not_found(mock_env, capsys):
    game_dir, debug_runtime, runtime_marker = mock_env
    # remove debug runtime
    debug_runtime.rmdir()

    assert not remix.swap_to_debug()
    captured = capsys.readouterr()
    assert "ERROR: Debug runtime not found" in captured.out


def test_swap_to_debug_no_trex(mock_env, capsys):
    game_dir, debug_runtime, runtime_marker = mock_env
    # debug runtime exists, but no .trex
    assert not remix.swap_to_debug()
    captured = capsys.readouterr()
    assert "ERROR: No .trex in debug runtime" in captured.out


def test_swap_to_debug_already_debug(mock_env, capsys):
    game_dir, debug_runtime, runtime_marker = mock_env
    (debug_runtime / ".trex").mkdir()
    runtime_marker.write_text("debug")

    assert remix.swap_to_debug()
    captured = capsys.readouterr()
    assert "Already on debug runtime" in captured.out


def test_swap_to_debug_success(mock_env, capsys):
    game_dir, debug_runtime, runtime_marker = mock_env

    # Setup debug runtime files
    debug_trex = debug_runtime / ".trex"
    debug_trex.mkdir()
    (debug_trex / "debug_file.txt").write_text("debug content")

    (debug_runtime / "d3d9.dll").write_text("debug dll")

    # Setup game regular files
    game_trex = game_dir / ".trex"
    game_trex.mkdir()
    (game_trex / "regular_file.txt").write_text("regular content")

    (game_dir / "d3d9.dll").write_text("regular dll")

    assert remix.swap_to_debug()

    # Check that backup was created
    backup_dir = game_dir / ".runtime_backup_regular"
    assert backup_dir.exists()
    assert (backup_dir / ".trex" / "regular_file.txt").read_text() == "regular content"
    assert (backup_dir / "d3d9.dll").read_text() == "regular dll"

    # Check that current game dir has debug files
    assert (game_dir / ".trex" / "debug_file.txt").read_text() == "debug content"
    assert (game_dir / "d3d9.dll").read_text() == "debug dll"

    # Check that marker is updated
    assert runtime_marker.read_text() == "debug"


def test_swap_to_regular_already_regular(mock_env, capsys):
    game_dir, debug_runtime, runtime_marker = mock_env
    runtime_marker.write_text("regular")

    assert remix.swap_to_regular()
    captured = capsys.readouterr()
    assert "Already on regular runtime" in captured.out


def test_swap_to_regular_no_backup(mock_env, capsys):
    game_dir, debug_runtime, runtime_marker = mock_env
    runtime_marker.write_text("debug")

    assert not remix.swap_to_regular()
    captured = capsys.readouterr()
    assert "ERROR: No regular runtime backup found" in captured.out


def test_swap_to_regular_success(mock_env, capsys):
    game_dir, debug_runtime, runtime_marker = mock_env

    # Assume we are currently in debug
    runtime_marker.write_text("debug")

    # Setup current game files (debug)
    game_trex = game_dir / ".trex"
    game_trex.mkdir()
    (game_trex / "debug_file.txt").write_text("debug content")
    (game_dir / "d3d9.dll").write_text("debug dll")

    # Setup regular backup
    backup_dir = game_dir / ".runtime_backup_regular"
    backup_dir.mkdir()
    backup_trex = backup_dir / ".trex"
    backup_trex.mkdir()
    (backup_trex / "regular_file.txt").write_text("regular content")
    (backup_dir / "d3d9.dll").write_text("regular dll")

    assert remix.swap_to_regular()

    # Check that debug state was backed up
    debug_backup = game_dir / ".runtime_backup_debug"
    assert debug_backup.exists()
    assert (debug_backup / ".trex" / "debug_file.txt").read_text() == "debug content"
    assert (debug_backup / "d3d9.dll").read_text() == "debug dll"

    # Check that regular state was restored
    assert (game_dir / ".trex" / "regular_file.txt").read_text() == "regular content"
    assert (game_dir / "d3d9.dll").read_text() == "regular dll"

    # Check that marker is updated
    assert runtime_marker.read_text() == "regular"
