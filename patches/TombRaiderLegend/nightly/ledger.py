"""Unified experiment ledger shared by nightly runs and autopatch."""
from __future__ import annotations

import json
from typing import Any

from .model import RunState
from .paths import AUTOPATCH_LEGACY_KNOWLEDGE_PATH, EXPERIMENT_LEDGER_PATH


DEFAULT_AUTOPATCH_SECTION = {
    "iterations": [],
    "confirmed_patches": [],
    "blacklisted_addrs": [],
    "diagnostic_results": [],
    "tried_addrs": [],
}


def _default_ledger() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "autopatch": dict(DEFAULT_AUTOPATCH_SECTION),
        "nightly_runs": [],
        "publication": [],
    }


class ExperimentLedger:
    """Thin JSON-backed ledger with autopatch migration support."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    @classmethod
    def load(cls) -> "ExperimentLedger":
        if EXPERIMENT_LEDGER_PATH.exists():
            return cls(json.loads(EXPERIMENT_LEDGER_PATH.read_text(encoding="utf-8")))

        payload = _default_ledger()
        if AUTOPATCH_LEGACY_KNOWLEDGE_PATH.exists():
            legacy = json.loads(AUTOPATCH_LEGACY_KNOWLEDGE_PATH.read_text(encoding="utf-8"))
            payload["autopatch"] = {
                key: legacy.get(key, value)
                for key, value in DEFAULT_AUTOPATCH_SECTION.items()
            }
        ledger = cls(payload)
        ledger.save()
        return ledger

    def save(self) -> None:
        EXPERIMENT_LEDGER_PATH.write_text(
            json.dumps(self.payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def autopatch_section(self) -> dict[str, Any]:
        self.payload.setdefault("autopatch", dict(DEFAULT_AUTOPATCH_SECTION))
        return self.payload["autopatch"]

    def upsert_run(self, state: RunState) -> None:
        serialized = state.to_dict()
        runs = self.payload.setdefault("nightly_runs", [])
        for index, run in enumerate(runs):
            if run.get("run_id") == state.run_id:
                runs[index] = serialized
                self.save()
                return
        runs.append(serialized)
        self.save()

    def get_run(self, run_id: str) -> RunState | None:
        for run in self.payload.get("nightly_runs", []):
            if run.get("run_id") == run_id:
                return RunState.from_dict(run)
        return None

    def record_publication(self, run_id: str, payload: dict[str, Any]) -> None:
        events = self.payload.setdefault("publication", [])
        events.append({"run_id": run_id, **payload})
        self.save()
