from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w

CONFIG_DIR = Path.home() / ".config" / "git-auto-sync"
CONFIG_FILE = CONFIG_DIR / "config.toml"


@dataclass
class Config:
    repos: list[str] = field(default_factory=list)
    interval_minutes: int = 10
    log_level: str = "INFO"


def load_config() -> Config:
    if not CONFIG_FILE.exists():
        return Config()
    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)
    return Config(
        repos=data.get("repos", []),
        interval_minutes=data.get("interval_minutes", 10),
        log_level=data.get("log_level", "INFO"),
    )


def save_config(config: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "repos": config.repos,
        "interval_minutes": config.interval_minutes,
        "log_level": config.log_level,
    }
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)
