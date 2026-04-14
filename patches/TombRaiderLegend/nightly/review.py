"""Structured nightly reviewer output."""
from __future__ import annotations

from .model import CandidateResult
from .scoring import promotion_key


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def review_candidate(
    result: CandidateResult,
    baseline: CandidateResult | None = None,
) -> dict[str, object]:
    """Convert a deterministic result into the structured nightly review schema."""
    failure_modes = list(result.failure_modes)
    next_hypotheses = list(result.next_hypotheses)

    if result.crashed:
        failure_modes.append("crash_during_scene_matrix")
        next_hypotheses.append("reduce mutation scope and re-run the current Bolivia baseline capture before promotion")
    if not result.hard_gate_pass:
        if result.hash_retention_pct < 98.0:
            failure_modes.append("hash_stability_regression")
            next_hypotheses.append("tighten anchor replay or roll back the newest hash-affecting routing change")
        if any(not hit for hit in result.required_patch_hits.values()):
            failure_modes.append("required_memory_patch_missing")
            next_hypotheses.append("verify runtime patch application order before scene evaluation starts")
    if not result.sky_pass:
        failure_modes.append("sky_gate_failed")
        if result.sky_non_void_pct < 70.0:
            next_hypotheses.append("widen sky candidate selection or raise sky brightness tagging")
        if result.sky_contamination_pct > 10.0:
            next_hypotheses.append("tighten sky isolation to avoid world/hash contamination in the vista ROI")
    if not result.water_pass:
        failure_modes.append("water_gate_failed")
        next_hypotheses.append("preserve animated TEX0 routing so waterfall motion survives the proxy path")

    verdict = result.verdict
    if result.screen_pass and not result.release_pass:
        verdict = "screened"
        next_hypotheses.append("run the stage-light end-to-end release gate before final promotion")
    elif result.promotion_eligible:
        if baseline is None or promotion_key(result) > promotion_key(baseline):
            verdict = "promote"
        else:
            verdict = "hold"
            next_hypotheses.append("keep correctness but recover performance before replacing the baseline")
    elif not result.crashed and result.hard_gate_pass and (result.sky_pass or result.water_pass):
        verdict = "investigate"

    return {
        "verdict": verdict,
        "failure_modes": _dedupe(failure_modes),
        "next_hypotheses": _dedupe(next_hypotheses),
    }
