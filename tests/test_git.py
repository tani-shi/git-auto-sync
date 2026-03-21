from __future__ import annotations

from pathlib import Path

from git_auto_sync.git import (
    fetch_all,
    get_current_branch,
    get_local_branches,
    is_git_repo,
    is_worktree_clean,
)


def test_is_git_repo(local_clone: Path, tmp_path: Path):
    assert is_git_repo(local_clone)
    assert not is_git_repo(tmp_path / "not_a_repo")


def test_get_current_branch(local_clone: Path):
    assert get_current_branch(local_clone) == "main"


def test_get_local_branches(local_clone: Path):
    branches = get_local_branches(local_clone)
    names = [b.name for b in branches]
    assert "main" in names


def test_is_worktree_clean(local_clone: Path):
    assert is_worktree_clean(local_clone)

    (local_clone / "dirty.txt").write_text("dirty")
    assert not is_worktree_clean(local_clone)


def test_fetch_all(local_clone: Path):
    assert fetch_all(local_clone)
