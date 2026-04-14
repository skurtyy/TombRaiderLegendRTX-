"""Persistent iteration history backed by the unified nightly experiment ledger."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

from patches.TombRaiderLegend.nightly.ledger import ExperimentLedger

# Addresses already tried in builds 001-044 (extracted from proxy defines and build history).
# These won't be re-generated as hypotheses.
SEED_TRIED_ADDRS = [
    0x407150, 0x4072BD, 0x4072D2, 0x407AF1, 0x407B30, 0x407B49,
    0x407B62, 0x407B7B, 0x4071CE, 0x407976, 0x407B06, 0x407ABC,
    0x40AE3E, 0x454AB0, 0x40E30F, 0x40E3B0, 0x40E2CA, 0x40E2D7,
    0x40E33A, 0x40E349, 0x40E359, 0x60CE20, 0x60B050, 0xEC6337,
    0x603AE6, 0x60E3B1, 0x40EEA7, 0x46C194, 0x46C19D, 0x46B85A,
    0x4071D9,  # code cave trampoline
    0xEFDD64,  # frustum threshold stamp
    0xF2A0D4, 0xF2A0D8, 0xF2A0DC,  # cull mode globals
    0x436740, 0x4367CD,  # ProcessPendingRemovals
]


@dataclass
class IterationRecord:
    id: str
    timestamp: float
    hypothesis_id: str
    description: str
    target_addr: int
    patch_bytes: str
    patch_type: str
    passed: bool
    crashed: bool
    confidence: float
    notes: str = ""


@dataclass
class KnowledgeBase:
    iterations: list[dict] = field(default_factory=list)
    confirmed_patches: list[dict] = field(default_factory=list)
    blacklisted_addrs: list[int] = field(default_factory=list)
    diagnostic_results: list[dict] = field(default_factory=list)
    tried_addrs: list[int] = field(default_factory=lambda: list(SEED_TRIED_ADDRS))

    def save(self) -> None:
        ledger = ExperimentLedger.load()
        autopatch = ledger.autopatch_section()
        autopatch["iterations"] = list(self.iterations)
        autopatch["confirmed_patches"] = list(self.confirmed_patches)
        autopatch["blacklisted_addrs"] = list(self.blacklisted_addrs)
        autopatch["diagnostic_results"] = list(self.diagnostic_results)
        autopatch["tried_addrs"] = list(self.tried_addrs)
        ledger.save()

    @classmethod
    def load(cls) -> "KnowledgeBase":
        ledger = ExperimentLedger.load()
        autopatch = ledger.autopatch_section()
        kb = cls(
            iterations=list(autopatch.get("iterations", [])),
            confirmed_patches=list(autopatch.get("confirmed_patches", [])),
            blacklisted_addrs=list(autopatch.get("blacklisted_addrs", [])),
            diagnostic_results=list(autopatch.get("diagnostic_results", [])),
            tried_addrs=list(autopatch.get("tried_addrs", [])),
        )
        for addr in SEED_TRIED_ADDRS:
            if addr not in kb.tried_addrs:
                kb.tried_addrs.append(addr)
        kb.save()
        return kb

    def is_tried(self, addr: int) -> bool:
        return addr in self.tried_addrs

    def is_blacklisted(self, addr: int) -> bool:
        return addr in self.blacklisted_addrs

    def record_iteration(self, rec: IterationRecord) -> None:
        self.iterations.append(asdict(rec))
        if rec.target_addr not in self.tried_addrs:
            self.tried_addrs.append(rec.target_addr)
        if rec.crashed:
            crash_count = sum(
                1 for it in self.iterations
                if it.get("target_addr") == rec.target_addr and it.get("crashed")
            )
            if crash_count >= 3 and rec.target_addr not in self.blacklisted_addrs:
                self.blacklisted_addrs.append(rec.target_addr)
        if rec.passed:
            self.confirmed_patches.append({
                "addr": rec.target_addr,
                "bytes": rec.patch_bytes,
                "hypothesis_id": rec.hypothesis_id,
                "description": rec.description,
            })
        self.save()

    def record_diagnostic(self, result: dict[str, Any]) -> None:
        self.diagnostic_results.append({
            "timestamp": time.time(),
            **result,
        })
        self.save()

    def next_iteration_id(self) -> str:
        return f"iter_{45 + len(self.iterations):03d}"

    def consecutive_failures(self) -> int:
        count = 0
        for it in reversed(self.iterations):
            if it.get("passed"):
                break
            count += 1
        return count
