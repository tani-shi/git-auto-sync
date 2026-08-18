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
    return _fetch_all(repo)


def fetch_remote_tracking(repo: Path) -> bool:
    remotes = run_git(repo, "remote")
    if remotes.returncode != 0:
        logger.warning(
            "Failed to list remotes for %s: %s", repo, remotes.stderr.strip()
        )
        return False

    for remote in remotes.stdout.splitlines():
        skip_fetch = run_git(
            repo, "config", "--bool", "--get", f"remote.{remote}.skipFetchAll"
        )
        if skip_fetch.returncode not in (0, 1):
            logger.warning(
                "Failed to inspect skipFetchAll for %s/%s: %s",
                repo,
                remote,
                skip_fetch.stderr.strip(),
            )
            return False
        if skip_fetch.stdout.strip() == "true":
            continue

        refspecs = run_git(repo, "config", "--get-all", f"remote.{remote}.fetch")
        if refspecs.returncode not in (0, 1):
            logger.warning(
                "Failed to inspect fetch refspecs for %s/%s: %s",
                repo,
                remote,
                refspecs.stderr.strip(),
            )
            return False
        unsafe_refspecs = [
            refspec
            for refspec in refspecs.stdout.splitlines()
            if not _is_remote_tracking_refspec(refspec)
        ]
        if unsafe_refspecs:
            logger.warning(
                "Fetch-only rejected non-remote-tracking refspecs for %s/%s: %s",
                repo,
                remote,
                ", ".join(unsafe_refspecs),
            )
            return False

    return _fetch_all(repo, "--no-tags", "--no-prune-tags")


def _fetch_all(repo: Path, *extra_args: str) -> bool:
    result = run_git(repo, "fetch", "--all", "--prune", "--quiet", *extra_args)
    if result.returncode != 0:
        logger.warning("Fetch failed for %s: %s", repo, result.stderr.strip())
        return False
    return True


def _is_remote_tracking_refspec(refspec: str) -> bool:
    normalized = refspec.removeprefix("+")
    if normalized.startswith("^") or ":" not in normalized:
        return True
    destination = normalized.split(":", 1)[1]
    return not destination or destination.startswith("refs/remotes/")


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


def get_checked_out_branches(repo: Path) -> dict[str, str] | None:
    result = run_git(repo, "worktree", "list", "--porcelain", "-z")
    if result.returncode != 0:
        logger.warning(
            "Failed to inspect worktrees for %s: %s", repo, result.stderr.strip()
        )
        return None

    branches = {}
    worktree_path: str | None = None
    branch_prefix = "branch refs/heads/"
    for field in result.stdout.split("\0"):
        if field.startswith("worktree "):
            worktree_path = field.removeprefix("worktree ")
        elif field.startswith(branch_prefix) and worktree_path is not None:
            branches[field.removeprefix(branch_prefix)] = worktree_path
    return branches


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


def force_branch(repo: Path, branch: str, new_sha: str) -> bool:
    result = run_git(repo, "branch", "--force", branch, new_sha)
    if result.returncode != 0:
        logger.warning(
            "Branch update failed for %s/%s: %s",
            repo,
            branch,
            result.stderr.strip(),
        )
        return False
    return True
