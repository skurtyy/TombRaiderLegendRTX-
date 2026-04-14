"""Deterministic screenshot and performance scoring for nightly candidates."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .model import CandidateResult, Rect

_DEFAULT_WATER_MIN_ABS_ENERGY = 1.0
_DEFAULT_WATER_BACKGROUND_FLOOR = 0.5
_DEFAULT_WATER_RATIO_CAP = 64.0


@dataclass
class SkyFrameMeasurement:
    non_void_pct: float
    contamination_pct: float


@dataclass
class WaterMotionMeasurement:
    water_energy: float
    background_energy: float
    ratio: float


def _threshold_value(thresholds: dict[str, float] | None, key: str, default: float) -> float:
    if thresholds is None:
        return default
    value = thresholds.get(key)
    return float(default if value is None else value)


def _load_rgb(path: str | Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)


def _crop(arr: np.ndarray, rect: Rect) -> np.ndarray:
    height, width = arr.shape[:2]
    left, top, right, bottom = rect.as_box(width, height)
    return arr[top:bottom, left:right]


def measure_sky_frame(path: str | Path, roi: Rect) -> SkyFrameMeasurement:
    arr = _crop(_load_rgb(path), roi)
    brightness = arr.mean(axis=2)
    saturation = arr.max(axis=2) - arr.min(axis=2)
    non_void_pct = float((brightness > 12.0).mean() * 100.0)

    grad_x = np.abs(np.diff(brightness, axis=1))
    grad_y = np.abs(np.diff(brightness, axis=0))
    edge = np.hypot(grad_x[:-1, :], grad_y[:, :-1])
    contamination = ((saturation[:-1, :-1] > 35.0) | (edge > 18.0)).mean()
    return SkyFrameMeasurement(
        non_void_pct=non_void_pct,
        contamination_pct=float(contamination * 100.0),
    )


def evaluate_sky_frames(paths: list[str | Path], roi: Rect, thresholds: dict[str, float]) -> tuple[bool, float, float]:
    if not paths:
        return False, 0.0, 100.0
    frames = [measure_sky_frame(path, roi) for path in paths]
    min_non_void = min(frame.non_void_pct for frame in frames)
    max_contamination = max(frame.contamination_pct for frame in frames)
    passed = (
        min_non_void >= thresholds["sky_non_void_min_pct"]
        and max_contamination <= thresholds["sky_contamination_max_pct"]
    )
    return passed, min_non_void, max_contamination


def evaluate_hash_stability(paths: list[str | Path], roi: Rect, tolerance: int = 4) -> float:
    if len(paths) < 2:
        return 0.0
    frames = [_crop(_load_rgb(path), roi) for path in paths]
    baseline = frames[0]
    stable_mask = np.ones(baseline.shape[:2], dtype=bool)
    for frame in frames[1:]:
        delta = np.max(np.abs(frame - baseline), axis=2)
        stable_mask &= delta <= tolerance
    return float(stable_mask.mean() * 100.0)


def evaluate_water_motion(
    paths: list[str | Path],
    water_roi: Rect,
    background_roi: Rect,
    thresholds: dict[str, float] | None = None,
) -> WaterMotionMeasurement:
    if len(paths) < 2:
        return WaterMotionMeasurement(0.0, 0.0, 0.0)
    frames = [_load_rgb(path) for path in paths]
    water_energy = 0.0
    background_energy = 0.0
    comparisons = 0
    for previous, current in zip(frames, frames[1:]):
        water_prev = _crop(previous, water_roi)
        water_curr = _crop(current, water_roi)
        background_prev = _crop(previous, background_roi)
        background_curr = _crop(current, background_roi)
        water_energy += float(np.abs(water_curr - water_prev).mean())
        background_energy += float(np.abs(background_curr - background_prev).mean())
        comparisons += 1
    if comparisons:
        water_energy /= comparisons
        background_energy /= comparisons
    min_water_energy = _threshold_value(thresholds, "water_motion_abs_min", _DEFAULT_WATER_MIN_ABS_ENERGY)
    background_floor = _threshold_value(thresholds, "water_background_floor", _DEFAULT_WATER_BACKGROUND_FLOOR)
    ratio_cap = _threshold_value(thresholds, "water_motion_ratio_cap", _DEFAULT_WATER_RATIO_CAP)
    if water_energy < min_water_energy:
        ratio = 0.0
    else:
        ratio = min(water_energy / max(background_energy, background_floor), ratio_cap)
    return WaterMotionMeasurement(water_energy, background_energy, float(ratio))


def promotion_key(result: CandidateResult) -> tuple[float, ...]:
    return tuple(result.deterministic_score)


def beats_baseline(candidate: CandidateResult, baseline: CandidateResult) -> bool:
    if not candidate.screen_pass:
        return False
    if not baseline.screen_pass:
        return True
    return promotion_key(candidate) > promotion_key(baseline)


def build_candidate_result(
    candidate_id: str,
    mutation_class: str,
    description: str,
    *,
    crashed: bool,
    hard_gate_pass: bool,
    sky_pass: bool,
    water_pass: bool,
    release_pass: bool,
    hash_retention_pct: float,
    sky_non_void_pct: float,
    sky_contamination_pct: float,
    water_motion_ratio: float,
    performance_p95_cpu_ms: float,
    performance_median_cpu_ms: float,
    required_patch_hits: dict[str, bool],
    failure_modes: list[str],
    next_hypotheses: list[str],
    artifacts: dict[str, object],
) -> CandidateResult:
    finite_p95 = performance_p95_cpu_ms if np.isfinite(performance_p95_cpu_ms) else 9999.0
    finite_median = performance_median_cpu_ms if np.isfinite(performance_median_cpu_ms) else 9999.0
    score = [
        1.0 if hard_gate_pass else 0.0,
        1.0 if sky_pass else 0.0,
        1.0 if water_pass else 0.0,
        hash_retention_pct,
        sky_non_void_pct,
        -sky_contamination_pct,
        water_motion_ratio,
        -finite_p95,
        -finite_median,
    ]
    screen_pass = hard_gate_pass and sky_pass and water_pass
    promotion_eligible = screen_pass and release_pass
    if promotion_eligible:
        verdict = "promote"
    elif screen_pass:
        verdict = "screened"
    else:
        verdict = "reject"
    return CandidateResult(
        candidate_id=candidate_id,
        mutation_class=mutation_class,
        description=description,
        crashed=crashed,
        hard_gate_pass=hard_gate_pass,
        sky_pass=sky_pass,
        water_pass=water_pass,
        screen_pass=screen_pass,
        release_pass=release_pass,
        hash_retention_pct=float(hash_retention_pct),
        sky_non_void_pct=float(sky_non_void_pct),
        sky_contamination_pct=float(sky_contamination_pct),
        water_motion_ratio=float(water_motion_ratio),
        performance_p95_cpu_ms=float(finite_p95),
        performance_median_cpu_ms=float(finite_median),
        deterministic_score=[float(value) for value in score],
        promotion_eligible=promotion_eligible,
        verdict=verdict,
        failure_modes=list(failure_modes),
        next_hypotheses=list(next_hypotheses),
        required_patch_hits=dict(required_patch_hits),
        artifacts=dict(artifacts),
    )
