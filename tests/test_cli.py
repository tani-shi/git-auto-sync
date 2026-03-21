from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from git_auto_sync.cli import main


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "2026.3.21" in result.output


def test_add_and_list(local_clone: Path, tmp_path: Path):
    config_file = tmp_path / "cfg" / "config.toml"
    config_dir = tmp_path / "cfg"

    with (
        patch("git_auto_sync.config.CONFIG_FILE", config_file),
        patch("git_auto_sync.config.CONFIG_DIR", config_dir),
        patch("git_auto_sync.cli.load_config") as mock_load,
        patch("git_auto_sync.cli.save_config"),
        patch("git_auto_sync.cli.enable_maintenance"),
    ):
        # Use real load_config for the group, mock for add
        from git_auto_sync.config import Config

        mock_load.return_value = Config()

        runner = CliRunner()
        result = runner.invoke(main, ["add", str(local_clone)])
        assert result.exit_code == 0
        assert "Added" in result.output


def test_add_non_git_dir(tmp_path: Path):
    non_git = tmp_path / "not_git"
    non_git.mkdir()

    runner = CliRunner()
    result = runner.invoke(main, ["add", str(non_git)])
    assert result.exit_code != 0
    assert "not a git repository" in result.output


def test_list_empty(tmp_path: Path):
    config_file = tmp_path / "cfg" / "config.toml"

    with patch("git_auto_sync.config.CONFIG_FILE", config_file):
        runner = CliRunner()
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "No repositories registered" in result.output


def test_sync_no_repos(tmp_path: Path):
    config_file = tmp_path / "cfg" / "config.toml"
    lock_dir = tmp_path / "lock"
    lock_dir.mkdir()
    lock_file = lock_dir / "sync.lock"

    with (
        patch("git_auto_sync.config.CONFIG_FILE", config_file),
        patch("git_auto_sync.lockfile.LOCK_DIR", lock_dir),
        patch("git_auto_sync.lockfile.LOCK_FILE", lock_file),
    ):
        runner = CliRunner()
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0
        assert "No repositories registered" in result.output


def test_logs_no_file(tmp_path: Path):
    fake_log = tmp_path / "nonexistent.log"

    with patch("git_auto_sync.cli.LOG_FILE", fake_log):
        runner = CliRunner()
        result = runner.invoke(main, ["logs"])
        assert result.exit_code == 0
        assert "No logs found" in result.output
