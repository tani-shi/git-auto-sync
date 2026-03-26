from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from git_auto_sync import git

logger = logging.getLogger("git_auto_sync")


@dataclass
class BranchResult:
    name: str
    status: str  # "updated", "skipped", "diverged", "error", "up-to-date"
    detail: str = ""


@dataclass
class SyncResult:
    repo: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    branches: list[BranchResult] = field(default_factory=list)
    fetch_ok: bool = True
    error: str = ""


def sync_repo(repo_path: Path) -> SyncResult:
    result = SyncResult(repo=str(repo_path))

    if not git.is_git_repo(repo_path):
        result.error = "Not a git repository"
        return result

    if not git.fetch_all(repo_path):
        result.fetch_ok = False
        result.error = "Fetch failed (offline or remote unavailable)"
        return result

    current_branch = git.get_current_branch(repo_path)
    branches = git.get_local_branches(repo_path)

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
                result.branches.append(
                    BranchResult(branch.name, "error", detail)
                )
        else:
            if git.update_ref(repo_path, branch.name, tracking.upstream_sha):
                result.branches.append(
                    BranchResult(branch.name, "updated", "ref updated")
                )
            else:
                result.branches.append(
                    BranchResult(branch.name, "error", "update-ref failed")
                )

    logger.info("Synced %s: %s", repo_path, _summary(result))
    return result


def sync_all(repos: list[str]) -> list[SyncResult]:
    results = []
    for repo in repos:
        repo_path = Path(repo)
        if not repo_path.exists():
            logger.warning("Repo path does not exist: %s", repo)
            results.append(SyncResult(repo=repo, error="Path does not exist"))
            continue
        results.append(sync_repo(repo_path))
    return results


def _summary(result: SyncResult) -> str:
    if result.error and not result.branches:
        return result.error
    counts: dict[str, int] = {}
    for b in result.branches:
        counts[b.status] = counts.get(b.status, 0) + 1
    return ", ".join(f"{v} {k}" for k, v in counts.items())
