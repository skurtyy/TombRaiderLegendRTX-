import pytest

from automation.build_validator import ArtifactMetrics, assert_metrics_match


def test_match_perfect():
    actual = ArtifactMetrics(
        path="dummy.dll", md5="abcdef1234567890abcdef1234567890", size_bytes=1000
    )
    expected = ArtifactMetrics(
        path="dummy.dll", md5="abcdef1234567890abcdef1234567890", size_bytes=1000
    )
    # Should not raise
    assert_metrics_match(actual, expected)


def test_match_prefix_md5():
    actual = ArtifactMetrics(
        path="dummy.dll", md5="abcdef1234567890abcdef1234567890", size_bytes=1000
    )
    expected = ArtifactMetrics(path="dummy.dll", md5="abcdef12", size_bytes=1000)
    # Should not raise
    assert_metrics_match(actual, expected)


def test_size_mismatch():
    actual = ArtifactMetrics(
        path="dummy.dll", md5="abcdef1234567890abcdef1234567890", size_bytes=1001
    )
    expected = ArtifactMetrics(
        path="dummy.dll", md5="abcdef1234567890abcdef1234567890", size_bytes=1000
    )
    with pytest.raises(AssertionError, match="Size mismatch"):
        assert_metrics_match(actual, expected)


def test_md5_mismatch():
    actual = ArtifactMetrics(
        path="dummy.dll", md5="bbbbef1234567890abcdef1234567890", size_bytes=1000
    )
    expected = ArtifactMetrics(
        path="dummy.dll", md5="abcdef1234567890abcdef1234567890", size_bytes=1000
    )
    with pytest.raises(AssertionError, match="MD5 mismatch"):
        assert_metrics_match(actual, expected)


def test_empty_expected_md5():
    actual = ArtifactMetrics(
        path="dummy.dll", md5="abcdef1234567890abcdef1234567890", size_bytes=1000
    )
    expected = ArtifactMetrics(path="dummy.dll", md5="", size_bytes=1000)
    with pytest.raises(AssertionError, match="Baseline MD5 is empty"):
        assert_metrics_match(actual, expected)
