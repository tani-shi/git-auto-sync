from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path.home() / ".config" / "git-auto-sync" / "logs"
LOG_FILE = LOG_DIR / "sync.log"


def setup_logging(level: str = "INFO") -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("git_auto_sync")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(file_handler)

        stderr_handler = logging.StreamHandler()
        stderr_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(stderr_handler)
