import pytest
from automation.build_validator import get_file_metrics, ArtifactMetrics


def test_get_file_metrics_valid_file(tmp_path):
    test_file = tmp_path / "test_artifact.dll"
    content = b"fake dll content"
    test_file.write_bytes(content)

    metrics = get_file_metrics(test_file)

    assert isinstance(metrics, ArtifactMetrics)
    assert metrics.path == str(test_file)
    assert metrics.size_bytes == len(content)
    # The MD5 of "fake dll content" can be pre-calculated or checked for correctness
    import hashlib

    expected_md5 = hashlib.md5(content).hexdigest()
    assert metrics.md5 == expected_md5


def test_get_file_metrics_not_found(tmp_path):
    missing_file = tmp_path / "missing.dll"

    with pytest.raises(FileNotFoundError, match="Artifact not found:"):
        get_file_metrics(missing_file)


def test_get_file_metrics_directory(tmp_path):
    directory = tmp_path / "somedir"
    directory.mkdir()

    with pytest.raises(FileNotFoundError, match="Artifact not found:"):
        get_file_metrics(directory)
