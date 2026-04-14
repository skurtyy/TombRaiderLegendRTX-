"""Shared filesystem paths for the TRL nightly solver."""
from __future__ import annotations

from pathlib import Path

from config import GAME_DIR, PROXY_LOG, REPO_ROOT

TRL_PATCH_DIR = REPO_ROOT / "patches" / "TombRaiderLegend"
NIGHTLY_DIR = TRL_PATCH_DIR / "nightly"
NIGHTLY_CONFIG_PATH = TRL_PATCH_DIR / "nightly_config.json"
SCENE_MANIFEST_PATH = TRL_PATCH_DIR / "scene_manifest.json"
ANCHOR_MANIFEST_PATH = NIGHTLY_DIR / "anchor_manifest.json"
EXPERIMENT_LEDGER_PATH = NIGHTLY_DIR / "experiment_ledger.json"
AUTOPATCH_LEGACY_KNOWLEDGE_PATH = REPO_ROOT / "autopatch" / "knowledge.json"

RUNS_ROOT = GAME_DIR / "artifacts" / "nightly"
WORKTREES_ROOT = GAME_DIR / "artifacts" / "nightly-worktrees"
CURATED_ROOT = GAME_DIR / "artifacts" / "nightly-curated"
CAPTURES_ROOT = GAME_DIR / "rtx-remix" / "captures"
MODS_ROOT = GAME_DIR / "rtx-remix" / "mods"
PROXY_SOURCE_DIR = TRL_PATCH_DIR / "proxy"
PROXY_SOURCE_FILE = PROXY_SOURCE_DIR / "d3d9_device.c"
PROXY_INI_PATH = PROXY_SOURCE_DIR / "proxy.ini"
RTX_CONF_PATH = TRL_PATCH_DIR / "rtx.conf"
CHECKPOINT_PATH = TRL_PATCH_DIR / "peru_checkpoint.dat"
LIVE_PROXY_LOG = PROXY_LOG


def ensure_nightly_dirs() -> None:
    """Create local-only nightly directories inside the ignored game tree."""
    for path in (NIGHTLY_DIR, RUNS_ROOT, WORKTREES_ROOT, CURATED_ROOT):
        path.mkdir(parents=True, exist_ok=True)
