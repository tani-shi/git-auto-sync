from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from git_auto_sync.lockfile import SyncAlreadyRunningError, acquire_lock


def test_acquire_and_release(tmp_path: Path):
    lock_file = tmp_path / "sync.lock"

    with (
        patch("git_auto_sync.lockfile.LOCK_DIR", tmp_path),
        patch("git_auto_sync.lockfile.LOCK_FILE", lock_file),
    ):
        with acquire_lock():
            assert lock_file.exists()


def test_concurrent_lock_raises(tmp_path: Path):
    lock_file = tmp_path / "sync.lock"

    with (
        patch("git_auto_sync.lockfile.LOCK_DIR", tmp_path),
        patch("git_auto_sync.lockfile.LOCK_FILE", lock_file),
    ):
        with acquire_lock():
            with pytest.raises(SyncAlreadyRunningError):
                with acquire_lock():
                    pass
