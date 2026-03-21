from __future__ import annotations

import logging
from pathlib import Path

from git_auto_sync.git import run_git

logger = logging.getLogger("git_auto_sync")

MAINTENANCE_TASKS = [
    "prefetch",
    "commit-graph",
    "loose-objects",
    "incremental-repack",
]


def enable_maintenance(repo: Path) -> bool:
    result = run_git(repo, "maintenance", "register")
    if result.returncode != 0:
        logger.warning(
            "Failed to register maintenance for %s: %s",
            repo,
            result.stderr.strip(),
        )
        return False

    for task in MAINTENANCE_TASKS:
        run_git(repo, "config", f"maintenance.{task}.enabled", "true")

    logger.info("Enabled git maintenance for %s", repo)
    return True


def disable_maintenance(repo: Path) -> bool:
    result = run_git(repo, "maintenance", "unregister")
    if result.returncode != 0:
        logger.warning(
            "Failed to unregister maintenance for %s: %s",
            repo,
            result.stderr.strip(),
        )
        return False

    logger.info("Disabled git maintenance for %s", repo)
    return True
