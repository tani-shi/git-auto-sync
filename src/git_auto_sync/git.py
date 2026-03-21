from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("git_auto_sync")


class GitError(Exception):
    pass


@dataclass
class BranchInfo:
    name: str
    sha: str


@dataclass
class TrackingInfo:
    upstream: str
    upstream_sha: str


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    cmd = ["git", "-C", str(repo), *args]
    logger.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.debug("git stderr: %s", result.stderr.strip())
    return result


def is_git_repo(path: Path) -> bool:
    result = run_git(path, "rev-parse", "--git-dir")
    return result.returncode == 0


def fetch_all(repo: Path) -> bool:
    result = run_git(repo, "fetch", "--all", "--quiet")
    if result.returncode != 0:
        logger.warning("Fetch failed for %s: %s", repo, result.stderr.strip())
        return False
    return True


def is_worktree_clean(repo: Path) -> bool:
    result = run_git(repo, "status", "--porcelain")
    if result.returncode != 0:
        return False
    return result.stdout.strip() == ""


def get_current_branch(repo: Path) -> str | None:
    result = run_git(repo, "symbolic-ref", "--short", "HEAD")
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def get_local_branches(repo: Path) -> list[BranchInfo]:
    result = run_git(
        repo, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads/"
    )
    if result.returncode != 0:
        return []
    branches = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split(" ", 1)
        if len(parts) == 2:
            branches.append(BranchInfo(name=parts[0], sha=parts[1]))
    return branches


def get_tracking_info(repo: Path, branch: str) -> TrackingInfo | None:
    fmt = "%(upstream:short) %(upstream)"
    result = run_git(repo, "for-each-ref", f"--format={fmt}", f"refs/heads/{branch}")
    if result.returncode != 0 or not result.stdout.strip():
        return None
    parts = result.stdout.strip().split(" ", 1)
    if len(parts) < 2 or not parts[0]:
        return None
    upstream_short = parts[0]
    # Get the upstream SHA
    sha_result = run_git(repo, "rev-parse", upstream_short)
    if sha_result.returncode != 0:
        return None
    return TrackingInfo(upstream=upstream_short, upstream_sha=sha_result.stdout.strip())


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    result = run_git(repo, "merge-base", "--is-ancestor", ancestor, descendant)
    return result.returncode == 0


def merge_ff_only(repo: Path, upstream: str) -> bool:
    result = run_git(repo, "merge", "--ff-only", upstream)
    if result.returncode != 0:
        logger.warning("FF-merge failed for %s: %s", repo, result.stderr.strip())
        return False
    return True


def update_ref(repo: Path, ref: str, new_sha: str) -> bool:
    result = run_git(repo, "update-ref", f"refs/heads/{ref}", new_sha)
    if result.returncode != 0:
        logger.warning(
            "update-ref failed for %s/%s: %s", repo, ref, result.stderr.strip()
        )
        return False
    return True
