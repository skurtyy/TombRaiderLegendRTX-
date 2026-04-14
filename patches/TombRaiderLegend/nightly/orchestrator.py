"""Top-level TRL nightly orchestration."""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .continuation import launch_claude_followup, write_handoff_report
from .executor import NightlyExecutor
from .ledger import ExperimentLedger
from .manifests import load_nightly_config, load_scene_manifest
from .model import CandidateResult, CandidateSpec, RunState
from .mutations import generate_initial_candidate_specs, generate_source_candidate_specs
from .paths import RUNS_ROOT, WORKTREES_ROOT, ensure_nightly_dirs
from .publication import (
    build_draft_pr_payload,
    build_nightly_comment,
    discover_origin_remote,
    format_rolling_branch,
    format_run_branch,
    github_request,
    resolve_github_token,
)
from .reporting import rank_results, write_candidate_reviews, write_curated_artifacts, write_leaderboard, write_publication_payload, write_summary
from .review import review_candidate
from .scoring import beats_baseline, promotion_key
from .worktrees import commit_if_dirty, copy_candidate_files, create_branch_worktree, push_branch, remove_worktree


class NightlyOrchestrator:
    def __init__(self, *, dry_run: bool = False) -> None:
        self.config = load_nightly_config()
        self.scenes = load_scene_manifest()
        self.ledger = ExperimentLedger.load()
        self.executor = NightlyExecutor(self.config, self.scenes, dry_run=dry_run)
        self.dry_run = dry_run

    def bootstrap(self, scene_ids: list[str] | None = None) -> dict[str, object]:
        return self.executor.bootstrap(scene_ids)

    def _new_run_state(self, hours_requested: int) -> RunState:
        ensure_nightly_dirs()
        started_at = datetime.now().isoformat(timespec="seconds")
        run_id = datetime.now().strftime("run-%Y%m%d-%H%M%S")
        run_dir = RUNS_ROOT / run_id
        branch_name = format_run_branch(
            self.config.publication["run_branch_prefix"],
            started_at,
            run_id,
        )
        rolling_branch = format_rolling_branch(self.config.publication["rolling_pr_branch_prefix"])
        return RunState(
            run_id=run_id,
            branch_name=branch_name,
            rolling_branch_name=rolling_branch,
            run_dir=str(run_dir),
            started_at=started_at,
            hours_requested=hours_requested,
            status="running",
            phase="bootstrap",
            scene_ids=[scene.scene_id for scene in self.scenes],
        )

    def _load_results(self, state: RunState) -> list[CandidateResult]:
        return [CandidateResult.from_dict(payload) for payload in state.candidate_results]

    def _load_specs(self, state: RunState) -> list[CandidateSpec]:
        return [CandidateSpec.from_dict(payload) for payload in state.candidate_specs]

    def _write_reports(self, state: RunState) -> dict[str, str]:
        run_dir = Path(state.run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        baseline = CandidateResult.from_dict(state.baseline_result) if state.baseline_result else None
        results = self._load_results(state)
        ranked = rank_results(results)
        write_candidate_reviews(run_dir, results)
        write_curated_artifacts(
            run_dir,
            ranked,
            limit=int(self.config.publication.get("curated_artifact_limit", 12)),
        )
        summary_path = write_summary(run_dir, state, baseline, ranked) if baseline else None
        leaderboard_path = write_leaderboard(run_dir, baseline, ranked) if baseline else None
        return {
            "summary_path": str(summary_path) if summary_path else "",
            "leaderboard_path": str(leaderboard_path) if leaderboard_path else "",
        }

    def _review_and_store(
        self,
        result: CandidateResult,
        baseline: CandidateResult | None,
    ) -> CandidateResult:
        result.review = review_candidate(result, baseline)
        return result

    def _select_shortlist(self, results: list[CandidateResult]) -> list[CandidateResult]:
        ranked = rank_results(results)
        return ranked[: self.config.keep_top_candidates]

    def _deadline_exceeded(self, deadline: float | None) -> bool:
        return deadline is not None and time.monotonic() >= deadline

    def _apply_source_rounds(self, state: RunState, deadline: float | None = None) -> None:
        baseline = CandidateResult.from_dict(state.baseline_result)
        existing_ids = {spec["candidate_id"] for spec in state.candidate_specs}
        all_results = self._load_results(state)
        shortlisted = self._select_shortlist(all_results)
        for round_index in range(state.source_round_index, self.config.max_source_mutation_rounds):
            if self._deadline_exceeded(deadline):
                state.notes.append("Stopped source mutation rounds after exhausting the nightly budget")
                break
            source_specs = generate_source_candidate_specs(
                self.config,
                shortlisted,
                round_index,
                existing_ids,
            )
            if not source_specs:
                break
            state.phase = f"source-round-{round_index + 1}"
            state.source_round_index = round_index
            for spec in source_specs:
                if self._deadline_exceeded(deadline):
                    state.notes.append("Stopped source mutation candidate evaluation after exhausting the nightly budget")
                    break
                state.candidate_specs.append(spec.to_dict())
                existing_ids.add(spec.candidate_id)
                result = self.executor.evaluate_candidate(state, spec)
                result = self._review_and_store(result, baseline)
                state.candidate_results.append(result.to_dict())
                self.ledger.upsert_run(state)
            state.source_round_index = round_index + 1
            all_results = self._load_results(state)
            shortlisted = self._select_shortlist(all_results)

    def _finalize(self, state: RunState) -> RunState:
        baseline = CandidateResult.from_dict(state.baseline_result)
        ranked = rank_results(self._load_results(state))
        state.shortlisted_ids = [result.candidate_id for result in ranked[: self.config.keep_top_candidates]]
        screen_winner = None
        for result in ranked:
            if result.screen_pass and beats_baseline(result, baseline):
                screen_winner = result
                break
        winner = None
        for result in ranked:
            if result.promotion_eligible and beats_baseline(result, baseline):
                winner = result
                break
        state.screen_winner_id = screen_winner.candidate_id if screen_winner else None
        state.winner_id = winner.candidate_id if winner else None
        if winner:
            state.phase = "publish_ready"
        elif screen_winner:
            state.phase = "screened"
        else:
            state.phase = "completed"
        state.status = "completed"
        self._write_reports(state)
        self.ledger.upsert_run(state)
        return state

    def run(self, hours: int | None = None) -> RunState:
        hours_requested = hours or self.config.default_hours
        deadline = time.monotonic() + (hours_requested * 3600)
        state = self._new_run_state(hours_requested)
        self.ledger.upsert_run(state)

        self.bootstrap()
        state.phase = "baseline"
        baseline_spec = CandidateSpec(
            candidate_id="baseline",
            mutation_class="baseline",
            description="Authoritative TRL baseline using the current tracked proxy/runtime",
        )
        baseline = self.executor.evaluate_candidate(state, baseline_spec)
        baseline = self._review_and_store(baseline, None)
        state.baseline_result = baseline.to_dict()
        self.ledger.upsert_run(state)

        state.phase = "candidate_generation"
        specs = generate_initial_candidate_specs(self.config, self.ledger)
        state.candidate_specs = [spec.to_dict() for spec in specs]
        self.ledger.upsert_run(state)

        state.phase = "candidate_eval"
        for index in range(state.next_index, len(specs)):
            if self._deadline_exceeded(deadline):
                state.notes.append("Stopped config/runtime candidate evaluation after exhausting the nightly budget")
                break
            spec = specs[index]
            result = self.executor.evaluate_candidate(state, spec)
            result = self._review_and_store(result, baseline)
            state.candidate_results.append(result.to_dict())
            state.next_index = index + 1
            self.ledger.upsert_run(state)

        self._apply_source_rounds(state, deadline)
        return self._finalize(state)

    def resume(self, run_id: str) -> RunState:
        state = self.ledger.get_run(run_id)
        if not state:
            raise RuntimeError(f"Unknown run id: {run_id}")
        if state.status == "completed":
            return state

        baseline = CandidateResult.from_dict(state.baseline_result) if state.baseline_result else None
        if baseline is None:
            baseline_spec = CandidateSpec(
                candidate_id="baseline",
                mutation_class="baseline",
                description="Authoritative TRL baseline using the current tracked proxy/runtime",
            )
            baseline = self.executor.evaluate_candidate(state, baseline_spec)
            baseline = self._review_and_store(baseline, None)
            state.baseline_result = baseline.to_dict()
            self.ledger.upsert_run(state)

        specs = self._load_specs(state)
        if not specs:
            specs = generate_initial_candidate_specs(self.config, self.ledger)
            state.candidate_specs = [spec.to_dict() for spec in specs]
            self.ledger.upsert_run(state)

        for index in range(state.next_index, len(specs)):
            spec = specs[index]
            result = self.executor.evaluate_candidate(state, spec)
            result = self._review_and_store(result, baseline)
            state.candidate_results.append(result.to_dict())
            state.next_index = index + 1
            self.ledger.upsert_run(state)

        self._apply_source_rounds(state)
        return self._finalize(state)

    def post_run_automation(self, state: RunState) -> dict[str, object]:
        run_dir = Path(state.run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

        auto_publish: dict[str, object] = {
            "attempted": False,
            "succeeded": False,
        }
        if self.config.publication.get("auto_publish_on_completion", False) and not self.dry_run:
            auto_publish["attempted"] = True
            if resolve_github_token():
                try:
                    publish_payload = self.publish(state.run_id)
                    auto_publish["succeeded"] = True
                    auto_publish["payload_path"] = publish_payload.get("payload_path", "")
                    auto_publish["winner_id"] = publish_payload.get("winner_id", "")
                    if publish_payload.get("publish_note"):
                        auto_publish["note"] = publish_payload["publish_note"]
                except Exception as exc:
                    auto_publish["error"] = str(exc)
            else:
                auto_publish["note"] = "GITHUB_TOKEN is not set"

        payload: dict[str, object] = {"auto_publish": auto_publish}
        if self.config.automation.get("write_handoff_report", True):
            handoff_path = write_handoff_report(
                run_dir,
                state,
                self.config,
                auto_publish=auto_publish,
            )
            payload["handoff_path"] = str(handoff_path)

            auto_hours = {
                int(value)
                for value in self.config.automation.get("auto_continue_hours", [])
            }
            if (
                self.config.automation.get("auto_continue_with_claude", False)
                and not self.dry_run
                and state.hours_requested in auto_hours
            ):
                try:
                    payload["claude_followup"] = launch_claude_followup(
                        run_dir,
                        handoff_path,
                        state,
                        self.config,
                    )
                except Exception as exc:
                    payload["claude_followup"] = {
                        "started": False,
                        "error": str(exc),
                    }
        return payload

    def publish(self, run_id: str) -> dict[str, object]:
        state = self.ledger.get_run(run_id)
        if not state:
            raise RuntimeError(f"Unknown run id: {run_id}")

        reports = self._write_reports(state)
        run_dir = Path(state.run_dir)
        leaderboard = json.loads(Path(reports["leaderboard_path"]).read_text(encoding="utf-8"))["leaderboard"]
        summary_markdown = Path(reports["summary_path"]).read_text(encoding="utf-8")
        comment_body = build_nightly_comment(state.run_id, summary_markdown, leaderboard)
        pr_payload = build_draft_pr_payload(
            title=self.config.publication["rolling_draft_pr_title"],
            body=summary_markdown,
            head_branch=state.rolling_branch_name,
            base_branch=self.config.publication["base_branch"],
        )

        payload: dict[str, object] = {
            "run_id": state.run_id,
            "screen_winner_id": state.screen_winner_id,
            "winner_id": state.winner_id,
            "run_branch": state.branch_name,
            "rolling_branch": state.rolling_branch_name,
            "pr_payload": pr_payload,
            "comment_body": comment_body,
        }

        winner_result = None
        if state.winner_id:
            for result in self._load_results(state):
                if result.candidate_id == state.winner_id:
                    winner_result = result
                    break

        branch_worktree = WORKTREES_ROOT / state.run_id / "publish"
        if winner_result:
            create_branch_worktree(branch_worktree, state.branch_name, dry_run=self.dry_run)
            worktree_path = str(winner_result.artifacts.get("workspace", {}).get("worktree_path", ""))
            source_root = Path(worktree_path) if worktree_path else Path(winner_result.artifacts["candidate_dir"])
            if worktree_path and not (source_root / "patches" / "TombRaiderLegend" / "proxy" / "d3d9_device.c").exists():
                source_root = Path(winner_result.artifacts["candidate_dir"])
            copy_candidate_files(source_root, branch_worktree)
            commit_if_dirty(branch_worktree, f"nightly: promote {state.run_id}", dry_run=self.dry_run)
            push_branch(branch_worktree, state.branch_name, dry_run=self.dry_run)
            push_branch(branch_worktree, state.rolling_branch_name, dry_run=self.dry_run)

        if not self.dry_run:
            owner, repo = discover_origin_remote()
            pulls_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            existing_url = f"{pulls_url}?state=open&head={owner}:{state.rolling_branch_name}"
            existing = github_request("GET", existing_url)
            existing_pull = existing[0] if isinstance(existing, list) and existing else None
            pull = None
            if existing_pull:
                pull_number = existing_pull["number"]
                pull = github_request(
                    "PATCH",
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}",
                    {
                        "title": pr_payload["title"],
                        "body": pr_payload["body"],
                        "base": pr_payload["base"],
                    },
                )
                if not winner_result:
                    payload["publish_note"] = "No release-gated winner; updated and commented on the existing rolling PR with screening results only"
            elif winner_result:
                pull = github_request("POST", pulls_url, pr_payload)
            else:
                payload["publish_note"] = "No release-gated winner and no existing rolling PR; skipping GitHub PR creation"
            if pull:
                payload["pull_request"] = pull
            if pull and pull.get("number"):
                comments_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pull['number']}/comments"
                payload["comment"] = github_request("POST", comments_url, {"body": comment_body})

        payload_path = write_publication_payload(run_dir, payload)
        payload["payload_path"] = str(payload_path)
        self.ledger.record_publication(run_id, payload)
        remove_worktree(branch_worktree, dry_run=self.dry_run)
        return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TRL RTX Remix nightly solver")
    parser.add_argument("--dry-run", action="store_true", help="Exercise the nightly loop without launching the game")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap_parser = subparsers.add_parser("bootstrap", help="Validate prerequisites and refresh the live anchor mod")
    bootstrap_parser.add_argument("--scene", action="append", dest="scene_ids", help="Limit bootstrap to specific scene ids")

    run_parser = subparsers.add_parser("run", help="Execute a nightly run")
    run_parser.add_argument("--hours", type=int, default=None, help="Override the default nightly budget")

    resume_parser = subparsers.add_parser("resume", help="Resume an interrupted nightly run")
    resume_parser.add_argument("run_id")

    publish_parser = subparsers.add_parser("publish", help="Push the winning candidate and update the rolling draft PR")
    publish_parser.add_argument("run_id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    orchestrator = NightlyOrchestrator(dry_run=args.dry_run)

    if args.command == "bootstrap":
        payload = orchestrator.bootstrap(args.scene_ids)
    elif args.command == "run":
        state = orchestrator.run(hours=args.hours)
        payload = {
            "run": state.to_dict(),
            "automation": orchestrator.post_run_automation(state),
        }
    elif args.command == "resume":
        state = orchestrator.resume(args.run_id)
        payload = {
            "run": state.to_dict(),
            "automation": orchestrator.post_run_automation(state),
        }
    elif args.command == "publish":
        payload = orchestrator.publish(args.run_id)
    else:
        raise RuntimeError(f"Unsupported command: {args.command}")

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0
