import pytest
from gamepilot.remix import swap_to_regular, swap_to_debug, get_active_runtime


@pytest.fixture
def mock_remix_dirs(tmp_path, monkeypatch):
    game_dir = tmp_path / "game"
    game_dir.mkdir()
    debug_dir = tmp_path / "debug"
    debug_dir.mkdir()

    monkeypatch.setattr("gamepilot.remix.GAME_DIR", game_dir)
    monkeypatch.setattr("gamepilot.remix.DEBUG_RUNTIME", debug_dir)
    monkeypatch.setattr("gamepilot.remix.RUNTIME_MARKER", game_dir / ".runtime_type")

    return game_dir, debug_dir


def test_swap_to_regular_already_regular(mock_remix_dirs, capsys):
    game_dir, _ = mock_remix_dirs
    # By default, without marker, get_active_runtime() returns 'regular'

    assert swap_to_regular() is True

    captured = capsys.readouterr()
    assert "[remix] Already on regular runtime" in captured.out


def test_swap_to_regular_no_backup(mock_remix_dirs, capsys):
    game_dir, _ = mock_remix_dirs
    marker = game_dir / ".runtime_type"
    marker.write_text("debug")

    assert swap_to_regular() is False

    captured = capsys.readouterr()
    assert "ERROR: No regular runtime backup found" in captured.out


def test_swap_to_regular_success(mock_remix_dirs, capsys):
    game_dir, _ = mock_remix_dirs
    marker = game_dir / ".runtime_type"
    marker.write_text("debug")

    # Create a fake backup
    backup_dir = game_dir / ".runtime_backup_regular"
    backup_dir.mkdir()

    # Fake backup files
    (backup_dir / "d3d9.dll").write_text("regular d3d9")
    (backup_dir / ".trex").mkdir()
    (backup_dir / ".trex" / "test.txt").write_text("trex data")

    # Fake current debug files
    (game_dir / "d3d9.dll").write_text("debug d3d9")
    (game_dir / ".trex").mkdir()

    assert swap_to_regular() is True

    # Check marker updated
    assert marker.read_text().strip() == "regular"

    # Check debug was backed up
    debug_backup = game_dir / ".runtime_backup_debug"
    assert debug_backup.exists()
    assert (debug_backup / "d3d9.dll").read_text() == "debug d3d9"

    # Check regular was restored
    assert (game_dir / "d3d9.dll").read_text() == "regular d3d9"
    assert (game_dir / ".trex" / "test.txt").read_text() == "trex data"


def test_swap_to_debug_already_debug(mock_remix_dirs, capsys):
    game_dir, debug_dir = mock_remix_dirs
    debug_dir.mkdir(exist_ok=True)
    (debug_dir / ".trex").mkdir()

    marker = game_dir / ".runtime_type"
    marker.write_text("debug")

    assert swap_to_debug() is True

    captured = capsys.readouterr()
    assert "[remix] Already on debug runtime" in captured.out


def test_swap_to_debug_no_debug_runtime(mock_remix_dirs, capsys):
    game_dir, debug_dir = mock_remix_dirs
    debug_dir.rmdir()  # remove the directory so it doesn't exist

    assert swap_to_debug() is False

    captured = capsys.readouterr()
    assert "ERROR: Debug runtime not found" in captured.out


def test_swap_to_debug_no_trex(mock_remix_dirs, capsys):
    game_dir, debug_dir = mock_remix_dirs
    # debug_dir exists, but no .trex

    assert swap_to_debug() is False

    captured = capsys.readouterr()
    assert "ERROR: No .trex in debug runtime" in captured.out


def test_swap_to_debug_success(mock_remix_dirs, capsys):
    game_dir, debug_dir = mock_remix_dirs
    (debug_dir / ".trex").mkdir()
    (debug_dir / ".trex" / "debug.txt").write_text("debug trex")
    (debug_dir / "d3d9.dll").write_text("debug d3d9")

    (game_dir / ".trex").mkdir()
    (game_dir / ".trex" / "reg.txt").write_text("reg trex")
    (game_dir / "d3d9.dll").write_text("reg d3d9")

    assert swap_to_debug() is True

    marker = game_dir / ".runtime_type"
    assert marker.read_text().strip() == "debug"

    # Check backup of regular exists
    backup_dir = game_dir / ".runtime_backup_regular"
    assert backup_dir.exists()
    assert (backup_dir / "d3d9.dll").read_text() == "reg d3d9"
    assert (backup_dir / ".trex" / "reg.txt").exists()

    # Check debug is copied into game dir
    assert (game_dir / "d3d9.dll").read_text() == "debug d3d9"
    assert (game_dir / ".trex" / "debug.txt").exists()


def test_get_active_runtime(mock_remix_dirs):
    game_dir, _ = mock_remix_dirs
    marker = game_dir / ".runtime_type"

    # Test fallback
    assert get_active_runtime() == "regular"

    # Test reading marker
    marker.write_text("debug\n")
    assert get_active_runtime() == "debug"
