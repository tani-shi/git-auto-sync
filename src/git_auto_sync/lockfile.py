from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

LOCK_DIR = Path.home() / ".config" / "git-auto-sync"
LOCK_FILE = LOCK_DIR / "sync.lock"


class SyncAlreadyRunningError(Exception):
    pass


@contextmanager
def acquire_lock() -> Generator[None]:
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_WRONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        raise SyncAlreadyRunningError(
            "Another git-auto-sync process is already running"
        )
    try:
        os.write(fd, str(os.getpid()).encode())
        os.ftruncate(fd, len(str(os.getpid())))
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        try:
            LOCK_FILE.unlink()
        except FileNotFoundError:
            pass
