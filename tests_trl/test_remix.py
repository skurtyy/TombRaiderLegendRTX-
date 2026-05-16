import shutil
from unittest.mock import patch
import pytest

from gamepilot.remix import swap_to_debug, ROOT_RUNTIME_FILES

@pytest.fixture
def mock_env(tmp_path):
    game_dir = tmp_path / "game"
    game_dir.mkdir()
    debug_dir = tmp_path / "debug"
    debug_dir.mkdir()

    with patch("gamepilot.remix.GAME_DIR", game_dir), \
         patch("gamepilot.remix.DEBUG_RUNTIME", debug_dir), \
         patch("gamepilot.remix.RUNTIME_MARKER", game_dir / ".runtime_type"):
        yield game_dir, debug_dir

def test_swap_to_debug_missing_runtime(mock_env):
    game_dir, debug_dir = mock_env
    shutil.rmtree(debug_dir)  # Make it missing

    assert swap_to_debug() is False

def test_swap_to_debug_missing_trex(mock_env):
    game_dir, debug_dir = mock_env
    # DEBUG_RUNTIME exists, but no .trex inside
    assert swap_to_debug() is False

def test_swap_to_debug_already_debug(mock_env):
    game_dir, debug_dir = mock_env
    (debug_dir / ".trex").mkdir()

    marker = game_dir / ".runtime_type"
    marker.write_text("debug")

    assert swap_to_debug() is True
    # Verify no backup was created
    assert not (game_dir / ".runtime_backup_regular").exists()

def test_swap_to_debug_success(mock_env):
    game_dir, debug_dir = mock_env

    # Setup regular game environment
    (game_dir / ".trex").mkdir()
    (game_dir / ".trex" / "regular_file.txt").touch()
    for fname in ROOT_RUNTIME_FILES:
        (game_dir / fname).touch()

    # Setup debug runtime environment
    (debug_dir / ".trex").mkdir()
    (debug_dir / ".trex" / "debug_file.txt").touch()
    (debug_dir / ROOT_RUNTIME_FILES[0]).write_text("debug version")

    assert swap_to_debug() is True

    # Verify marker
    marker = game_dir / ".runtime_type"
    assert marker.read_text().strip() == "debug"

    # Verify backup
    backup_dir = game_dir / ".runtime_backup_regular"
    assert backup_dir.exists()
    assert (backup_dir / ".trex" / "regular_file.txt").exists()
    for fname in ROOT_RUNTIME_FILES:
        assert (backup_dir / fname).exists()

    # Verify new files in game dir
    assert (game_dir / ".trex" / "debug_file.txt").exists()
    assert (game_dir / ROOT_RUNTIME_FILES[0]).read_text() == "debug version"
