# git-auto-sync

A CLI tool that keeps local git repositories up-to-date automatically in the background. Combines `git fetch` with safe fast-forward merges and `git maintenance`.

## Features

- **Centralized management** — one tool, one scheduler for all your repos
- **Safe by default** — only fast-forward merges; diverged or dirty branches are skipped
- **Background daemon** — launchd integration on macOS for automatic syncing
- **git maintenance** — enables prefetch, commit-graph, loose-objects, incremental-repack

## Installation

```bash
uv tool install git-auto-sync
```

Or for development:

```bash
git clone https://github.com/tani-shi/git-auto-sync.git
cd git-auto-sync
uv sync --dev
```

## Usage

```bash
# Register repositories
git-auto-sync add ~/projects/my-repo
git-auto-sync add ~/projects/another-repo

# View registered repos
git-auto-sync list

# Run sync manually
git-auto-sync sync              # sync all registered repos
git-auto-sync sync ~/projects/my-repo  # sync a specific repo

# Check results
git-auto-sync status            # last sync results
git-auto-sync logs              # recent log entries

# Background scheduling (macOS)
git-auto-sync install           # install launchd scheduler
git-auto-sync uninstall         # remove scheduler

# Manage repos
git-auto-sync remove ~/projects/my-repo
```

## How It Works

For each registered repository:

1. **Fetch** all remotes (`git fetch --all`)
2. For each local tracking branch:
   - If it's the **current branch** and the worktree is clean: `git merge --ff-only`
   - If it's a **non-current branch**: `git update-ref` to advance the ref
   - If the branch has **diverged**: skip and log
3. Enable **git maintenance** tasks for optimized repo performance

## Configuration

Config file: `~/.config/git-auto-sync/config.toml`

```toml
repos = [
    "/Users/you/projects/repo1",
    "/Users/you/projects/repo2",
]
interval_minutes = 10
log_level = "INFO"
```

| Key                | Default  | Description                  |
|--------------------|----------|------------------------------|
| `repos`            | `[]`     | List of registered repo paths |
| `interval_minutes` | `10`     | Sync interval for scheduler  |
| `log_level`        | `"INFO"` | Logging level                |

## Safety

- Only fast-forward merges — never creates merge commits
- Never force-pushes or resets
- Never modifies untracked/ignored files
- Fetch failures are logged and skipped (offline-safe)
- Lockfile prevents concurrent syncs

## License

MIT
