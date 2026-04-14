"""Nightly candidate generation."""
from __future__ import annotations

import json
from pathlib import Path

from autopatch.hypothesis import generate_from_diagnostic

from .ledger import ExperimentLedger
from .model import CandidateResult, CandidateSpec, NightlyConfig

DIAGNOSTIC_REPORT_PATH = Path(__file__).resolve().parents[3] / "autopatch" / "diagnostic_captures" / "diagnostic_report.json"


def _config_candidates() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            candidate_id="cfg-sky-wide",
            mutation_class="config_only",
            description="Lower sky candidate thresholds in proxy.ini for wider Bolivia sky capture",
            proxy_overrides={
                "Sky": {
                    "CandidateMinVerts": 8000,
                    "CandidateMinPrims": 18,
                    "WarmupScenes": 120,
                }
            },
        ),
        CandidateSpec(
            candidate_id="cfg-sky-fastwarm",
            mutation_class="config_only",
            description="Accelerate sky warmup and push Bolivia sky brightness above the manual baseline",
            proxy_overrides={
                "Sky": {
                    "CandidateMinVerts": 6000,
                    "CandidateMinPrims": 12,
                    "WarmupScenes": 60,
                }
            },
            rtx_overrides={"rtx.skyBrightness": 2.5},
        ),
        CandidateSpec(
            candidate_id="cfg-water-tag",
            mutation_class="config_only",
            description="Strengthen animated-water tagging in rtx.conf while preserving current proxy",
            rtx_overrides={
                "rtx.translucentMaterial.animatedWaterEnable": True,
                "rtx.opaqueMaterial.layeredWaterNormalEnable": True,
            },
        ),
        CandidateSpec(
            candidate_id="cfg-anchor-refresh",
            mutation_class="config_only",
            description="Anchor-refresh control candidate using the tracked mod.usda manifest only",
        ),
    ]


def _load_latest_diagnostic(ledger: ExperimentLedger) -> dict | None:
    autopatch = ledger.autopatch_section()
    if autopatch.get("diagnostic_results"):
        return autopatch["diagnostic_results"][-1]
    if DIAGNOSTIC_REPORT_PATH.exists():
        return json.loads(DIAGNOSTIC_REPORT_PATH.read_text(encoding="utf-8"))
    return None


def _runtime_candidates(
    config: NightlyConfig,
    ledger: ExperimentLedger,
) -> list[CandidateSpec]:
    runtime_cfg = dict(config.mutation_classes.get("runtime_hypothesis", {}))
    if not runtime_cfg.get("enabled", True):
        return []
    diagnostic = _load_latest_diagnostic(ledger)
    if not diagnostic:
        return [
            CandidateSpec(
                candidate_id="rt-diagnostic-refresh",
                mutation_class="runtime_hypothesis",
                description="Fallback runtime candidate while diagnostic capture history is absent",
                runtime_patch={"engine": "autopatch", "mode": "no_op"},
            )
        ]

    autopatch = ledger.autopatch_section()
    hypotheses = generate_from_diagnostic(
        diagnostic,
        tried_addrs=list(autopatch.get("tried_addrs", [])),
        blacklisted_addrs=list(autopatch.get("blacklisted_addrs", [])),
        max_hypotheses=int(runtime_cfg.get("count", 8)),
    )
    specs: list[CandidateSpec] = []
    for hypothesis in hypotheses:
        specs.append(
            CandidateSpec(
                candidate_id=f"rt-{hypothesis.id.lower()}",
                mutation_class="runtime_hypothesis",
                description=hypothesis.description,
                runtime_patch={
                    "engine": "autopatch",
                    "addr": hypothesis.target_addr,
                    "patch_bytes_hex": hypothesis.patch_bytes.hex(),
                    "original_bytes_hex": hypothesis.original_bytes.hex(),
                    "hypothesis_id": hypothesis.id,
                    "confidence": hypothesis.confidence,
                    "source": hypothesis.source,
                },
            )
        )
    return specs


def generate_initial_candidate_specs(
    config: NightlyConfig,
    ledger: ExperimentLedger,
) -> list[CandidateSpec]:
    specs: list[CandidateSpec] = []
    config_cfg = dict(config.mutation_classes.get("config_only", {}))
    if config_cfg.get("enabled", True):
        specs.extend(_config_candidates()[: int(config_cfg.get("count", 4))])
    specs.extend(_runtime_candidates(config, ledger))
    return specs[: config.candidate_limit]


def generate_source_candidate_specs(
    config: NightlyConfig,
    parents: list[CandidateResult],
    round_index: int,
    existing_ids: set[str],
) -> list[CandidateSpec]:
    source_cfg = dict(config.mutation_classes.get("source_mutation", {}))
    if not source_cfg.get("enabled", True):
        return []
    templates = list(source_cfg.get("templates", []))
    if not templates:
        return []

    generated: list[CandidateSpec] = []
    max_templates = config.max_source_candidates_per_round
    start = round_index * max_templates
    selected_templates = templates[start : start + max_templates]
    if not selected_templates:
        selected_templates = templates[:max_templates]

    for parent in parents:
        for template in selected_templates:
            candidate_id = f"{parent.candidate_id}-{template}-r{round_index + 1}"
            if candidate_id in existing_ids:
                continue
            generated.append(
                CandidateSpec(
                    candidate_id=candidate_id,
                    mutation_class="source_mutation",
                    description=f"{template} derived from {parent.candidate_id}",
                    source_template=template,
                    parent_candidate_id=parent.candidate_id,
                    round_index=round_index + 1,
                )
            )
    return generated
