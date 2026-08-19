# git-auto-sync

A CLI tool that keeps Git repositories up-to-date automatically in the background. Use sync mode for safe fast-forward updates or fetch-only mode to refresh remote-tracking branches without changing local work.

## Features

- **Centralized management** — one tool, one scheduler for all your repos
- **Safe by default** — only fast-forward merges; diverged branches are skipped, dirty worktrees are merged when conflict-free
- **Fetch-only mode** — refresh remote-tracking branches without updating local branches, the index, or working tree files
- **Worktree-aware updates** — branches checked out in linked worktrees are never moved
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

# Configure sync interval
git-auto-sync interval          # show current interval
git-auto-sync interval 5        # set to 5 minutes

# Configure mode
git-auto-sync mode              # show current mode
git-auto-sync mode fetch-only   # update remote-tracking branches only
git-auto-sync mode sync         # fetch and fast-forward local branches

# Background scheduling (macOS)
git-auto-sync install           # install launchd scheduler
git-auto-sync uninstall         # remove scheduler

# Manage repos
git-auto-sync remove ~/projects/my-repo
```

## How It Works

Every run fetches all remotes and prunes refs that no longer exist on their remote. The exact fetch behavior depends on the configured mode.

### Sync mode

Sync mode runs the repository's configured fetch refspecs:

```bash
git fetch --all --prune
```

For each local tracking branch:

   - If it's the **current branch**: `git merge --ff-only` (works even with uncommitted changes if no conflicts)
   - If it's checked out in **another worktree**: skip it
   - If it's an **unchecked-out branch**: `git branch --force` to advance it after verifying a fast-forward
   - If the branch has **diverged**: skip and log

### Fetch-only mode

Fetch-only mode requires every configured fetch destination to be under `refs/remotes/`, then disables automatic tag following:

```bash
git fetch --all --prune --no-tags --no-prune-tags
```

The mode stops after fetching and does not update local branches, tags, the index, or working tree files. `--no-prune-tags` overrides global and remote-specific tag-pruning settings. Repositories with mirror refspecs or custom destinations outside `refs/remotes/` are rejected before the fetch starts.

### Git maintenance

Registered repositories enable `prefetch`, `commit-graph`, `loose-objects`, and `incremental-repack` maintenance tasks. Git's prefetch task stores downloaded refs under `refs/prefetch/`; it does not update `origin/main`. A regular fetch is still required to refresh remote-tracking branches.

## Configuration

Config file: `~/.config/git-auto-sync/config.toml`

```toml
repos = [
    "/Users/you/projects/repo1",
    "/Users/you/projects/repo2",
]
interval_minutes = 10
log_level = "INFO"
mode = "sync"
```

| Key                | Default  | Description                  |
|--------------------|----------|------------------------------|
| `repos`            | `[]`     | List of registered repo paths |
| `interval_minutes` | `10`     | Sync interval for scheduler  |
| `log_level`        | `"INFO"` | Logging level                |
| `mode`             | `"sync"` | `"sync"` or `"fetch-only"` |

## Safety

- Only fast-forward merges — never creates merge commits
- Never force-pushes or resets
- Never modifies untracked/ignored files
- Never updates a branch checked out in another linked worktree
- Fetch failures are logged and skipped (offline-safe)
- Lockfile prevents concurrent syncs

In sync mode, `--prune` follows each remote's configured fetch refspec and may prune custom destination refs. Fetch-only mode rejects destinations outside `refs/remotes/` and explicitly disables tag pruning.

## License

MIT
