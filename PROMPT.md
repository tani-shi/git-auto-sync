# git-auto-sync

## Overview

A CLI tool that keeps local git repositories up-to-date automatically in the background.
Combines `git maintenance` (prefetch, gc, etc.) with safe fast-forward merges.

## Goals

- **Centralized management**: One tool, one scheduler — no scattered cron jobs
- **Safe by default**: Only fast-forward merges; skip diverged or dirty branches
- **CLI interface**: Interactive commands for status, add/remove repos, manual sync, logs
- **Background daemon**: Single scheduled process (launchd on macOS) handles all repos

## Core Behavior

1. **Fetch**: `git fetch --all` for each registered repo
2. **Fast-forward**: For each local tracking branch, if the remote is strictly ahead (local is ancestor of remote):
   - **Current branch**: merge `--ff-only` only if working tree is clean
   - **Other branches**: `git update-ref` to advance the ref directly
3. **Skip**: Diverged branches, uncommitted changes — log and move on
4. **git maintenance**: Enable `prefetch`, `commit-graph`, `loose-objects`, `incremental-repack` for registered repos

## CLI Commands

```
git-auto-sync add <path>        # Register a repo
git-auto-sync remove <path>     # Unregister a repo
git-auto-sync list              # Show registered repos and their status
git-auto-sync sync [<path>]     # Run sync now (all or specific repo)
git-auto-sync status            # Show last sync time, results, errors
git-auto-sync logs              # Show recent sync logs
git-auto-sync install           # Install launchd plist (macOS) for background scheduling
git-auto-sync uninstall         # Remove background scheduler
```

## Configuration

- Config file: `~/.config/git-auto-sync/config.toml`
- Stores: registered repos, sync interval, log level
- Default sync interval: 10 minutes

## Constraints

- No merge commits — fast-forward only
- Never force-push or reset
- Never modify untracked/ignored files
- Offline-safe: fetch failures are logged and skipped silently
- Single process: avoid concurrent syncs (use a lockfile)

## Tech Stack

- TBD (Python with Click? Rust? Shell?)

## Non-Goals

- Pushing local changes to remote
- Resolving merge conflicts
- GUI
