from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from git_auto_sync.scheduler import PLIST_LABEL, is_installed


def test_is_installed_false(tmp_path: Path):
    fake_plist = tmp_path / f"{PLIST_LABEL}.plist"
    with patch("git_auto_sync.scheduler.PLIST_PATH", fake_plist):
        assert not is_installed()


def test_is_installed_true(tmp_path: Path):
    fake_plist = tmp_path / f"{PLIST_LABEL}.plist"
    fake_plist.write_text("<plist/>")
    with patch("git_auto_sync.scheduler.PLIST_PATH", fake_plist):
        assert is_installed()
