"""Nightly report writers."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .model import CandidateResult, RunState
from .scoring import promotion_key


def rank_results(results: list[CandidateResult]) -> list[CandidateResult]:
    return sorted(results, key=promotion_key, reverse=True)


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_candidate_reviews(run_dir: Path, results: list[CandidateResult]) -> Path:
    reviews_dir = run_dir / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    for result in results:
        payload = result.to_dict()
        payload["review"] = dict(result.review)
        _write_json(reviews_dir / f"{result.candidate_id}.json", payload)
    return reviews_dir


def write_curated_artifacts(
    run_dir: Path,
    ranked_results: list[CandidateResult],
    *,
    limit: int,
) -> Path:
    curated_dir = run_dir / "curated"
    curated_dir.mkdir(parents=True, exist_ok=True)
    for result in ranked_results[:limit]:
        candidate_dir = curated_dir / result.candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        scenes = result.artifacts.get("scenes", {})
        for scene_id, scene_artifacts in scenes.items():
            clean_paths = list(scene_artifacts.get("clean", []))
            if clean_paths:
                src = Path(clean_paths[0])
                if src.exists():
                    shutil.copy2(src, candidate_dir / f"{scene_id}-{src.name}")
        log_path = result.artifacts.get("log_path")
        if log_path and Path(log_path).exists():
            excerpt = "\n".join(Path(log_path).read_text(encoding="utf-8", errors="replace").splitlines()[:80])
            (candidate_dir / "ffp_proxy_excerpt.txt").write_text(excerpt + "\n", encoding="utf-8")
    return curated_dir


def write_leaderboard(
    run_dir: Path,
    baseline: CandidateResult,
    ranked_results: list[CandidateResult],
) -> Path:
    payload = {
        "baseline": baseline.to_dict(),
        "leaderboard": [result.to_dict() for result in ranked_results],
    }
    return _write_json(run_dir / "leaderboard.json", payload)


def write_summary(
    run_dir: Path,
    state: RunState,
    baseline: CandidateResult,
    ranked_results: list[CandidateResult],
) -> Path:
    lines = [
        f"# TRL Nightly Run {state.run_id}",
        "",
        f"- Status: `{state.status}`",
        f"- Phase: `{state.phase}`",
        f"- Screened leader: `{state.screen_winner_id or 'none'}`",
        f"- Release-gated winner: `{state.winner_id or 'none'}`",
        f"- Requested hours: `{state.hours_requested}`",
        f"- Scene matrix: {', '.join(state.scene_ids)}",
        f"- Branch: `{state.branch_name}`",
        f"- Rolling draft branch: `{state.rolling_branch_name}`",
        "",
        "## Baseline",
        "",
        f"- Verdict: `{baseline.verdict}`",
        f"- Hard gate: `{baseline.hard_gate_pass}`",
        f"- Screen pass: `{baseline.screen_pass}`",
        f"- Release pass: `{baseline.release_pass}`",
        f"- Sky: `{baseline.sky_pass}`",
        f"- Water: `{baseline.water_pass}`",
        f"- Hash retention: `{baseline.hash_retention_pct:.2f}`",
        f"- Water motion ratio: `{baseline.water_motion_ratio:.2f}`",
        "",
        "## Leaderboard",
        "",
    ]
    for result in ranked_results[:10]:
        lines.extend(
            [
                f"### {result.candidate_id}",
                "",
                f"- Class: `{result.mutation_class}`",
                f"- Verdict: `{result.review.get('verdict', result.verdict)}`",
                f"- Hard/Sky/Water: `{result.hard_gate_pass}` / `{result.sky_pass}` / `{result.water_pass}`",
                f"- Screen/Release: `{result.screen_pass}` / `{result.release_pass}`",
                f"- Hash retention: `{result.hash_retention_pct:.2f}`",
                f"- Sky non-void: `{result.sky_non_void_pct:.2f}`",
                f"- Sky contamination: `{result.sky_contamination_pct:.2f}`",
                f"- Water motion ratio: `{result.water_motion_ratio:.2f}`",
                f"- p95/median CPU ms: `{result.performance_p95_cpu_ms:.2f}` / `{result.performance_median_cpu_ms:.2f}`",
            ]
        )
        failure_modes = result.review.get("failure_modes") or result.failure_modes
        if failure_modes:
            lines.append(f"- Failure modes: {', '.join(str(item) for item in failure_modes)}")
        next_hypotheses = result.review.get("next_hypotheses") or result.next_hypotheses
        if next_hypotheses:
            lines.append(f"- Next hypotheses: {', '.join(str(item) for item in next_hypotheses)}")
        lines.append("")
    path = run_dir / "nightly_summary.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_publication_payload(
    run_dir: Path,
    payload: dict[str, object],
) -> Path:
    return _write_json(run_dir / "publication_payload.json", payload)
