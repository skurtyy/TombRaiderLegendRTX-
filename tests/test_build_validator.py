import hashlib
import pytest
from automation.build_validator import compute_md5


def test_compute_md5_empty(tmp_path):
    f = tmp_path / "empty.txt"
    f.touch()

    expected = hashlib.md5(b"").hexdigest()
    assert compute_md5(f) == expected
    assert compute_md5(str(f)) == expected


def test_compute_md5_short(tmp_path):
    f = tmp_path / "short.txt"
    content = b"hello world"
    f.write_bytes(content)

    expected = hashlib.md5(content).hexdigest()
    assert compute_md5(f) == expected


def test_compute_md5_large(tmp_path):
    f = tmp_path / "large.txt"
    content = b"A" * (65536 * 2 + 100)
    f.write_bytes(content)

    expected = hashlib.md5(content).hexdigest()
    assert compute_md5(f) == expected


def test_compute_md5_non_existent(tmp_path):
    f = tmp_path / "nonexistent.txt"
    with pytest.raises(FileNotFoundError):
        compute_md5(f)
