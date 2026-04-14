"""Tracked nightly config and scene manifest loading."""
from __future__ import annotations

import json

from .model import NightlyConfig, SceneDefinition
from .paths import NIGHTLY_CONFIG_PATH, SCENE_MANIFEST_PATH


def load_nightly_config() -> NightlyConfig:
    return NightlyConfig.from_dict(json.loads(NIGHTLY_CONFIG_PATH.read_text(encoding="utf-8")))


def load_scene_manifest() -> list[SceneDefinition]:
    payload = json.loads(SCENE_MANIFEST_PATH.read_text(encoding="utf-8"))
    return [SceneDefinition.from_dict(entry) for entry in payload["scenes"]]
