import pytest
from automation.build_validator import get_file_metrics, ArtifactMetrics


def test_get_file_metrics_valid_file(tmp_path):
    # Create a dummy file with known content
    test_file = tmp_path / "dummy.txt"
    content = b"hello world"
    test_file.write_bytes(content)

    metrics = get_file_metrics(test_file)

    assert isinstance(metrics, ArtifactMetrics)
    assert metrics.path == str(test_file)
    assert metrics.size_bytes == len(content)

    # Calculate expected md5
    import hashlib

    expected_md5 = hashlib.md5(content).hexdigest()
    assert metrics.md5 == expected_md5


def test_get_file_metrics_string_path(tmp_path):
    test_file = tmp_path / "dummy2.txt"
    content = b"another test"
    test_file.write_bytes(content)

    metrics = get_file_metrics(str(test_file))
    assert metrics.path == str(test_file)
    assert metrics.size_bytes == len(content)


def test_get_file_metrics_not_found(tmp_path):
    missing_file = tmp_path / "nonexistent.dll"

    with pytest.raises(FileNotFoundError, match="Artifact not found"):
        get_file_metrics(missing_file)


def test_get_file_metrics_directory(tmp_path):
    # Should raise FileNotFoundError if path is a directory
    with pytest.raises(FileNotFoundError, match="Artifact not found"):
        get_file_metrics(tmp_path)
