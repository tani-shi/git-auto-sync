from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from conftest import make_remote_commit
from git_auto_sync.config import SyncMode
from git_auto_sync.sync import sync_repo


def test_sync_up_to_date(local_clone: Path):
    result = sync_repo(local_clone)
    assert result.fetch_ok
    assert not result.error
    branch_results = {b.name: b.status for b in result.branches}
    assert branch_results.get("main") == "up-to-date"


def test_sync_fast_forward(local_clone: Path, bare_remote: Path):
    make_remote_commit(bare_remote, local_clone)
    result = sync_repo(local_clone)
    assert result.fetch_ok
    branch_results = {b.name: b.status for b in result.branches}
    assert branch_results.get("main") == "updated"


def test_fetch_only_updates_remote_tracking_branch(
    local_clone: Path, bare_remote: Path
):
    local_sha = _git_output(local_clone, "rev-parse", "main")
    remote_sha = make_remote_commit(bare_remote, local_clone)
    dirty_file = local_clone / "dirty.txt"
    dirty_file.write_text("dirty")

    result = sync_repo(local_clone, SyncMode.FETCH_ONLY)

    assert result.fetch_ok
    assert result.mode == SyncMode.FETCH_ONLY
    assert result.branches == []
    assert _git_output(local_clone, "rev-parse", "origin/main") == remote_sha
    assert _git_output(local_clone, "rev-parse", "main") == local_sha
    assert dirty_file.read_text() == "dirty"


def test_fetch_only_prunes_deleted_remote_branch(local_clone: Path, bare_remote: Path):
    subprocess.run(
        ["git", "branch", "obsolete", "main"],
        cwd=local_clone,
        check=True,
    )
    subprocess.run(
        ["git", "push", "origin", "obsolete"],
        cwd=local_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "--git-dir",
            str(bare_remote),
            "update-ref",
            "-d",
            "refs/heads/obsolete",
        ],
        check=True,
    )
    assert _git_output(local_clone, "rev-parse", "origin/obsolete")

    sync_repo(local_clone, SyncMode.FETCH_ONLY)

    result = subprocess.run(
        ["git", "rev-parse", "--verify", "origin/obsolete"],
        cwd=local_clone,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert _git_output(local_clone, "rev-parse", "obsolete")


def test_fetch_only_rejects_refspec_that_updates_local_branches(
    local_clone: Path, bare_remote: Path
):
    make_remote_commit(bare_remote, local_clone)
    subprocess.run(
        ["git", "config", "--unset-all", "remote.origin.fetch"],
        cwd=local_clone,
        check=True,
    )
    subprocess.run(
        [
            "git",
            "config",
            "--add",
            "remote.origin.fetch",
            "+refs/heads/*:refs/heads/fetched/*",
        ],
        cwd=local_clone,
        check=True,
    )

    result = sync_repo(local_clone, SyncMode.FETCH_ONLY)

    assert not result.fetch_ok
    assert "unsafe refspec" in result.error
    fetched_branch = subprocess.run(
        ["git", "rev-parse", "--verify", "refs/heads/fetched/main"],
        cwd=local_clone,
        capture_output=True,
        text=True,
    )
    assert fetched_branch.returncode != 0


def test_fetch_only_ignores_unsafe_refspec_on_skipped_remote(
    local_clone: Path, bare_remote: Path
):
    remote_sha = make_remote_commit(bare_remote, local_clone)
    subprocess.run(
        ["git", "remote", "add", "archive", str(bare_remote)],
        cwd=local_clone,
        check=True,
    )
    subprocess.run(
        ["git", "config", "remote.archive.skipFetchAll", "true"],
        cwd=local_clone,
        check=True,
    )
    subprocess.run(
        [
            "git",
            "config",
            "remote.archive.fetch",
            "+refs/heads/*:refs/heads/archive/*",
        ],
        cwd=local_clone,
        check=True,
    )

    result = sync_repo(local_clone, SyncMode.FETCH_ONLY)

    assert result.fetch_ok
    assert _git_output(local_clone, "rev-parse", "origin/main") == remote_sha


def test_fetch_only_overrides_prune_tags_config(local_clone: Path, bare_remote: Path):
    subprocess.run(
        ["git", "tag", "local-only"],
        cwd=local_clone,
        check=True,
    )
    tag_sha = _git_output(local_clone, "rev-parse", "local-only")
    subprocess.run(
        ["git", "config", "fetch.pruneTags", "true"],
        cwd=local_clone,
        check=True,
    )
    subprocess.run(
        ["git", "config", "remote.origin.pruneTags", "true"],
        cwd=local_clone,
        check=True,
    )
    make_remote_commit(bare_remote, local_clone)

    result = sync_repo(local_clone, SyncMode.FETCH_ONLY)

    assert result.fetch_ok
    assert _git_output(local_clone, "rev-parse", "local-only") == tag_sha


def test_sync_dirty_worktree_no_conflict_updates(local_clone: Path, bare_remote: Path):
    make_remote_commit(bare_remote, local_clone)

    # Make worktree dirty with a file that doesn't conflict
    (local_clone / "dirty.txt").write_text("dirty")

    result = sync_repo(local_clone)
    branch_results = {b.name: b.status for b in result.branches}
    assert branch_results.get("main") == "updated"


def test_sync_dirty_worktree_with_conflict(local_clone: Path, bare_remote: Path):
    # Remote modifies file.txt
    make_remote_commit(bare_remote, local_clone, filename="file.txt")

    # Local has uncommitted changes to the same file
    (local_clone / "file.txt").write_text("local dirty changes")

    result = sync_repo(local_clone)
    branch_results = {b.name: b.status for b in result.branches}
    assert branch_results.get("main") == "error"
    main_result = [b for b in result.branches if b.name == "main"][0]
    assert "dirty worktree" in main_result.detail


def test_sync_diverged_branch(local_clone: Path, bare_remote: Path):
    make_remote_commit(bare_remote, local_clone)

    # Create a local commit that diverges
    (local_clone / "local.txt").write_text("local")
    subprocess.run(
        ["git", "add", "local.txt"],
        cwd=local_clone,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "local commit"],
        cwd=local_clone,
        check=True,
    )

    result = sync_repo(local_clone)
    branch_results = {b.name: b.status for b in result.branches}
    assert branch_results.get("main") == "diverged"


def test_sync_updates_non_current_branch(local_clone: Path, bare_remote: Path):
    # Create a feature branch on the remote
    tmp_clone = bare_remote.parent / "tmp_clone2"
    subprocess.run(
        ["git", "clone", str(bare_remote), str(tmp_clone)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "-b", "feature"],
        cwd=tmp_clone,
        check=True,
        capture_output=True,
    )
    (tmp_clone / "feature.txt").write_text("feature")
    subprocess.run(
        ["git", "add", "feature.txt"],
        cwd=tmp_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "feature commit"],
        cwd=tmp_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "origin", "feature"],
        cwd=tmp_clone,
        check=True,
        capture_output=True,
    )

    # Create local tracking branch
    subprocess.run(
        ["git", "fetch", "--all"],
        cwd=local_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "branch", "feature", "origin/feature"],
        cwd=local_clone,
        check=True,
        capture_output=True,
    )

    # Push another commit to feature on remote
    (tmp_clone / "feature2.txt").write_text("feature2")
    subprocess.run(
        ["git", "add", "feature2.txt"],
        cwd=tmp_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "feature commit 2"],
        cwd=tmp_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "origin", "feature"],
        cwd=tmp_clone,
        check=True,
        capture_output=True,
    )

    result = sync_repo(local_clone)
    branch_results = {b.name: b.status for b in result.branches}
    assert branch_results.get("feature") == "updated"
    feature_result = [b for b in result.branches if b.name == "feature"][0]
    assert feature_result.detail == "branch updated"


def test_sync_skips_branch_checked_out_in_other_worktree(
    local_clone: Path, bare_remote: Path, tmp_path: Path
):
    subprocess.run(
        ["git", "branch", "--track", "feature", "origin/main"],
        cwd=local_clone,
        check=True,
        capture_output=True,
    )
    feature_sha = _git_output(local_clone, "rev-parse", "feature")
    worktree = tmp_path / "feature-worktree"
    subprocess.run(
        ["git", "worktree", "add", str(worktree), "feature"],
        cwd=local_clone,
        check=True,
        capture_output=True,
    )
    make_remote_commit(bare_remote, local_clone)

    result = sync_repo(local_clone)

    feature_result = next(
        branch for branch in result.branches if branch.name == "feature"
    )
    assert feature_result.status == "skipped"
    assert feature_result.detail == f"checked out at {worktree}"
    assert _git_output(local_clone, "rev-parse", "feature") == feature_sha
    assert _git_output(worktree, "status", "--porcelain") == ""


def test_sync_updates_branch_referenced_by_detached_worktree(
    local_clone: Path, bare_remote: Path, tmp_path: Path
):
    subprocess.run(
        ["git", "branch", "--track", "feature", "origin/main"],
        cwd=local_clone,
        check=True,
        capture_output=True,
    )
    worktree = tmp_path / "detached-worktree"
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(worktree), "feature"],
        cwd=local_clone,
        check=True,
        capture_output=True,
    )
    remote_sha = make_remote_commit(bare_remote, local_clone)

    result = sync_repo(local_clone)

    feature_result = next(
        branch for branch in result.branches if branch.name == "feature"
    )
    assert feature_result.status == "updated"
    assert _git_output(local_clone, "rev-parse", "feature") == remote_sha


def test_sync_reports_checkout_race_as_skipped(
    local_clone: Path, bare_remote: Path, tmp_path: Path
):
    subprocess.run(
        ["git", "branch", "--track", "feature", "origin/main"],
        cwd=local_clone,
        check=True,
        capture_output=True,
    )
    make_remote_commit(bare_remote, local_clone)
    worktree = tmp_path / "late-worktree"

    with (
        patch(
            "git_auto_sync.sync.git.get_checked_out_branches",
            side_effect=[{}, {"feature": str(worktree)}],
        ),
        patch("git_auto_sync.sync.git.force_branch", return_value=False),
    ):
        result = sync_repo(local_clone)

    feature_result = next(
        branch for branch in result.branches if branch.name == "feature"
    )
    assert feature_result.status == "skipped"
    assert feature_result.detail == f"checked out at {worktree}"


def _git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
