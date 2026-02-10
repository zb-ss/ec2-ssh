"""Help screen for EC2 Connect v2.0."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Markdown


HELP_TEXT = """
# EC2 Connect v2.0 — User Manual

## Overview

EC2 Connect is a Terminal User Interface (TUI) for managing and connecting to AWS EC2 instances.
It provides SSH connections, file browsing, command execution, SCP transfers, and server scanning —
all from a single interface.

## Main Menu

| Option | Shortcut | Description |
|--------|----------|-------------|
| **List Instances** | `1` or `L` | Fetch and display all EC2 instances across AWS regions |
| **Search** | `2` or `S` | Search instances by name/type/ID, and keyword scan results |
| **Manage SSH Keys** | `3` or `K` | Configure SSH keys, auto-discovery, and SSH agent integration |
| **Scan Servers** | `4` or `C` | Run configured scans on all running instances |
| **Settings** | `5` or `T` | Edit configuration: username, cache, scan paths, theme |
| **Quit** | `6` or `Q` | Exit the application |

## Instance List

When you select **List Instances**, all EC2 instances are fetched (with caching).

| Action | Shortcut | Description |
|--------|----------|-------------|
| Navigate | `↑` `↓` | Move between instances in the table |
| Select | `Enter` | Open server actions for the selected instance |
| SSH Connect | `S` | Quick SSH connect to the selected instance |
| Search | `/` | Focus the search/filter input |
| Refresh | `R` | Re-fetch instances from AWS (bypass cache) |
| Back | `Escape` | Return to main menu |

## Server Actions

After selecting an instance, you can:

### Browse Files
Opens a remote file browser showing the server's filesystem via SSH. Directories expand lazily
on click. Configured scan paths appear as root nodes.

### Run Command
Opens a command overlay where you can type and execute commands on the remote server.
Output appears in real-time. Use `↑`/`↓` to navigate command history.

### SSH Connect
Launches a **new terminal window** with an SSH session to the selected server.
Automatically detects your terminal emulator (gnome-terminal, konsole, xfce4-terminal,
Terminal.app, iTerm, etc.).

### SCP Transfer
Upload or download files via SCP. Supports bastion/proxy connections transparently.

### View Scan Results
Displays keyword scan data previously collected from this server.

## Connection Profiles & Bastion Support

EC2 Connect supports SSH connections through bastion hosts using ProxyJump (`-J`).

Configure in `~/.ec2_ssh_config.json`:
```json
{
  "connection_profiles": [
    {
      "name": "my-bastion",
      "bastion_host": "bastion.example.com",
      "bastion_user": "ubuntu",
      "ssh_port": 22
    }
  ],
  "connection_rules": [
    {
      "name": "private-instances",
      "match_conditions": {"has_public_ip": "false"},
      "profile_name": "my-bastion"
    }
  ]
}
```

## SSH Key Management

EC2 Connect auto-discovers SSH keys in `~/.ssh/` based on the AWS key pair name.
It searches for patterns like `key_name.pem`, `id_rsa_key_name`, etc.

You can also:
- Set instance-specific keys
- Set a default key for all instances
- Add keys to SSH agent
- Fix key file permissions (600/400)

## Scanning & Keywords

Configure paths and commands to scan on servers:

```json
{
  "default_scan_paths": ["~/shared/", "/var/log/"],
  "scan_rules": [
    {
      "name": "web-servers",
      "match_conditions": {"name_contains": "web"},
      "scan_paths": ["/var/www", "/var/log/nginx"],
      "scan_commands": ["pm2 list", "systemctl status nginx"]
    }
  ]
}
```

Results are stored in the keyword store and searchable via the Search screen.

## Configuration

All settings are stored in `~/.ec2_ssh_config.json`. Key fields:

| Field | Default | Description |
|-------|---------|-------------|
| `default_username` | `ec2-user` | SSH username for connections |
| `cache_ttl_seconds` | `300` | Instance cache duration (5 min) |
| `default_scan_paths` | `["~/shared/"]` | Paths to scan on all servers |
| `terminal_emulator` | `auto` | Preferred terminal (`auto` for detection) |
| `theme` | `dark` | UI theme (`dark` or `light`) |

## Keyboard Shortcuts (Global)

| Key | Action |
|-----|--------|
| `Q` | Quit application |
| `?` or `H` | Open this help screen |
| `Escape` | Go back / close overlay |
| `Tab` | Next focusable widget |
| `Shift+Tab` | Previous focusable widget |

## Requirements

- **Python** 3.8+
- **AWS credentials** configured (`~/.aws/credentials` or env vars)
- **Permissions**: `ec2:DescribeInstances`, `ec2:DescribeRegions`
"""


class HelpScreen(Screen):
    """Help screen displaying the user manual."""

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
        Binding("q", "back", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Markdown(HELP_TEXT, id="help_content"),
            id="help_container"
        )
        yield Footer()

    def action_back(self) -> None:
        """Navigate back."""
        self.app.pop_screen()
