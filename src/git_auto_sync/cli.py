from __future__ import annotations

from pathlib import Path

import click

from git_auto_sync import __version__
from git_auto_sync.config import load_config, save_config
from git_auto_sync.git import get_current_branch, is_git_repo, is_worktree_clean
from git_auto_sync.lockfile import SyncAlreadyRunningError, acquire_lock
from git_auto_sync.log import LOG_FILE, setup_logging
from git_auto_sync.maintenance import disable_maintenance, enable_maintenance
from git_auto_sync.scheduler import install as scheduler_install
from git_auto_sync.scheduler import is_installed as scheduler_is_installed
from git_auto_sync.scheduler import uninstall as scheduler_uninstall
from git_auto_sync.sync import SyncResult, sync_all, sync_repo


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Keep local git repositories up-to-date automatically."""
    config = load_config()
    setup_logging(config.log_level)


@main.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
def add(path: str) -> None:
    """Register a repository for auto-sync."""
    repo_path = Path(path)
    if not is_git_repo(repo_path):
        click.echo(f"Error: {path} is not a git repository", err=True)
        raise SystemExit(1)

    config = load_config()
    resolved = str(repo_path.resolve())

    if resolved in config.repos:
        click.echo(f"Already registered: {resolved}")
        return

    config.repos.append(resolved)
    save_config(config)
    enable_maintenance(repo_path)
    click.echo(f"Added: {resolved}")


@main.command()
@click.argument("path", type=click.Path(resolve_path=True))
def remove(path: str) -> None:
    """Unregister a repository from auto-sync."""
    config = load_config()
    resolved = str(Path(path).resolve())

    if resolved not in config.repos:
        click.echo(f"Not registered: {resolved}", err=True)
        raise SystemExit(1)

    config.repos.remove(resolved)
    save_config(config)
    disable_maintenance(Path(resolved))
    click.echo(f"Removed: {resolved}")


@main.command("list")
def list_repos() -> None:
    """Show registered repositories."""
    config = load_config()
    if not config.repos:
        click.echo(
            "No repositories registered. Use 'git-auto-sync add <path>' to add one."
        )
        return

    for repo in config.repos:
        repo_path = Path(repo)
        if not repo_path.exists():
            click.echo(f"  {repo}  [missing]")
            continue

        branch = get_current_branch(repo_path) or "detached"
        clean = "clean" if is_worktree_clean(repo_path) else "dirty"
        click.echo(f"  {repo}  [{branch}] ({clean})")


@main.command()
@click.argument(
    "path",
    required=False,
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
def sync(path: str | None) -> None:
    """Run sync now (all repos or a specific one)."""
    try:
        with acquire_lock():
            if path:
                result = sync_repo(Path(path))
                _print_sync_result(result)
            else:
                config = load_config()
                if not config.repos:
                    click.echo("No repositories registered.")
                    return
                results = sync_all(config.repos)
                for r in results:
                    _print_sync_result(r)
    except SyncAlreadyRunningError:
        click.echo("Error: Another sync is already running", err=True)
        raise SystemExit(1)


@main.command()
def status() -> None:
    """Show last sync results."""
    if not LOG_FILE.exists():
        click.echo("No sync history found.")
        return

    # Show last sync entries from log
    lines = LOG_FILE.read_text().splitlines()
    sync_lines = [line for line in lines if "Synced " in line]
    if not sync_lines:
        click.echo("No sync history found.")
        return

    # Show the most recent batch (lines with the same timestamp prefix)
    last_time = sync_lines[-1][:19]  # "YYYY-MM-DD HH:MM:SS"
    click.echo("Last sync:")
    for line in sync_lines:
        if line[:19] == last_time:
            click.echo(f"  {line}")


@main.command()
@click.option("-n", "--lines", default=20, help="Number of lines to show")
def logs(lines: int) -> None:
    """Show recent sync logs."""
    if not LOG_FILE.exists():
        click.echo("No logs found.")
        return

    all_lines = LOG_FILE.read_text().splitlines()
    for line in all_lines[-lines:]:
        click.echo(line)


@main.command()
@click.argument("minutes", required=False, type=click.IntRange(min=1))
def interval(minutes: int | None) -> None:
    """Get or set the sync interval in minutes."""
    config = load_config()

    if minutes is None:
        click.echo(f"{config.interval_minutes}")
        return

    config.interval_minutes = minutes
    save_config(config)
    click.echo(f"Interval set to {minutes} minutes.")

    if scheduler_is_installed():
        scheduler_uninstall()
        scheduler_install(interval_minutes=minutes)
        click.echo("Scheduler reinstalled with new interval.")


@main.command()
def install() -> None:
    """Install background scheduler (launchd on macOS)."""
    if scheduler_is_installed():
        click.echo("Scheduler is already installed.")
        return

    config = load_config()
    scheduler_install(interval_minutes=config.interval_minutes)
    click.echo("Background scheduler installed.")
    click.echo(f"Sync will run every {config.interval_minutes} minutes.")


@main.command()
def uninstall() -> None:
    """Remove background scheduler."""
    if not scheduler_is_installed():
        click.echo("Scheduler is not installed.")
        return

    scheduler_uninstall()
    click.echo("Background scheduler removed.")


def _print_sync_result(result: SyncResult) -> None:
    if result.error and not result.branches:
        click.echo(f"  {result.repo}: {result.error}")
        return

    click.echo(f"  {result.repo}:")
    for b in result.branches:
        detail = f" ({b.detail})" if b.detail else ""
        click.echo(f"    {b.name}: {b.status}{detail}")
