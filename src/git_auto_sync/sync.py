from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from git_auto_sync import git
from git_auto_sync.config import SyncMode

logger = logging.getLogger("git_auto_sync")


@dataclass
class BranchResult:
    name: str
    status: str  # "updated", "skipped", "diverged", "error", "up-to-date"
    detail: str = ""


@dataclass
class SyncResult:
    repo: str
    mode: SyncMode = SyncMode.SYNC
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    branches: list[BranchResult] = field(default_factory=list)
    fetch_ok: bool = True
    error: str = ""


def sync_repo(repo_path: Path, mode: SyncMode = SyncMode.SYNC) -> SyncResult:
    result = SyncResult(repo=str(repo_path), mode=mode)

    if not git.is_git_repo(repo_path):
        result.error = "Not a git repository"
        return result

    fetch = git.fetch_remote_tracking if mode == SyncMode.FETCH_ONLY else git.fetch_all
    if not fetch(repo_path):
        result.fetch_ok = False
        if mode == SyncMode.FETCH_ONLY:
            result.error = (
                "Fetch failed (unsafe refspec, offline, or remote unavailable)"
            )
        else:
            result.error = "Fetch failed (offline or remote unavailable)"
        return result

    if mode == SyncMode.FETCH_ONLY:
        logger.info("Synced %s: %s", repo_path, _summary(result))
        return result

    current_branch = git.get_current_branch(repo_path)
    branches = git.get_local_branches(repo_path)
    checked_out_branches = git.get_checked_out_branches(repo_path)

    for branch in branches:
        tracking = git.get_tracking_info(repo_path, branch.name)
        if tracking is None:
            result.branches.append(
                BranchResult(branch.name, "skipped", "no upstream tracking branch")
            )
            continue

        if branch.sha == tracking.upstream_sha:
            result.branches.append(BranchResult(branch.name, "up-to-date"))
            continue

        # Check if local is ancestor of remote (can fast-forward)
        if not git.is_ancestor(repo_path, branch.sha, tracking.upstream_sha):
            result.branches.append(
                BranchResult(branch.name, "diverged", "local and remote have diverged")
            )
            continue

        if branch.name == current_branch:
            if git.merge_ff_only(repo_path, tracking.upstream):
                result.branches.append(
                    BranchResult(branch.name, "updated", "fast-forward merge")
                )
            else:
                detail = "ff-only merge failed"
                if not git.is_worktree_clean(repo_path):
                    detail = "ff-only merge failed (dirty worktree conflict)"
                result.branches.append(BranchResult(branch.name, "error", detail))
        else:
            result.branches.append(
                _update_non_current_branch(
                    repo_path,
                    branch.name,
                    tracking.upstream_sha,
                    checked_out_branches,
                )
            )

    logger.info("Synced %s: %s", repo_path, _summary(result))
    return result


def sync_all(repos: list[str], mode: SyncMode = SyncMode.SYNC) -> list[SyncResult]:
    results = []
    for repo in repos:
        repo_path = Path(repo)
        if not repo_path.exists():
            logger.warning("Repo path does not exist: %s", repo)
            results.append(
                SyncResult(repo=repo, mode=mode, error="Path does not exist")
            )
            continue
        results.append(sync_repo(repo_path, mode))
    return results


def _summary(result: SyncResult) -> str:
    if result.error and not result.branches:
        return result.error
    if result.mode == SyncMode.FETCH_ONLY:
        return "fetch-only complete"
    counts: dict[str, int] = {}
    for b in result.branches:
        counts[b.status] = counts.get(b.status, 0) + 1
    return ", ".join(f"{v} {k}" for k, v in counts.items())


def _update_non_current_branch(
    repo_path: Path,
    branch: str,
    upstream_sha: str,
    checked_out_branches: dict[str, str] | None,
) -> BranchResult:
    if checked_out_branches is None:
        return BranchResult(branch, "error", "worktree inspection failed")

    worktree_path = checked_out_branches.get(branch)
    if worktree_path is not None:
        return BranchResult(branch, "skipped", f"checked out at {worktree_path}")

    if git.force_branch(repo_path, branch, upstream_sha):
        return BranchResult(branch, "updated", "branch updated")

    latest_checked_out = git.get_checked_out_branches(repo_path)
    worktree_path = (
        latest_checked_out.get(branch) if latest_checked_out is not None else None
    )
    if worktree_path is not None:
        return BranchResult(branch, "skipped", f"checked out at {worktree_path}")
    return BranchResult(branch, "error", "branch update failed")
