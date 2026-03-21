from __future__ import annotations

import logging
import plistlib
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("git_auto_sync")

PLIST_LABEL = "dev.tani-shi.git-auto-sync"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"


def _find_executable() -> str:
    path = shutil.which("git-auto-sync")
    if path:
        return path
    # Fallback: use the Python entry point directly
    import sys

    return f"{sys.executable} -m git_auto_sync.cli"


def install(interval_minutes: int = 10) -> None:
    executable = _find_executable()

    plist = {
        "Label": PLIST_LABEL,
        "ProgramArguments": executable.split() + ["sync"],
        "StartInterval": interval_minutes * 60,
        "StandardOutPath": str(
            Path.home() / ".config" / "git-auto-sync" / "logs" / "launchd-stdout.log"
        ),
        "StandardErrorPath": str(
            Path.home() / ".config" / "git-auto-sync" / "logs" / "launchd-stderr.log"
        ),
        "RunAtLoad": True,
    }

    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PLIST_PATH, "wb") as f:
        plistlib.dump(plist, f)

    subprocess.run(
        ["launchctl", "load", str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )
    logger.info("Installed launchd plist at %s", PLIST_PATH)


def uninstall() -> None:
    if not PLIST_PATH.exists():
        logger.warning("Plist not found at %s", PLIST_PATH)
        return

    subprocess.run(
        ["launchctl", "unload", str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )
    PLIST_PATH.unlink(missing_ok=True)
    logger.info("Uninstalled launchd plist from %s", PLIST_PATH)


def is_installed() -> bool:
    return PLIST_PATH.exists()
