from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from git_auto_sync.config import Config, load_config, save_config


def test_default_config():
    config = Config()
    assert config.repos == []
    assert config.interval_minutes == 10
    assert config.log_level == "INFO"


def test_roundtrip(tmp_path: Path):
    config_file = tmp_path / "config.toml"
    config_dir = tmp_path

    with (
        patch("git_auto_sync.config.CONFIG_FILE", config_file),
        patch("git_auto_sync.config.CONFIG_DIR", config_dir),
    ):
        original = Config(
            repos=["/path/to/repo1", "/path/to/repo2"],
            interval_minutes=5,
            log_level="DEBUG",
        )
        save_config(original)
        loaded = load_config()

        assert loaded.repos == original.repos
        assert loaded.interval_minutes == original.interval_minutes
        assert loaded.log_level == original.log_level


def test_load_missing_file(tmp_path: Path):
    config_file = tmp_path / "nonexistent" / "config.toml"

    with patch("git_auto_sync.config.CONFIG_FILE", config_file):
        config = load_config()
        assert config.repos == []
        assert config.interval_minutes == 10
