from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.fixture
def bare_remote(tmp_path: Path) -> Path:
    """Create a bare git repo to act as a remote."""
    remote = tmp_path / "remote.git"
    remote.mkdir()
    _run_git(remote, "init", "--bare")
    _run_git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    return remote


@pytest.fixture
def local_clone(tmp_path: Path, bare_remote: Path) -> Path:
    """Clone from bare_remote, with an initial commit."""
    local = tmp_path / "local"
    _run_git(tmp_path, "clone", str(bare_remote), "local")

    # Configure user for commits
    _run_git(local, "config", "user.email", "test@test.com")
    _run_git(local, "config", "user.name", "Test")

    # Create initial commit
    (local / "file.txt").write_text("initial")
    _run_git(local, "add", "file.txt")
    _run_git(local, "commit", "-m", "initial commit")
    _run_git(local, "push", "origin", "main")

    return local


def make_remote_commit(
    bare_remote: Path, local_clone: Path, filename: str = "remote.txt"
) -> str:
    """Create a commit on the remote (via a temp clone) so local falls behind."""
    tmp_clone = bare_remote.parent / "tmp_clone"
    if tmp_clone.exists():
        import shutil

        shutil.rmtree(tmp_clone)

    _run_git(bare_remote.parent, "clone", str(bare_remote), "tmp_clone")
    _run_git(tmp_clone, "config", "user.email", "test@test.com")
    _run_git(tmp_clone, "config", "user.name", "Test")

    (tmp_clone / filename).write_text("remote content")
    _run_git(tmp_clone, "add", filename)
    _run_git(tmp_clone, "commit", "-m", f"add {filename}")
    _run_git(tmp_clone, "push", "origin", "main")

    # Return the new remote SHA
    result = _run_git(tmp_clone, "rev-parse", "HEAD")
    return result.stdout.strip()
