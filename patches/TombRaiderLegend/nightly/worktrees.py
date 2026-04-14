"""Git worktree helpers for nightly source-mutation isolation."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from config import REPO_ROOT

TRACKED_RELATIVE_PATHS = [
    Path("patches/TombRaiderLegend/proxy/d3d9_device.c"),
    Path("patches/TombRaiderLegend/proxy/proxy.ini"),
    Path("patches/TombRaiderLegend/rtx.conf"),
]


def git(
    args: list[str],
    *,
    cwd: str | Path = REPO_ROOT,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def create_detached_worktree(path: Path, *, base_ref: str = "HEAD", dry_run: bool = False) -> Path:
    if dry_run:
        path.mkdir(parents=True, exist_ok=True)
        return path
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    git(["worktree", "add", "--force", "--detach", str(path), base_ref])
    return path


def create_branch_worktree(
    path: Path,
    branch_name: str,
    *,
    base_ref: str = "HEAD",
    dry_run: bool = False,
) -> Path:
    if dry_run:
        path.mkdir(parents=True, exist_ok=True)
        return path
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    git(["worktree", "add", "--force", "-B", branch_name, str(path), base_ref])
    return path


def remove_worktree(path: Path, *, dry_run: bool = False) -> None:
    if not path.exists():
        return
    if dry_run:
        shutil.rmtree(path, ignore_errors=True)
        return
    git(["worktree", "remove", "--force", str(path)], check=False)


def copy_candidate_files(src_root: Path, dst_root: Path) -> None:
    for relative in TRACKED_RELATIVE_PATHS:
        src = src_root / relative
        if not src.exists():
            if relative.name == "rtx.conf":
                src = src_root / "rtx.conf"
            else:
                src = src_root / "proxy" / relative.name
        dst = dst_root / relative
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def commit_if_dirty(worktree_path: Path, message: str, *, dry_run: bool = False) -> bool:
    if dry_run:
        return True
    status = git(["status", "--porcelain"], cwd=worktree_path, check=False)
    if not status.stdout.strip():
        return False
    git(["add", *[str(path) for path in TRACKED_RELATIVE_PATHS]], cwd=worktree_path)
    git(["commit", "-m", message], cwd=worktree_path)
    return True


def push_branch(worktree_path: Path, branch_name: str, *, dry_run: bool = False) -> None:
    if dry_run:
        return
    git(["push", "--force-with-lease", "origin", f"HEAD:refs/heads/{branch_name}"], cwd=worktree_path)
