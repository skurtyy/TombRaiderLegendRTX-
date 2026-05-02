"""Build artifact validator — enforces md5sum + stat verification.

Fixes issue #148: build-validator was hallucinating d3d9.dll sizes.
All reported metrics MUST come from subprocess output, never from
free-form text generation.

Usage:
    python automation/build_validator.py [path/to/d3d9.dll]

Baseline (build-041):
    md5: 9016bcdd...  size: 1,183,232 bytes
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


class ArtifactMetrics(NamedTuple):
    path: str
    md5: str
    size_bytes: int

    def __str__(self) -> str:
        return f"{self.path}: md5={self.md5}  size={self.size_bytes:,} bytes"


# Build-041 confirmed baseline — used as smoke-test regression gate.
BUILD_041_BASELINE = ArtifactMetrics(
    path="d3d9.dll",
    md5="9016bcdd",  # first 8 chars; update with full hash after confirmation
    size_bytes=1_183_232,
)


def compute_md5(file_path: str | Path) -> str:
    """Compute MD5 by reading the file directly — no subprocess, no hallucination."""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_file_metrics(file_path: str | Path) -> ArtifactMetrics:
    """
    Return ArtifactMetrics by reading the file directly.
    Values are derived from actual I/O, never from free-form generation.
    """
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"Artifact not found: {file_path}")

    md5_hex = compute_md5(p)
    size = p.stat().st_size
    return ArtifactMetrics(path=str(p), md5=md5_hex, size_bytes=size)


def assert_metrics_match(actual: ArtifactMetrics, expected: ArtifactMetrics) -> None:
    """
    Raise AssertionError if size mismatches. MD5 prefix check (first 8 chars)
    when a partial baseline is stored; full check when full hash is known.
    """
    if actual.size_bytes != expected.size_bytes:
        raise AssertionError(
            f"Size mismatch: expected {expected.size_bytes:,} bytes, "
            f"got {actual.size_bytes:,} bytes\n"
            f"Actual:   {actual}\n"
            f"Expected: {expected}"
        )

    expected_md5 = expected.md5
    actual_md5 = actual.md5
    # Partial-prefix comparison when baseline stores only first N chars
    if actual_md5[: len(expected_md5)] != expected_md5:
        raise AssertionError(
            f"MD5 mismatch: expected prefix {expected_md5!r}, "
            f"got {actual_md5!r}\n"
            f"Actual:   {actual}\n"
            f"Expected: {expected}"
        )


def validate_build_artifact(
    dll_path: str | Path,
    baseline: ArtifactMetrics | None = None,
    *,
    verbose: bool = True,
) -> ArtifactMetrics:
    """
    Validate a build artifact by computing its actual metrics and optionally
    asserting against a known baseline.

    This is the single authoritative function for reporting build metrics.
    Callers MUST report the returned ArtifactMetrics, not their own text.
    """
    metrics = get_file_metrics(dll_path)
    if verbose:
        print(f"[validator] {metrics}")

    if baseline is not None:
        assert_metrics_match(metrics, baseline)
        if verbose:
            print(f"[validator] PASS — matches baseline {baseline.md5[:8]}... {baseline.size_bytes:,} bytes")

    return metrics


def main() -> int:
    dll_path = sys.argv[1] if len(sys.argv) > 1 else "d3d9.dll"

    try:
        metrics = validate_build_artifact(dll_path, baseline=None, verbose=True)
        print(f"\nValidation complete. Report these verbatim values:")
        print(f"  md5  = {metrics.md5}")
        print(f"  size = {metrics.size_bytes:,} bytes")
        return 0
    except FileNotFoundError as e:
        print(f"[validator] ERROR: {e}", file=sys.stderr)
        return 2
    except AssertionError as e:
        print(f"[validator] FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
