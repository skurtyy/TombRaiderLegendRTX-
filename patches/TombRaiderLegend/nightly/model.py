"""Shared dataclasses for TRL nightly orchestration."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Rect:
    """Normalized ROI rectangle."""

    x1: float
    y1: float
    x2: float
    y2: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Rect":
        return cls(
            x1=float(data["x1"]),
            y1=float(data["y1"]),
            x2=float(data["x2"]),
            y2=float(data["y2"]),
        )

    def as_box(self, width: int, height: int) -> tuple[int, int, int, int]:
        return (
            int(width * self.x1),
            int(height * self.y1),
            int(width * self.x2),
            int(height * self.y2),
        )


@dataclass
class SceneDefinition:
    """A single scene gate in the TRL nightly matrix."""

    scene_id: str
    label: str
    checkpoint_file: str
    bootstrap_goals: list[str]
    macro_sequence: str = ""
    mouse_moves: list[dict[str, Any]] = field(default_factory=list)
    debug_views: dict[str, int] = field(default_factory=dict)
    capture_hotkeys: list[str] = field(default_factory=lambda: ["]"])
    screenshot_cadence_ms: int = 1200
    hash_capture_count: int = 3
    clean_capture_count: int = 3
    performance_sample_seconds: int = 15
    rois: dict[str, Rect] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SceneDefinition":
        rois = {
            name: Rect.from_dict(rect)
            for name, rect in data.get("rois", {}).items()
        }
        return cls(
            scene_id=data["id"],
            label=data["label"],
            checkpoint_file=data["checkpoint_file"],
            bootstrap_goals=list(data.get("bootstrap_goals", [])),
            macro_sequence=data.get("macro_sequence", ""),
            mouse_moves=list(data.get("mouse_moves", [])),
            debug_views=dict(data.get("debug_views", {})),
            capture_hotkeys=list(data.get("capture_hotkeys", ["]"])),
            screenshot_cadence_ms=int(data.get("screenshot_cadence_ms", 1200)),
            hash_capture_count=int(data.get("hash_capture_count", 3)),
            clean_capture_count=int(data.get("clean_capture_count", 3)),
            performance_sample_seconds=int(data.get("performance_sample_seconds", 15)),
            rois=rois,
            thresholds=dict(data.get("thresholds", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.scene_id,
            "label": self.label,
            "checkpoint_file": self.checkpoint_file,
            "bootstrap_goals": list(self.bootstrap_goals),
            "macro_sequence": self.macro_sequence,
            "mouse_moves": list(self.mouse_moves),
            "debug_views": dict(self.debug_views),
            "capture_hotkeys": list(self.capture_hotkeys),
            "screenshot_cadence_ms": self.screenshot_cadence_ms,
            "hash_capture_count": self.hash_capture_count,
            "clean_capture_count": self.clean_capture_count,
            "performance_sample_seconds": self.performance_sample_seconds,
            "rois": {
                name: asdict(rect)
                for name, rect in self.rois.items()
            },
            "thresholds": dict(self.thresholds),
        }


@dataclass
class NightlyConfig:
    """Tracked nightly configuration."""

    default_hours: int
    candidate_limit: int
    keep_top_candidates: int
    max_source_mutation_rounds: int
    max_source_candidates_per_round: int
    required_patch_tokens: list[str]
    review_rules: dict[str, Any]
    runtime: dict[str, Any]
    publication: dict[str, Any]
    automation: dict[str, Any]
    mutation_classes: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NightlyConfig":
        return cls(
            default_hours=int(data["budgets"]["default_hours"]),
            candidate_limit=int(data["budgets"]["candidate_limit"]),
            keep_top_candidates=int(data["budgets"]["keep_top_candidates"]),
            max_source_mutation_rounds=int(data["budgets"]["max_source_mutation_rounds"]),
            max_source_candidates_per_round=int(data["budgets"]["max_source_candidates_per_round"]),
            required_patch_tokens=list(data.get("required_patch_tokens", [])),
            review_rules=dict(data.get("review", {})),
            runtime=dict(data.get("runtime", {})),
            publication=dict(data.get("publication", {})),
            automation=dict(data.get("automation", {})),
            mutation_classes=dict(data.get("mutation_classes", {})),
        )


@dataclass
class CandidateSpec:
    """One candidate mutation to evaluate."""

    candidate_id: str
    mutation_class: str
    description: str
    proxy_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    rtx_overrides: dict[str, Any] = field(default_factory=dict)
    runtime_patch: dict[str, Any] | None = None
    source_template: str | None = None
    source_params: dict[str, Any] = field(default_factory=dict)
    parent_candidate_id: str | None = None
    round_index: int = 0
    worktree_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateSpec":
        return cls(**data)


@dataclass
class CandidateResult:
    """Deterministic evaluation outcome for a candidate."""

    candidate_id: str
    mutation_class: str
    description: str
    crashed: bool
    hard_gate_pass: bool
    sky_pass: bool
    water_pass: bool
    hash_retention_pct: float
    sky_non_void_pct: float
    sky_contamination_pct: float
    water_motion_ratio: float
    performance_p95_cpu_ms: float
    performance_median_cpu_ms: float
    deterministic_score: list[float]
    promotion_eligible: bool
    verdict: str
    screen_pass: bool = False
    release_pass: bool = False
    failure_modes: list[str] = field(default_factory=list)
    next_hypotheses: list[str] = field(default_factory=list)
    required_patch_hits: dict[str, bool] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    review: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateResult":
        return cls(**data)


@dataclass
class RunState:
    """Serializable run state to support resume/publish."""

    run_id: str
    branch_name: str
    rolling_branch_name: str
    run_dir: str
    started_at: str
    hours_requested: int
    status: str
    phase: str
    scene_ids: list[str]
    candidate_specs: list[dict[str, Any]] = field(default_factory=list)
    candidate_results: list[dict[str, Any]] = field(default_factory=list)
    baseline_result: dict[str, Any] | None = None
    shortlisted_ids: list[str] = field(default_factory=list)
    screen_winner_id: str | None = None
    winner_id: str | None = None
    next_index: int = 0
    source_round_index: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunState":
        return cls(**data)
