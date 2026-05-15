import sys
import hashlib
from pathlib import Path

import pytest

# Add the repository root to sys.path so we can import 'automation'
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.build_validator import compute_md5


def test_compute_md5_empty_file(tmp_path: Path):
    """Test computing MD5 of an empty file (0 bytes)."""
    file_path = tmp_path / "empty.bin"
    file_path.write_bytes(b"")

    expected_md5 = hashlib.md5(b"").hexdigest()
    assert compute_md5(file_path) == expected_md5


def test_compute_md5_normal_file(tmp_path: Path):
    """Test computing MD5 of a normal, small file."""
    file_path = tmp_path / "normal.txt"
    content = b"Hello, World! This is a test file."
    file_path.write_bytes(content)

    expected_md5 = hashlib.md5(content).hexdigest()
    assert compute_md5(file_path) == expected_md5


def test_compute_md5_large_file_chunking(tmp_path: Path):
    """Test computing MD5 of a file larger than the chunk size (65536 bytes)."""
    file_path = tmp_path / "large.bin"

    # Create a file larger than 65536 bytes to test the chunking logic.
    # We will make it 2.5 times the chunk size to ensure multiple reads.
    chunk_size = 65536
    content = b"A" * (int(chunk_size * 2.5))
    file_path.write_bytes(content)

    expected_md5 = hashlib.md5(content).hexdigest()
    assert compute_md5(file_path) == expected_md5


def test_compute_md5_file_not_found(tmp_path: Path):
    """Test that a FileNotFoundError is raised when the file does not exist."""
    file_path = tmp_path / "does_not_exist.txt"

    with pytest.raises(FileNotFoundError):
        compute_md5(file_path)
