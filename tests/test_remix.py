from unittest import mock
from pathlib import Path
from gamepilot.remix import (
    swap_to_regular,
    swap_to_debug,
    get_active_runtime,
    _backup_current,
    _restore_from,
)


def test_swap_to_regular_already_regular():
    with mock.patch("gamepilot.remix.get_active_runtime", return_value="regular"):
        assert swap_to_regular() is True


def test_swap_to_regular_no_backup():
    with (
        mock.patch("gamepilot.remix.get_active_runtime", return_value="debug"),
        mock.patch("gamepilot.remix.GAME_DIR", Path("/fake/game/dir")),
    ):
        # We need to mock Path.exists to return False for the backup dir
        with mock.patch.object(Path, "exists", return_value=False):
            assert swap_to_regular() is False


def test_swap_to_regular_success(tmp_path):
    # Setup mock game directory
    game_dir = tmp_path / "game"
    game_dir.mkdir()

    # Create marker indicating we are on debug
    marker = game_dir / ".runtime_type"
    marker.write_text("debug")

    # Create the backup directory
    backup_dir = game_dir / ".runtime_backup_regular"
    backup_dir.mkdir()

    with (
        mock.patch("gamepilot.remix.GAME_DIR", game_dir),
        mock.patch("gamepilot.remix.RUNTIME_MARKER", marker),
    ):
        with (
            mock.patch("gamepilot.remix._backup_current") as mock_backup,
            mock.patch("gamepilot.remix._restore_from") as mock_restore,
        ):
            assert swap_to_regular() is True
            mock_backup.assert_called_once_with("debug")
            mock_restore.assert_called_once_with(backup_dir)
            assert marker.read_text() == "regular"


def test_swap_to_debug_no_debug_runtime():
    with mock.patch("gamepilot.remix.DEBUG_RUNTIME", Path("/fake/debug/dir")):
        with mock.patch.object(Path, "exists", return_value=False):
            assert swap_to_debug() is False


def test_swap_to_debug_no_debug_trex():
    debug_runtime = Path("/fake/debug/dir")
    with mock.patch("gamepilot.remix.DEBUG_RUNTIME", debug_runtime):

        def mock_exists(self):
            if self == debug_runtime:
                return True
            if self == debug_runtime / ".trex":
                return False
            return True

        with mock.patch.object(Path, "exists", new=mock_exists):
            assert swap_to_debug() is False


def test_swap_to_debug_already_debug():
    debug_runtime = Path("/fake/debug/dir")
    with mock.patch("gamepilot.remix.DEBUG_RUNTIME", debug_runtime):

        def mock_exists(self):
            if self == debug_runtime:
                return True
            if self == debug_runtime / ".trex":
                return True
            return True

        with mock.patch.object(Path, "exists", new=mock_exists):
            with mock.patch("gamepilot.remix.get_active_runtime", return_value="debug"):
                assert swap_to_debug() is True


def test_swap_to_debug_success(tmp_path):
    game_dir = tmp_path / "game"
    game_dir.mkdir()

    debug_dir = tmp_path / "debug"
    debug_dir.mkdir()
    (debug_dir / ".trex").mkdir()

    marker = game_dir / ".runtime_type"
    marker.write_text("regular")

    with (
        mock.patch("gamepilot.remix.GAME_DIR", game_dir),
        mock.patch("gamepilot.remix.RUNTIME_MARKER", marker),
        mock.patch("gamepilot.remix.DEBUG_RUNTIME", debug_dir),
    ):
        with (
            mock.patch("gamepilot.remix._backup_current") as mock_backup,
            mock.patch("gamepilot.remix._restore_from") as mock_restore,
        ):
            assert swap_to_debug() is True
            mock_backup.assert_called_once_with("regular")
            mock_restore.assert_called_once_with(debug_dir)
            assert marker.read_text() == "debug"


def test_get_active_runtime_no_marker(tmp_path):
    with mock.patch("gamepilot.remix.RUNTIME_MARKER", tmp_path / "missing_marker"):
        assert get_active_runtime() == "regular"


def test_backup_current(tmp_path):
    game_dir = tmp_path / "game"
    game_dir.mkdir()

    trex_dir = game_dir / ".trex"
    trex_dir.mkdir()
    (trex_dir / "file.txt").write_text("trex data")

    # Create some root files
    (game_dir / "d3d9.dll").write_text("d3d9 data")
    (game_dir / "missing.dll").write_text("missing")

    with (
        mock.patch("gamepilot.remix.GAME_DIR", game_dir),
        mock.patch("gamepilot.remix.ROOT_RUNTIME_FILES", ["d3d9.dll", "not_exist.dll"]),
    ):
        # Call _backup_current
        backup_dir = _backup_current("test")

        assert backup_dir.name == ".runtime_backup_test"
        assert backup_dir.exists()

        # Verify .trex was copied
        assert (backup_dir / ".trex" / "file.txt").read_text() == "trex data"

        # Verify root files were copied
        assert (backup_dir / "d3d9.dll").read_text() == "d3d9 data"
        assert not (backup_dir / "not_exist.dll").exists()


def test_backup_current_replace_existing(tmp_path):
    game_dir = tmp_path / "game"
    game_dir.mkdir()

    backup_dir = game_dir / ".runtime_backup_test"
    backup_dir.mkdir()
    (backup_dir / "old_file.txt").write_text("old")

    with mock.patch("gamepilot.remix.GAME_DIR", game_dir):
        _backup_current("test")

        assert backup_dir.exists()
        assert not (backup_dir / "old_file.txt").exists()


def test_restore_from(tmp_path):
    game_dir = tmp_path / "game"
    game_dir.mkdir()

    # Setup existing .trex to be replaced
    trex_dst = game_dir / ".trex"
    trex_dst.mkdir()
    (trex_dst / "old.txt").write_text("old")

    src_dir = tmp_path / "source"
    src_dir.mkdir()

    # Setup new .trex
    trex_src = src_dir / ".trex"
    trex_src.mkdir()
    (trex_src / "new.txt").write_text("new")

    # Setup root files
    (src_dir / "d3d9.dll").write_text("d3d9 new")

    with (
        mock.patch("gamepilot.remix.GAME_DIR", game_dir),
        mock.patch("gamepilot.remix.ROOT_RUNTIME_FILES", ["d3d9.dll", "not_exist.dll"]),
    ):
        _restore_from(src_dir)

        # Verify .trex was replaced
        assert trex_dst.exists()
        assert not (trex_dst / "old.txt").exists()
        assert (trex_dst / "new.txt").read_text() == "new"

        # Verify root files were copied
        assert (game_dir / "d3d9.dll").read_text() == "d3d9 new"
        assert not (game_dir / "not_exist.dll").exists()


def test_restore_from_no_existing_trex(tmp_path):
    game_dir = tmp_path / "game"
    game_dir.mkdir()

    src_dir = tmp_path / "source"
    src_dir.mkdir()

    trex_src = src_dir / ".trex"
    trex_src.mkdir()
    (trex_src / "new.txt").write_text("new")

    with mock.patch("gamepilot.remix.GAME_DIR", game_dir):
        _restore_from(src_dir)

        assert (game_dir / ".trex").exists()
        assert (game_dir / ".trex" / "new.txt").read_text() == "new"
