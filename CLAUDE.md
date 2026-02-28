# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EC2 Connect v2.0 is a Terminal User Interface (TUI) application for managing AWS EC2 instances. Built with Python and Textual, it provides an interactive interface for listing instances, SSHing into servers, transferring files via SCP, browsing remote file systems, running commands, and scanning servers for keywords.

**Key capabilities:**
- Multi-region EC2 instance listing with caching
- SSH connection management with bastion/jump host support
- SCP file transfer (upload/download)
- Remote file system browser
- Remote command execution overlay
- Keyword-based server scanning with persistent results
- SSH key auto-discovery and management

## Development Commands

```bash
# Install for production
pipx install .

# Update existing pipx installation
pipx install . --force

# Run directly without installing (for development)
PYTHONPATH=src python3 -m ec2_ssh.main

# Or
python src/ec2_ssh/main.py

# Install dependencies directly (alternative to pipx)
pip install -e ".[dev]"
```

There are no tests, linter, or CI pipeline currently configured.

## Architecture

EC2 Connect v2.0 is a modular TUI application built on the Textual framework. The codebase is organized into five main packages:

### Package Structure

```
src/ec2_ssh/
├── config/          # Configuration management
│   ├── manager.py       # ConfigManager - loads/saves/migrates config
│   ├── schema.py        # Dataclass definitions: AppConfig, ScanRule, ConnectionProfile
│   └── migration.py     # Config version migration logic
├── services/        # Business logic layer
│   ├── interfaces.py    # Abstract base classes for all services
│   ├── aws_service.py   # EC2 instance fetching via boto3
│   ├── cache_service.py # Instance list caching with TTL
│   ├── ssh_service.py   # SSH key management, command building, agent integration
│   ├── connection_service.py  # Connection profile resolution, ProxyJump handling
│   ├── scan_service.py  # Server scanning (keyword search in files/commands)
│   ├── keyword_store.py # Persistent storage for scan results
│   ├── scp_service.py   # SCP command building for file transfer
│   └── terminal_service.py  # Terminal detection and external SSH launch
├── screens/         # Textual screens (views)
│   ├── main_menu.py     # Main menu with 6 options
│   ├── instance_list.py # Tabular instance list
│   ├── search.py        # Search/filter overlay
│   ├── server_actions.py  # Actions for selected server
│   ├── key_management.py  # SSH key configuration UI
│   ├── settings.py      # Settings editor
│   ├── file_browser.py  # Remote file system browser
│   ├── command_overlay.py  # Remote command execution panel
│   ├── scp_transfer.py  # File transfer UI
│   └── scan_results.py  # Keyword scan results viewer
├── widgets/         # Reusable UI components
│   ├── instance_table.py    # DataTable for instances
│   ├── remote_tree.py       # Tree widget for remote filesystem
│   ├── status_bar.py        # Status bar component
│   ├── progress_indicator.py  # Progress display
│   └── command_output.py    # Command output display
├── utils/           # Utility functions
│   ├── formatting.py    # String formatting helpers
│   ├── platform_utils.py  # OS detection
│   └── ssh_utils.py     # SSH-specific utilities
├── app.py           # EC2ConnectApp (main Textual App class)
└── main.py          # Entry point
```

### Key Design Patterns

**Service Layer:**
- All services implement abstract interfaces defined in `services/interfaces.py`
- Services are instantiated in `EC2ConnectApp._init_services()` and attached to `self.app`
- Screens access services via `self.app.<service>` (e.g., `self.app.ssh_service.get_key_path(instance_id)`)

**Configuration:**
- Config is a dataclass (`AppConfig`) with nested dataclasses (`ScanRule`, `ConnectionProfile`, `ConnectionRule`)
- Schema versioning with migration support (`CONFIG_VERSION = 2`)
- JSON storage at `~/.ec2_ssh_config.json`
- ConfigManager handles loading, saving, migration, and validation

**Screens and Navigation:**
- All screens inherit from `textual.screen.Screen`
- Screen navigation via `self.app.push_screen()` and `self.app.pop_screen()`
- Lazy-loaded screens defined in `EC2ConnectApp.SCREENS` dict
- Shared state stored in `self.app.instances` (list of all fetched instances)

**Async Pattern:**
- AWS API calls and SSH operations are async (`async def`)
- Long-running tasks use `self.run_worker()` to avoid blocking UI
- Workers update UI via `self.notify()` and screen updates

## Key Design Decisions

**Textual TUI Framework:**
- Chosen for cross-platform TUI support, async-first design, and rich widget library
- Uses reactive data patterns and CSS-like styling

**SSH Connection Strategy:**
- Uses OpenSSH ProxyJump (`-J`) or ProxyCommand for bastion hosts (depending on bastion_key)
- `IdentitiesOnly=yes` only added when `-i` flag is present (prevents "Too many auth failures" without breaking agent-only auth)
- SSH key auto-discovery searches `~/.ssh/` with multiple patterns (exact match, `.pem`, fuzzy matching)
- External SSH sessions launched in new terminal window via wrapper script that keeps terminal open on failure
- Terminal auto-detection supports gnome-terminal, konsole, alacritty, kitty, xterm, xfce4-terminal, mate-terminal, tilix, Terminal.app, iTerm.app, wt.exe
- `terminal_emulator` config setting feeds into TerminalService preferred parameter

**Instance Caching (stale-while-revalidate):**
- Cache stored in `~/.ec2_ssh_cache.json` with timestamp
- Default TTL: 3600 seconds / 1 hour (configurable via `cache_ttl_seconds`)
- On startup: shows stale cached data immediately, then refreshes in background if expired
- Force refresh via `R` key in instance list
- `CacheService.load()` respects TTL; `load_any()` returns data regardless of age; `is_fresh()` checks TTL

**Server Scanning:**
- Scans run SSH commands or search files for keywords
- Match rules define which instances to scan (`match_conditions` on name/region/state)
- Results stored persistently in keyword store (`~/.ec2_ssh_keywords.json`)
- Searchable from UI and scan results screen

**Connection Profiles:**
- Define bastion/proxy configuration per environment
- Applied to instances via connection rules with match conditions
- When bastion_key is set → uses ProxyCommand (allows separate bastion key)
- When no bastion_key → uses simpler ProxyJump (`-J`)
- Supports custom ProxyCommand for advanced scenarios

**Configuration Migration:**
- v1 config (flat structure) auto-migrates to v2 (nested profiles/rules)
- Migration runs on first load if `version` field missing or < 2
- Preserves backward compatibility

## User Configuration Files

At runtime, the application creates and uses:
- `~/.ec2_ssh_config.json` — Main configuration (keys, profiles, scan rules)
- `~/.ec2_ssh_cache.json` — Cached instance list with timestamp
- `~/.ec2_ssh_keywords.json` — Keyword scan results store
- `~/.ec2_ssh_logs/ec2_ssh.log` — Application log (SSH commands, errors, cache status)
- `~/.ec2_ssh_logs/ec2ssh_*.sh` — Temporary wrapper scripts for SSH terminal sessions

## Dependencies

- `boto3` — AWS SDK for Python (EC2 API)
- `tabulate` — Table formatting (legacy, may be removed)
- `textual>=0.40.0` — TUI framework

Optional (stdlib on Unix, missing on Windows):
- `readline` — Tab autocomplete for key paths (graceful fallback if missing)

## Entry Point

Defined in `pyproject.toml`:
```toml
[project.scripts]
ec2-ssh = "ec2_ssh.main:main"
```

The `main()` function in `src/ec2_ssh/main.py` creates and runs the Textual app:
```python
def main():
    app = EC2ConnectApp()
    app.run()
```

## Version

Current version: **2.0.0** (defined in `pyproject.toml` and `src/ec2_ssh/__init__.py`)
