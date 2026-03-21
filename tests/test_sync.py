from __future__ import annotations

import subprocess
from pathlib import Path

from conftest import make_remote_commit
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


def test_sync_dirty_worktree_skips(local_clone: Path, bare_remote: Path):
    make_remote_commit(bare_remote, local_clone)

    # Make worktree dirty
    (local_clone / "dirty.txt").write_text("dirty")

    result = sync_repo(local_clone)
    branch_results = {b.name: b.status for b in result.branches}
    assert branch_results.get("main") == "skipped"


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


def test_sync_non_current_branch_update_ref(local_clone: Path, bare_remote: Path):
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

    # Now sync: main is current, feature should be updated via update-ref
    result = sync_repo(local_clone)
    branch_results = {b.name: b.status for b in result.branches}
    assert branch_results.get("feature") == "updated"
    # Verify the detail says ref updated (not merge)
    feature_result = [b for b in result.branches if b.name == "feature"][0]
    assert feature_result.detail == "ref updated"
