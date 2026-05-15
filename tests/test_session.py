import json
from pathlib import Path
from unittest.mock import patch

import pytest

from gamepilot.session import Session


def test_save_artifact_success_default_name(tmp_path):
    source_file = tmp_path / "source.txt"
    source_file.write_text("hello artifact")

    session_dir = tmp_path / "session"

    with Session(goal="test", session_dir=session_dir) as session:
        result = session.save_artifact(source_file)

        assert result is not None
        assert result.exists()
        assert result.name == "source.txt"
        assert result.read_text() == "hello artifact"
        assert result.parent == session.session_dir

    # Verify log after session is closed
    log_content = session._log_path.read_text()
    assert "artifact_saved" in log_content
    assert str(source_file).replace("\\", "\\\\") in log_content.replace("\\\\", "\\") or str(source_file) in log_content


def test_save_artifact_success_custom_name(tmp_path):
    source_file = tmp_path / "source.txt"
    source_file.write_text("hello artifact custom")

    session_dir = tmp_path / "session"

    with Session(goal="test custom name", session_dir=session_dir) as session:
        result = session.save_artifact(source_file, dest_name="custom.log")

        assert result is not None
        assert result.exists()
        assert result.name == "custom.log"
        assert result.read_text() == "hello artifact custom"
        assert result.parent == session.session_dir

    # Verify log
    log_content = session._log_path.read_text()
    assert "artifact_saved" in log_content
    assert "custom.log" in log_content


def test_save_artifact_missing_source(tmp_path):
    missing_file = tmp_path / "does_not_exist.txt"
    session_dir = tmp_path / "session"

    with Session(goal="test missing source", session_dir=session_dir) as session:
        result = session.save_artifact(missing_file)

        assert result is None

    # Verify log
    log_content = session._log_path.read_text()
    assert "artifact_missing" in log_content
    assert str(missing_file).replace("\\", "\\\\") in log_content.replace("\\\\", "\\") or str(missing_file) in log_content


def test_save_artifact_copy_failure(tmp_path):
    source_file = tmp_path / "source.txt"
    source_file.write_text("hello artifact")

    session_dir = tmp_path / "session"

    with Session(goal="test copy failure", session_dir=session_dir) as session:
        # Mock shutil.copy2 to raise an exception
        with patch("gamepilot.session.shutil.copy2", side_effect=PermissionError("Permission denied")):
            result = session.save_artifact(source_file)

            assert result is None

    # Verify log
    log_content = session._log_path.read_text()
    assert "artifact_save_failed" in log_content
    assert "Permission denied" in log_content
