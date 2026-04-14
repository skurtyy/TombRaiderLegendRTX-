"""Handoff reporting and optional Claude CLI continuation."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from config import GAME_DIR, REPO_ROOT

from .model import NightlyConfig, RunState


def _runtime_line(config: NightlyConfig, key: str, default: object) -> object:
    return config.runtime.get(key, default)


def write_handoff_report(
    run_dir: Path,
    state: RunState,
    config: NightlyConfig,
    *,
    auto_publish: dict[str, Any] | None = None,
) -> Path:
    """Write a concise handoff for the next agent/context."""
    launch_chapter = _runtime_line(config, "launch_chapter", 2)
    post_load_sequence = _runtime_line(config, "post_load_sequence", "")
    sky_brightness = _runtime_line(config, "sky_brightness", 2.0)
    fallback_light_mode = _runtime_line(config, "fallback_light_mode", 0)
    auto_hours = list(config.automation.get("auto_continue_hours", []))

    if state.status == "completed":
        next_command = f"python ..\\patches\\TombRaiderLegend\\nightly.py run --hours {state.hours_requested}"
    else:
        next_command = f"python ..\\patches\\TombRaiderLegend\\nightly.py resume {state.run_id}"

    lines = [
        f"# TRL Nightly Handoff {state.run_id}",
        "",
        f"- Status: `{state.status}`",
        f"- Phase: `{state.phase}`",
        f"- Hours requested: `{state.hours_requested}`",
        f"- Winner: `{state.winner_id or 'none'}`",
        f"- Run dir: `{run_dir}`",
        f"- Scene matrix: {', '.join(state.scene_ids)}",
        "",
        "## Runtime Settings",
        "",
        f"- Launch directory: `{GAME_DIR}`",
        f"- Chapter: `{launch_chapter}`",
        f"- Post-load sequence: `{post_load_sequence}`",
        f"- Sky brightness: `{sky_brightness}`",
        f"- Fallback light mode: `{fallback_light_mode}`",
        "- Manual sky tags: preserved via `rtx.skyBoxTextures`",
        "",
        "## Automation State",
        "",
        f"- Candidate specs tracked: `{len(state.candidate_specs)}`",
        f"- Candidate results recorded: `{len(state.candidate_results)}`",
        f"- Next candidate index: `{state.next_index}`",
        f"- Source mutation round index: `{state.source_round_index}`",
        "",
        "## Next Command",
        "",
        "```powershell",
        next_command,
        "```",
    ]

    if auto_publish:
        lines.extend(
            [
                "",
                "## Publish State",
                "",
                f"- Auto publish attempted: `{auto_publish.get('attempted', False)}`",
                f"- Auto publish succeeded: `{auto_publish.get('succeeded', False)}`",
            ]
        )
        if auto_publish.get("payload_path"):
            lines.append(f"- Publication payload: `{auto_publish['payload_path']}`")
        if auto_publish.get("error"):
            lines.append(f"- Publish error: `{auto_publish['error']}`")
        if auto_publish.get("note"):
            lines.append(f"- Publish note: `{auto_publish['note']}`")

    if auto_hours:
        lines.extend(
            [
                "",
                "## Context Chaining",
                "",
                f"- Auto-continue hours: `{', '.join(str(v) for v in auto_hours)}`",
                "- A fresh Claude context may be launched automatically when a run finishes on one of those budgets.",
            ]
        )

    path = run_dir / "claude_handoff.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def build_claude_prompt(handoff_path: Path, state: RunState, config: NightlyConfig) -> str:
    """Build a follow-up prompt for a fresh Claude context."""
    launch_chapter = _runtime_line(config, "launch_chapter", 2)
    post_load_sequence = _runtime_line(config, "post_load_sequence", "")
    sky_brightness = _runtime_line(config, "sky_brightness", 2.0)
    fallback_light_mode = _runtime_line(config, "fallback_light_mode", 0)

    if state.status == "completed":
        objective = (
            f"Review the handoff, then start a new nightly run for {state.hours_requested} hours "
            "with the same settings."
        )
    else:
        objective = f"Resume the interrupted nightly run `{state.run_id}`."

    return (
        "Continue the Tomb Raider Legend nightly automation from the handoff report at "
        f"{handoff_path}. Work in repository `{REPO_ROOT}` and launch/build/test from `{GAME_DIR}`. "
        f"Keep these settings unchanged: chapter `{launch_chapter}`, post-load sequence "
        f"`{post_load_sequence}`, `rtx.skyBrightness = {sky_brightness}`, "
        f"`rtx.fallbackLightMode = {fallback_light_mode}`, and preserve the manual "
        "`rtx.skyBoxTextures` tags. Auto-publish results to GitHub when the run completes if "
        "the token is available. Update the handoff report again before exiting. "
        f"{objective}"
    )


def launch_claude_followup(
    run_dir: Path,
    handoff_path: Path,
    state: RunState,
    config: NightlyConfig,
) -> dict[str, Any]:
    """Start a fresh Claude CLI context in the background."""
    claude_command = str(config.automation.get("claude_command", "claude"))
    prompt = build_claude_prompt(handoff_path, state, config)
    prompt_path = run_dir / "claude_handoff_prompt.txt"
    prompt_path.write_text(prompt + "\n", encoding="utf-8")

    log_path = run_dir / "claude_followup.log"
    command = [
        claude_command,
        "-p",
        prompt,
        "--dangerously-skip-permissions",
        "--add-dir",
        str(REPO_ROOT),
    ]

    with log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(
            command,
            cwd=str(GAME_DIR),
            stdout=handle,
            stderr=subprocess.STDOUT,
        )

    return {
        "started": True,
        "pid": process.pid,
        "command": command,
        "prompt_path": str(prompt_path),
        "log_path": str(log_path),
    }
