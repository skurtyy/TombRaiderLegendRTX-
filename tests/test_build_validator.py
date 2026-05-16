import sys
import hashlib
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.build_validator import get_file_metrics, ArtifactMetrics


def test_get_file_metrics_success(tmp_path):
    test_file = tmp_path / "test.dll"
    content = b"test content"
    test_file.write_bytes(content)

    expected_md5 = hashlib.md5(content).hexdigest()

    metrics = get_file_metrics(test_file)

    assert isinstance(metrics, ArtifactMetrics)
    assert metrics.path == str(test_file)
    assert metrics.md5 == expected_md5
    assert metrics.size_bytes == len(content)


def test_get_file_metrics_not_found(tmp_path):
    test_file = tmp_path / "nonexistent.dll"

    with pytest.raises(FileNotFoundError, match="Artifact not found"):
        get_file_metrics(test_file)
