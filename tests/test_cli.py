from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from git_auto_sync.cli import main
from git_auto_sync.config import Config, SyncMode


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


def test_interval_get(tmp_path: Path):
    config_file = tmp_path / "cfg" / "config.toml"

    with patch("git_auto_sync.config.CONFIG_FILE", config_file):
        runner = CliRunner()
        result = runner.invoke(main, ["interval"])
        assert result.exit_code == 0
        assert "10" in result.output


def test_interval_set(tmp_path: Path):
    config_dir = tmp_path / "cfg"
    config_file = config_dir / "config.toml"

    with (
        patch("git_auto_sync.config.CONFIG_FILE", config_file),
        patch("git_auto_sync.config.CONFIG_DIR", config_dir),
        patch("git_auto_sync.cli.scheduler_is_installed", return_value=False),
    ):
        runner = CliRunner()
        result = runner.invoke(main, ["interval", "5"])
        assert result.exit_code == 0
        assert "Interval set to 5 minutes" in result.output


def test_interval_set_reinstalls_scheduler(tmp_path: Path):
    config_dir = tmp_path / "cfg"
    config_file = config_dir / "config.toml"

    with (
        patch("git_auto_sync.config.CONFIG_FILE", config_file),
        patch("git_auto_sync.config.CONFIG_DIR", config_dir),
        patch("git_auto_sync.cli.scheduler_is_installed", return_value=True),
        patch("git_auto_sync.cli.scheduler_uninstall") as mock_uninstall,
        patch("git_auto_sync.cli.scheduler_install") as mock_install,
    ):
        runner = CliRunner()
        result = runner.invoke(main, ["interval", "15"])
        assert result.exit_code == 0
        assert "Scheduler reinstalled" in result.output
        mock_uninstall.assert_called_once()
        mock_install.assert_called_once_with(interval_minutes=15)


def test_interval_rejects_zero():
    runner = CliRunner()
    result = runner.invoke(main, ["interval", "0"])
    assert result.exit_code != 0


def test_mode_get(tmp_path: Path):
    config_file = tmp_path / "config.toml"

    with patch("git_auto_sync.config.CONFIG_FILE", config_file):
        runner = CliRunner()
        result = runner.invoke(main, ["mode"])

    assert result.exit_code == 0
    assert result.output == "sync\n"


def test_mode_set(tmp_path: Path):
    config_dir = tmp_path / "cfg"
    config_file = config_dir / "config.toml"

    with (
        patch("git_auto_sync.config.CONFIG_FILE", config_file),
        patch("git_auto_sync.config.CONFIG_DIR", config_dir),
    ):
        runner = CliRunner()
        result = runner.invoke(main, ["mode", "fetch-only"])

        assert result.exit_code == 0
        assert result.output == "Mode set to fetch-only.\n"
        from git_auto_sync.config import load_config

        assert load_config().mode == SyncMode.FETCH_ONLY


def test_sync_uses_configured_mode(local_clone: Path, tmp_path: Path):
    lock_dir = tmp_path / "lock"
    lock_dir.mkdir()
    lock_file = lock_dir / "sync.lock"

    with (
        patch(
            "git_auto_sync.cli.load_config",
            return_value=Config(mode=SyncMode.FETCH_ONLY),
        ),
        patch("git_auto_sync.lockfile.LOCK_DIR", lock_dir),
        patch("git_auto_sync.lockfile.LOCK_FILE", lock_file),
        patch("git_auto_sync.cli.sync_repo") as mock_sync,
    ):
        mock_sync.return_value.repo = str(local_clone)
        mock_sync.return_value.error = ""
        mock_sync.return_value.branches = []
        mock_sync.return_value.mode = SyncMode.FETCH_ONLY
        runner = CliRunner()
        result = runner.invoke(main, ["sync", str(local_clone)])

    assert result.exit_code == 0
    mock_sync.assert_called_once_with(local_clone, SyncMode.FETCH_ONLY)
