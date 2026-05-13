import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.build_validator import compute_md5

def test_compute_md5_happy_path_string(tmp_path: Path):
    test_file = tmp_path / "test.txt"
    content = b"hello world"
    test_file.write_bytes(content)

    expected_md5 = hashlib.md5(content).hexdigest()
    assert compute_md5(str(test_file)) == expected_md5

def test_compute_md5_happy_path_path(tmp_path: Path):
    test_file = tmp_path / "test.txt"
    content = b"hello world"
    test_file.write_bytes(content)

    expected_md5 = hashlib.md5(content).hexdigest()
    assert compute_md5(test_file) == expected_md5

def test_compute_md5_empty_file(tmp_path: Path):
    test_file = tmp_path / "empty.txt"
    test_file.touch()

    expected_md5 = hashlib.md5(b"").hexdigest()
    assert compute_md5(test_file) == expected_md5

def test_compute_md5_large_file(tmp_path: Path):
    # Create file larger than chunk size (65536 bytes)
    test_file = tmp_path / "large.bin"
    # 100 KB
    content = b"a" * 102400
    test_file.write_bytes(content)

    expected_md5 = hashlib.md5(content).hexdigest()
    assert compute_md5(test_file) == expected_md5

def test_compute_md5_file_not_found():
    with pytest.raises(FileNotFoundError):
        compute_md5("non_existent_file.txt")
