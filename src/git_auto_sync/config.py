from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import tomli_w

CONFIG_DIR = Path.home() / ".config" / "git-auto-sync"
CONFIG_FILE = CONFIG_DIR / "config.toml"


class ConfigError(ValueError):
    pass


class SyncMode(str, Enum):
    SYNC = "sync"
    FETCH_ONLY = "fetch-only"


@dataclass
class Config:
    repos: list[str] = field(default_factory=list)
    interval_minutes: int = 10
    log_level: str = "INFO"
    mode: SyncMode = SyncMode.SYNC


def load_config() -> Config:
    if not CONFIG_FILE.exists():
        return Config()
    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)
    try:
        mode = SyncMode(data.get("mode", SyncMode.SYNC.value))
    except ValueError as error:
        valid_modes = ", ".join(mode.value for mode in SyncMode)
        raise ConfigError(
            f"Invalid mode in {CONFIG_FILE}: expected one of {valid_modes}"
        ) from error
    return Config(
        repos=data.get("repos", []),
        interval_minutes=data.get("interval_minutes", 10),
        log_level=data.get("log_level", "INFO"),
        mode=mode,
    )


def save_config(config: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "repos": config.repos,
        "interval_minutes": config.interval_minutes,
        "log_level": config.log_level,
        "mode": config.mode.value,
    }
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)
