"""Candidate preparation, capture, and deterministic evaluation."""
from __future__ import annotations

import configparser
import json
import shutil
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from config import GAME_DIR
from patches.TombRaiderLegend import run as trl_run

from .anchors import load_anchor_manifest, refresh_anchor_hashes, write_live_mod
from .logs import parse_proxy_log
from .model import CandidateResult, CandidateSpec, NightlyConfig, RunState, SceneDefinition
from .paths import CAPTURES_ROOT, CHECKPOINT_PATH, PROXY_SOURCE_DIR, RTX_CONF_PATH, RUNS_ROOT, WORKTREES_ROOT, ensure_nightly_dirs
from .scoring import build_candidate_result, evaluate_hash_stability, evaluate_sky_frames, evaluate_water_motion
from .worktrees import create_detached_worktree

_SKY_VIEW_SNIPPET = """    if (!mat4_approx_equal(self->savedView, s_identity4x4, 1e-5f))
        return 0;
    if (!mat4_approx_equal(self->savedWorld, s_identity4x4, 1e-5f))
        return 0;
"""

_SKY_VIEW_REPLACEMENT = """    /* Nightly source mutation: widen TRL sky isolation beyond strict identity transforms. */
"""

_WATER_ROUTE_SNIPPET = """            if (self->curDeclPosType == D3DDECLTYPE_FLOAT3)
                float3Route = TRL_GetEffectiveFloat3Route(self);
"""

_WATER_ROUTE_REPLACEMENT = """            if (self->curDeclPosType == D3DDECLTYPE_FLOAT3)
                float3Route = TRL_GetEffectiveFloat3Route(self);
            if (animatedTex0 && self->curDeclPosType == D3DDECLTYPE_FLOAT3)
                float3Route = FLOAT3_ROUTE_SHADER;
"""

_FRAME_TIMING_SNIPPET = """    /* Reset per-scene draw counters */
"""

_FRAME_TIMING_REPLACEMENT = """    {
        static DWORD s_lastSceneTick = 0;
        DWORD nowTick = GetTickCount();
        if (self->drawsTotal > 0 && s_lastSceneTick != 0) {
            log_str("FrameCpuMs=");
            log_int("", (int)(nowTick - s_lastSceneTick));
        }
        s_lastSceneTick = nowTick;
    }

    /* Reset per-scene draw counters */
"""


def _copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _replace_once(text: str, old: str, new: str, template_name: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Source template '{template_name}' could not find its anchor")
    return text.replace(old, new, 1)


def _apply_source_template(path: Path, template_name: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if template_name == "sky_isolation_aggressive":
        text = _replace_once(text, _SKY_VIEW_SNIPPET, _SKY_VIEW_REPLACEMENT, template_name)
    elif template_name == "water_animation_preserve":
        text = _replace_once(text, _WATER_ROUTE_SNIPPET, _WATER_ROUTE_REPLACEMENT, template_name)
    elif template_name == "frame_timing_present_log":
        text = _replace_once(text, _FRAME_TIMING_SNIPPET, _FRAME_TIMING_REPLACEMENT, template_name)
    else:
        raise RuntimeError(f"Unknown source template: {template_name}")
    path.write_text(text, encoding="utf-8")


def _apply_proxy_overrides(path: Path, overrides: dict[str, dict[str, Any]]) -> None:
    if not overrides:
        return
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    for section, values in overrides.items():
        if not parser.has_section(section):
            parser.add_section(section)
        for key, value in values.items():
            parser.set(section, key, str(value))
    with path.open("w", encoding="utf-8") as handle:
        parser.write(handle)


def _apply_rtx_overrides(path: Path, overrides: dict[str, Any]) -> None:
    if not overrides:
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    pending = dict(overrides)
    updated: list[str] = []
    for line in lines:
        stripped = line.strip()
        replaced = False
        for key, value in list(pending.items()):
            if stripped.startswith(f"{key} ="):
                updated.append(f"{key} = {value}")
                pending.pop(key)
                replaced = True
                break
        if not replaced:
            updated.append(line)
    if pending:
        updated.append("")
        for key, value in pending.items():
            updated.append(f"{key} = {value}")
    path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


def _latest_capture() -> Path | None:
    captures = sorted(
        [path for path in CAPTURES_ROOT.glob("capture_*") if path.suffix.lower() in {".usd", ".usda"}],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return captures[0] if captures else None


class NightlyExecutor:
    def __init__(
        self,
        config: NightlyConfig,
        scenes: list[SceneDefinition],
        *,
        dry_run: bool = False,
    ) -> None:
        self.config = config
        self.scenes = scenes
        self.dry_run = dry_run

    def bootstrap(self, scene_ids: list[str] | None = None) -> dict[str, Any]:
        ensure_nightly_dirs()
        selected = scene_ids or [scene.scene_id for scene in self.scenes]
        scene_map = {scene.scene_id: scene for scene in self.scenes}
        missing_scene_ids = [scene_id for scene_id in selected if scene_id not in scene_map]
        if missing_scene_ids:
            raise RuntimeError(f"Unknown scene ids: {', '.join(missing_scene_ids)}")
        if not CHECKPOINT_PATH.exists():
            raise RuntimeError(f"Missing required TRL checkpoint: {CHECKPOINT_PATH}")

        latest_capture = _latest_capture()
        if latest_capture:
            manifest = refresh_anchor_hashes(latest_capture)
            anchor_validation = dict(manifest.get("anchor_validation", {}))
        else:
            manifest = load_anchor_manifest()
            anchor_validation = {
                "status": "missing_capture",
                "used_tracked_manifest": True,
                "reasons": ["no capture_*.usd(a) file was available to validate tracked stage anchors"],
            }
            manifest["anchor_validation"] = anchor_validation
        mod_path = write_live_mod(manifest)
        payload = {
            "selected_scenes": selected,
            "checkpoint": str(CHECKPOINT_PATH),
            "latest_capture": str(latest_capture) if latest_capture else None,
            "live_mod": str(mod_path),
            "anchor_validation": anchor_validation,
        }
        _write_json(RUNS_ROOT / "bootstrap_report.json", payload)
        return payload

    def prepare_candidate_workspace(self, state: RunState, spec: CandidateSpec) -> dict[str, str]:
        run_dir = Path(state.run_dir)
        candidate_dir = run_dir / "candidates" / spec.candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)

        build_proxy_dir = candidate_dir / "proxy"
        _copytree(PROXY_SOURCE_DIR, build_proxy_dir)
        build_rtx_conf = candidate_dir / "rtx.conf"
        shutil.copy2(RTX_CONF_PATH, build_rtx_conf)

        worktree_root: Path | None = None
        if spec.source_template:
            worktree_root = WORKTREES_ROOT / state.run_id / spec.candidate_id
            if not spec.worktree_path:
                create_detached_worktree(worktree_root, dry_run=self.dry_run)
                spec.worktree_path = str(worktree_root)
            else:
                worktree_root = Path(spec.worktree_path)
            worktree_source = worktree_root / "patches" / "TombRaiderLegend" / "proxy" / "d3d9_device.c"
            if worktree_source.exists():
                _apply_source_template(worktree_source, spec.source_template)
                shutil.copy2(worktree_source, build_proxy_dir / "d3d9_device.c")
            else:
                _apply_source_template(build_proxy_dir / "d3d9_device.c", spec.source_template)

        _apply_proxy_overrides(build_proxy_dir / "proxy.ini", spec.proxy_overrides)
        _apply_rtx_overrides(build_rtx_conf, spec.rtx_overrides)

        if worktree_root:
            worktree_proxy_ini = worktree_root / "patches" / "TombRaiderLegend" / "proxy" / "proxy.ini"
            worktree_rtx_conf = worktree_root / "patches" / "TombRaiderLegend" / "rtx.conf"
            if worktree_proxy_ini.exists():
                _apply_proxy_overrides(worktree_proxy_ini, spec.proxy_overrides)
            if worktree_rtx_conf.exists():
                _apply_rtx_overrides(worktree_rtx_conf, spec.rtx_overrides)

        metadata = {
            "candidate_dir": str(candidate_dir),
            "build_proxy_dir": str(build_proxy_dir),
            "rtx_conf": str(build_rtx_conf),
            "worktree_path": spec.worktree_path or "",
        }
        _write_json(candidate_dir / "workspace.json", metadata)
        return metadata

    def evaluate_candidate(self, state: RunState, spec: CandidateSpec) -> CandidateResult:
        workspace = self.prepare_candidate_workspace(state, spec)
        candidate_dir = Path(workspace["candidate_dir"])
        captures_dir = candidate_dir / "captures"
        captures_dir.mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            artifacts = self._capture_dry_run(spec, captures_dir)
        else:
            artifacts = self._capture_live(spec, workspace, captures_dir)

        result = self._score_candidate(spec, artifacts, candidate_dir)
        _write_json(candidate_dir / "result.json", result.to_dict())
        return result

    def _capture_live(
        self,
        spec: CandidateSpec,
        workspace: dict[str, str],
        captures_dir: Path,
    ) -> dict[str, Any]:
        from autopatch.patcher import apply_runtime, attach_livetools, detach_livetools
        from livetools.gamectl import find_hwnd_by_exe, focus_hwnd, move_mouse_relative, send_key, send_keys

        trl_run.build_proxy_bundle(
            proxy_dir=Path(workspace["build_proxy_dir"]),
            proxy_ini_path=Path(workspace["build_proxy_dir"]) / "proxy.ini",
            rtx_conf_path=Path(workspace["rtx_conf"]),
        )

        crashed = False
        try:
            trl_run.kill_game()
            runtime = dict(self.config.runtime)
            hwnd = trl_run.launch_game(
                chapter=int(runtime.get("launch_chapter", 2)),
                post_load_sequence=str(runtime.get("post_load_sequence", "")),
                post_load_settle_seconds=float(runtime.get("post_load_settle_seconds", 3.0)),
            )
            if spec.runtime_patch:
                attach_livetools("trl.exe")
                patch = dict(spec.runtime_patch)
                addr = int(patch["addr"])
                patch_bytes = bytes.fromhex(str(patch["patch_bytes_hex"]))
                if not apply_runtime(addr, patch_bytes):
                    raise RuntimeError(f"Failed to apply runtime patch for {spec.candidate_id}")

            scene_artifacts: dict[str, dict[str, Any]] = {}
            for scene in self.scenes:
                scene_dir = captures_dir / scene.scene_id
                scene_dir.mkdir(parents=True, exist_ok=True)
                if find_hwnd_by_exe("trl.exe") is None:
                    crashed = True
                    break
                focus_hwnd(hwnd)
                if scene.macro_sequence:
                    send_keys(hwnd, scene.macro_sequence, delay_ms=0)
                for move in scene.mouse_moves:
                    for _ in range(int(move.get("repeat", 1))):
                        move_mouse_relative(int(move.get("dx", 0)), int(move.get("dy", 0)))
                        time.sleep(float(move.get("delay_ms", 0)) / 1000.0)

                hash_paths: list[str] = []
                clean_paths: list[str] = []

                if "hash" in scene.debug_views:
                    trl_run.set_debug_view(int(scene.debug_views["hash"]))
                    before_hash = time.time()
                    for _ in range(scene.hash_capture_count):
                        send_key("]", hold_ms=50)
                        time.sleep(scene.screenshot_cadence_ms / 1000.0)
                    hash_paths = [
                        str(path)
                        for path in trl_run.collect_screenshots(
                            after_ts=before_hash,
                            limit=scene.hash_capture_count,
                            destination_dir=scene_dir / "hash",
                        )
                    ]

                if "clean" in scene.debug_views:
                    trl_run.set_debug_view(int(scene.debug_views["clean"]))
                    before_clean = time.time()
                    for _ in range(scene.clean_capture_count):
                        send_key("]", hold_ms=50)
                        time.sleep(scene.screenshot_cadence_ms / 1000.0)
                    clean_paths = [
                        str(path)
                        for path in trl_run.collect_screenshots(
                            after_ts=before_clean,
                            limit=scene.clean_capture_count,
                            destination_dir=scene_dir / "clean",
                        )
                    ]
                time.sleep(scene.performance_sample_seconds)
                scene_artifacts[scene.scene_id] = {
                    "hash": hash_paths,
                    "clean": clean_paths,
                }
            log_path = captures_dir / "ffp_proxy.log"
            if (GAME_DIR / "ffp_proxy.log").exists():
                shutil.copy2(GAME_DIR / "ffp_proxy.log", log_path)
            return {
                "crashed": crashed,
                "log_path": str(log_path),
                "scenes": scene_artifacts,
            }
        finally:
            if spec.runtime_patch:
                detach_livetools()
            trl_run.kill_game()

    def _capture_dry_run(self, spec: CandidateSpec, captures_dir: Path) -> dict[str, Any]:
        profile = self._dry_run_profile(spec)
        scene_artifacts: dict[str, dict[str, Any]] = {}
        for scene in self.scenes:
            scene_dir = captures_dir / scene.scene_id
            scene_dir.mkdir(parents=True, exist_ok=True)
            hash_paths = self._render_hash_frames(scene_dir / "hash", stable=profile["hash_stable"], count=scene.hash_capture_count)
            if "sky" in scene.rois:
                clean_paths = self._render_sky_frames(scene_dir / "clean", mode=profile["sky_mode"], count=scene.clean_capture_count)
            elif "water" in scene.rois and "background" in scene.rois:
                clean_paths = self._render_water_frames(scene_dir / "clean", moving=profile["water_moving"], count=scene.clean_capture_count)
            else:
                clean_paths = self._render_clean_frames(scene_dir / "clean", count=scene.clean_capture_count)
            scene_artifacts[scene.scene_id] = {
                "hash": [str(path) for path in hash_paths],
                "clean": [str(path) for path in clean_paths],
            }

        log_path = captures_dir / "ffp_proxy.log"
        log_lines = []
        for token in self.config.required_patch_tokens:
            if token not in profile["missing_tokens"]:
                log_lines.append(token)
        if profile["sky_events"]:
            for index in range(profile["sky_events"]):
                log_lines.append(f"SkyIso: applied iso = {index}")
        log_lines.append(f"passthrough={profile['passthrough']}")
        log_lines.append(f"xformBlocked={profile['xform_blocked']}")
        log_lines.append("DrawCache: replayed 3")
        for cpu_ms in profile["cpu_ms"]:
            log_lines.append(f"FrameCpuMs={cpu_ms}")
        log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        return {
            "crashed": profile["crashed"],
            "log_path": str(log_path),
            "scenes": scene_artifacts,
        }

    def _dry_run_profile(self, spec: CandidateSpec) -> dict[str, Any]:
        profile = {
            "crashed": False,
            "missing_tokens": set(),
            "passthrough": 0,
            "xform_blocked": 0,
            "sky_events": 0,
            "cpu_ms": [8.2, 8.6, 8.9, 8.4, 8.5],
            "hash_stable": True,
            "sky_mode": "dark",
            "water_moving": False,
        }
        candidate_id = spec.candidate_id

        if candidate_id == "baseline":
            return profile
        if spec.source_template == "sky_isolation_aggressive":
            profile["sky_mode"] = "clean"
            profile["sky_events"] = 10
            profile["cpu_ms"] = [7.6, 7.7, 7.5, 7.6, 7.8]
            return profile
        if spec.source_template == "water_animation_preserve":
            profile["sky_mode"] = "clean"
            profile["sky_events"] = 10
            profile["water_moving"] = True
            profile["cpu_ms"] = [6.1, 6.3, 6.2, 6.0, 6.4]
            return profile
        if spec.source_template == "frame_timing_present_log":
            profile["sky_mode"] = "clean"
            profile["sky_events"] = 8
            profile["water_moving"] = True
            profile["cpu_ms"] = [5.9, 6.0, 5.8, 6.1, 5.9]
            return profile
        if candidate_id.startswith("cfg-sky"):
            profile["sky_mode"] = "clean"
            profile["sky_events"] = 6
            profile["cpu_ms"] = [7.8, 7.9, 8.0, 8.1, 7.7]
            return profile
        if candidate_id == "cfg-water-tag":
            profile["water_moving"] = True
            profile["cpu_ms"] = [8.0, 8.1, 8.0, 8.2, 8.1]
            return profile
        if candidate_id == "cfg-anchor-refresh":
            profile["missing_tokens"] = {self.config.required_patch_tokens[-1]}
            profile["passthrough"] = 1
            profile["cpu_ms"] = [9.3, 9.0, 9.1, 9.2, 9.4]
            return profile
        if candidate_id.startswith("rt-"):
            profile["crashed"] = candidate_id.endswith("0")
            profile["hash_stable"] = not profile["crashed"]
            profile["passthrough"] = 1 if not profile["crashed"] else 0
            profile["cpu_ms"] = [10.5, 10.2, 10.1, 10.3, 10.4]
            return profile
        return profile

    def _render_hash_frames(self, out_dir: Path, *, stable: bool, count: int) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for index in range(count):
            image = Image.new("RGB", (400, 300), (48, 48, 48))
            draw = ImageDraw.Draw(image)
            offset = 0 if stable else index * 8
            draw.rectangle((60 + offset, 60, 320 + offset, 250), fill=(180, 180, 180))
            draw.rectangle((130, 100 + offset, 220, 170 + offset), fill=(220, 220, 220))
            path = out_dir / f"hash_{index + 1:02d}.png"
            image.save(path)
            paths.append(path)
        return paths

    def _render_clean_frames(self, out_dir: Path, *, count: int) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for index in range(count):
            image = Image.new("RGB", (400, 300), (70, 90, 110))
            draw = ImageDraw.Draw(image)
            draw.rectangle((120, 80, 280, 240), fill=(140, 130, 120))
            path = out_dir / f"clean_{index + 1:02d}.png"
            image.save(path)
            paths.append(path)
        return paths

    def _render_sky_frames(self, out_dir: Path, *, mode: str, count: int) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for index in range(count):
            if mode == "clean":
                image = Image.new("RGB", (400, 300), (90, 95, 105))
                draw = ImageDraw.Draw(image)
                draw.rectangle((80, 10, 320, 110), fill=(185, 192, 198))
                draw.rectangle((40, 130, 360, 280), fill=(90, 84, 80))
            elif mode == "contaminated":
                image = Image.new("RGB", (400, 300), (40, 40, 40))
                draw = ImageDraw.Draw(image)
                for step in range(0, 240, 20):
                    color = (40, 120, 240) if (step // 20) % 2 == 0 else (240, 40, 40)
                    draw.rectangle((80 + step // 4, 10, 100 + step // 4, 110), fill=color)
                draw.rectangle((40, 130, 360, 280), fill=(100, 70, 40))
            else:
                image = Image.new("RGB", (400, 300), (18, 18, 18))
                draw = ImageDraw.Draw(image)
                draw.rectangle((40, 130, 360, 280), fill=(95, 85, 75))
            path = out_dir / f"clean_{index + 1:02d}.png"
            image.save(path)
            paths.append(path)
        return paths

    def _render_water_frames(self, out_dir: Path, *, moving: bool, count: int) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for index in range(count):
            image = Image.new("RGB", (400, 300), (70, 70, 70))
            draw = ImageDraw.Draw(image)
            draw.rectangle((40, 80, 160, 250), fill=(82, 82, 82))
            draw.rectangle((250, 80, 372, 250), fill=(70, 95, 120))
            if moving:
                for stripe in range(0, 150, 18):
                    x1 = 250 + ((stripe + (index * 7)) % 120)
                    draw.rectangle((x1, 80, min(x1 + 10, 372), 250), fill=(170, 210, 235))
            path = out_dir / f"clean_{index + 1:02d}.png"
            image.save(path)
            paths.append(path)
        return paths

    def _score_candidate(
        self,
        spec: CandidateSpec,
        artifacts: dict[str, Any],
        candidate_dir: Path,
    ) -> CandidateResult:
        log_summary = parse_proxy_log(artifacts.get("log_path"), self.config.required_patch_tokens)
        hash_retention_values: list[float] = []
        sky_pass = False
        sky_non_void = 0.0
        sky_contamination = 100.0
        water_pass = False
        water_ratio = 0.0

        for scene in self.scenes:
            scene_artifacts = artifacts["scenes"].get(scene.scene_id, {})
            hash_paths = list(scene_artifacts.get("hash", []))
            if "hash_stability" in scene.rois:
                hash_retention_values.append(evaluate_hash_stability(hash_paths, scene.rois["hash_stability"]))

            clean_paths = list(scene_artifacts.get("clean", []))
            if "sky" in scene.rois:
                sky_pass, sky_non_void, sky_contamination = evaluate_sky_frames(
                    clean_paths,
                    scene.rois["sky"],
                    scene.thresholds,
                )
                sky_pass = sky_pass and log_summary.sky_isolation_events > 0
            if "water" in scene.rois and "background" in scene.rois:
                water = evaluate_water_motion(
                    clean_paths,
                    scene.rois["water"],
                    scene.rois["background"],
                    scene.thresholds,
                )
                water_ratio = water.ratio
                water_pass = water_ratio >= scene.thresholds["water_motion_ratio_min"]

        hash_retention_pct = min(hash_retention_values) if hash_retention_values else 0.0
        hard_gate_pass = (
            not artifacts.get("crashed", False)
            and log_summary.all_required_patches_present
            and log_summary.max_passthrough == 0
            and log_summary.max_xform_blocked == 0
            and hash_retention_pct >= 98.0
        )

        failure_modes: list[str] = []
        next_hypotheses: list[str] = []
        if artifacts.get("crashed", False):
            failure_modes.append("candidate_crashed")
        if not log_summary.all_required_patches_present:
            failure_modes.append("missing_required_patch_marker")
        if log_summary.max_passthrough > 0:
            failure_modes.append("draw_passthrough_nonzero")
        if log_summary.max_xform_blocked > 0:
            failure_modes.append("transform_override_blocked")
        if hash_retention_pct < 98.0:
            failure_modes.append("hash_retention_below_gate")
        if not sky_pass:
            next_hypotheses.append("increase sky-only candidate coverage without contaminating world hashes")
        if not water_pass:
            next_hypotheses.append("keep animated-water draws on the shader-preserving route")
        release_pass = bool(artifacts.get("release_gate", {}).get("passed", False))

        return build_candidate_result(
            spec.candidate_id,
            spec.mutation_class,
            spec.description,
            crashed=bool(artifacts.get("crashed", False)),
            hard_gate_pass=hard_gate_pass,
            sky_pass=sky_pass,
            water_pass=water_pass,
            release_pass=release_pass,
            hash_retention_pct=hash_retention_pct,
            sky_non_void_pct=sky_non_void,
            sky_contamination_pct=sky_contamination,
            water_motion_ratio=water_ratio,
            performance_p95_cpu_ms=log_summary.p95_cpu_ms,
            performance_median_cpu_ms=log_summary.median_cpu_ms,
            required_patch_hits=log_summary.required_patch_hits,
            failure_modes=failure_modes,
            next_hypotheses=next_hypotheses,
            artifacts={
                "candidate_dir": str(candidate_dir),
                "workspace": {
                    "source_template": spec.source_template,
                    "worktree_path": spec.worktree_path,
                },
                "log_path": artifacts.get("log_path"),
                "scenes": artifacts.get("scenes", {}),
                "release_gate": dict(artifacts.get("release_gate", {})),
            },
        )
