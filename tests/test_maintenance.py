from __future__ import annotations

import subprocess
from pathlib import Path

from git_auto_sync.maintenance import enable_maintenance


def test_enable_maintenance(local_clone: Path):
    assert enable_maintenance(local_clone)

    # Verify maintenance tasks are configured
    result = subprocess.run(
        ["git", "config", "--get", "maintenance.prefetch.enabled"],
        cwd=local_clone,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "true"
