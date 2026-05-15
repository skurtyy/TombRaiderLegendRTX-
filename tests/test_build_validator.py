import pytest
from automation.build_validator import ArtifactMetrics, assert_metrics_match

def test_assert_metrics_match_success():
    actual = ArtifactMetrics(path="d3d9.dll", md5="1234567890abcdef1234567890abcdef", size_bytes=100)
    expected = ArtifactMetrics(path="d3d9.dll", md5="1234567890abcdef1234567890abcdef", size_bytes=100)
    # Should not raise
    assert_metrics_match(actual, expected)

def test_assert_metrics_match_size_mismatch():
    actual = ArtifactMetrics(path="d3d9.dll", md5="1234567890abcdef1234567890abcdef", size_bytes=100)
    expected = ArtifactMetrics(path="d3d9.dll", md5="1234567890abcdef1234567890abcdef", size_bytes=200)
    with pytest.raises(AssertionError, match="Size mismatch"):
        assert_metrics_match(actual, expected)

def test_assert_metrics_match_md5_mismatch():
    actual = ArtifactMetrics(path="d3d9.dll", md5="1234567890abcdef1234567890abcdef", size_bytes=100)
    expected = ArtifactMetrics(path="d3d9.dll", md5="abcdef1234567890abcdef1234567890", size_bytes=100)
    with pytest.raises(AssertionError, match="MD5 mismatch"):
        assert_metrics_match(actual, expected)

def test_assert_metrics_match_empty_baseline_md5():
    actual = ArtifactMetrics(path="d3d9.dll", md5="1234567890abcdef1234567890abcdef", size_bytes=100)
    expected = ArtifactMetrics(path="d3d9.dll", md5="", size_bytes=100)
    with pytest.raises(AssertionError, match="Baseline MD5 is empty"):
        assert_metrics_match(actual, expected)

def test_assert_metrics_match_md5_prefix_success():
    actual = ArtifactMetrics(path="d3d9.dll", md5="1234567890abcdef1234567890abcdef", size_bytes=100)
    expected = ArtifactMetrics(path="d3d9.dll", md5="12345678", size_bytes=100)
    # Should not raise because actual starts with expected prefix
    assert_metrics_match(actual, expected)
