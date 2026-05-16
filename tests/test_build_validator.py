import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.build_validator import compute_md5


def test_compute_md5_empty_file(tmp_path):
    # Empty file test
    test_file = tmp_path / "empty.txt"
    test_file.write_bytes(b"")

    # d41d8cd98f00b204e9800998ecf8427e is MD5 of empty string
    assert compute_md5(test_file) == "d41d8cd98f00b204e9800998ecf8427e"


def test_compute_md5_small_file(tmp_path):
    # Small file test
    test_file = tmp_path / "small.txt"
    test_file.write_bytes(b"hello world")

    # 5eb63bbbe01eeed093cb22bb8f5acdc3 is MD5 of "hello world"
    assert compute_md5(test_file) == "5eb63bbbe01eeed093cb22bb8f5acdc3"


def test_compute_md5_large_file(tmp_path):
    # Large file test (larger than 65536 chunk size)
    test_file = tmp_path / "large.bin"
    # Create 65536 + 1 byte of "A"
    large_content = b"A" * 65537
    test_file.write_bytes(large_content)

    # We already computed the MD5 of this in an earlier test script
    # It should be f4e97e750d8693097418660e47bd9fb7
    assert compute_md5(test_file) == "f4e97e750d8693097418660e47bd9fb7"


def test_compute_md5_exact_chunk_size(tmp_path):
    # Exact chunk size test
    test_file = tmp_path / "exact.bin"
    exact_content = b"A" * 65536
    test_file.write_bytes(exact_content)

    # MD5 of 65536 'A's
    assert compute_md5(test_file) == "314e20944390bdb0d80b57257c3f1571"
