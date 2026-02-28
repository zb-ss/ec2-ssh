# EC2 Connect

A modern Terminal User Interface (TUI) for managing AWS EC2 instances — list, search, SSH, SCP, and scan servers across all regions.

## Quick Install

```bash
curl -sSL https://raw.githubusercontent.com/zb-ss/ec2-ssh/master/install.sh | bash
```

Or install manually:

```bash
git clone https://github.com/zb-ss/ec2-ssh.git
cd ec2-ssh
pipx install .
```

## Features

- **Interactive TUI** with mouse and keyboard support powered by Textual
- **List and search** EC2 instances across all AWS regions
- **SSH into instances** — launches in new terminal window
- **Run remote commands** via overlay panel (execute commands without leaving the TUI)
- **Browse remote file systems** — interactive file tree navigation
- **SCP file transfer** — upload/download files with progress tracking
- **Keyword-based server scanning** — search file contents across all instances
- **Bastion host / jump server support** via ProxyJump
- **SSH key management** with auto-discovery and autocomplete
- **Instance caching** for fast startup (configurable TTL)
- **Fully configurable** — no hardcoded values, all settings in JSON

## Prerequisites

- Python 3.8+
- AWS CLI configured with credentials (`~/.aws/credentials` and `~/.aws/config`)
- SSH client (standard on Linux/macOS, available on Windows via OpenSSH)
- `pipx` for isolated installation (recommended)

Your AWS credentials must have permissions for:
- `ec2:DescribeInstances`
- `ec2:DescribeRegions`

## Usage

Launch the application:

```bash
ec2-ssh
```

For debug logging (prints to stderr and writes to `~/.ec2_ssh_logs/ec2_ssh.log`):

```bash
ec2-ssh --debug
```

### Main Menu

Upon launch, you'll see 6 options:

1. **List Instances** — View all EC2 instances across all regions with filtering
2. **Search** — Filter instances by name, type, region, or state
3. **Manage SSH Keys** — Configure default and instance-specific SSH keys
4. **Scan Servers** — Run keyword scans across all running instances
5. **Settings** — Configure connection profiles, scan rules, and preferences
6. **Quit** — Exit the application

### Server Actions

When you select a server from the instance list, you can:

- **Browse Files** — Navigate the remote file system with an interactive tree view
- **Run Command** — Execute commands on the remote server (output shown in overlay)
- **SSH Connect** — Launch an SSH session in a new terminal window
- **SCP Transfer** — Upload or download files and directories
- **View Scan Results** — See keyword scan results for this server
- **Back** — Return to instance list

### Configuration

All configuration is stored in `~/.ec2_ssh_config.json`. The file is created automatically on first run with sensible defaults.

#### Configuration Reference

```json
{
  "version": 2,
  "default_key": "/home/user/.ssh/my-default-key.pem",
  "instance_keys": {
    "i-0123456789abcdef0": "/home/user/.ssh/special-key.pem"
  },
  "default_username": "ec2-user",
  "cache_ttl_seconds": 3600,
  "terminal_emulator": "auto",
  "theme": "dark",
  "keyword_store_path": "~/.ec2_ssh_keywords.json",
  "default_scan_paths": ["~/shared/", "/var/log/app.log"],
  "scan_rules": [],
  "connection_profiles": [],
  "connection_rules": []
}
```

**Field descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `version` | int | Config schema version (current: 2) |
| `default_key` | string | Default SSH key path for all instances |
| `instance_keys` | object | Instance-specific key mappings `{instance_id: key_path}` |
| `default_username` | string | Default SSH username (default: `ec2-user`) |
| `cache_ttl_seconds` | int | Instance cache TTL in seconds (default: 3600 = 1 hour) |
| `terminal_emulator` | string | Terminal preference: `auto`, `gnome-terminal`, `konsole`, `alacritty`, `kitty`, `xfce4-terminal`, `Terminal.app`, `iTerm.app`, `wt.exe`, etc. |
| `theme` | string | UI theme: `dark` or `light` |
| `keyword_store_path` | string | Path to keyword scan results file |
| `default_scan_paths` | array | Default paths to scan on all instances |
| `scan_rules` | array | Conditional scan rules (see below) |
| `connection_profiles` | array | SSH connection profiles (see below) |
| `connection_rules` | array | Rules for applying profiles to instances (see below) |

#### Scan Rules

Scan rules define what paths and commands to execute when scanning servers. Rules match instances based on attributes (name, region, tags) and execute scans only on matching servers.

**Example scan rule:**

```json
{
  "scan_rules": [
    {
      "name": "Web server logs",
      "match_conditions": {
        "name_contains": "web",
        "region": "us-east-1"
      },
      "scan_paths": [
        "/var/log/nginx/access.log",
        "/var/log/nginx/error.log"
      ],
      "scan_commands": [
        "grep -r 'ERROR' /var/www/html/logs/"
      ]
    }
  ]
}
```

**Match conditions:**
- `name_contains` — Instance name contains substring (case-insensitive)
- `region` — Exact region match (e.g., `us-east-1`)
- `state` — Instance state (e.g., `running`, `stopped`)

Scan results are stored in the keyword store and searchable via the TUI.

#### Connection Profiles

Connection profiles define how to connect to instances, including bastion/jump host configuration.

**Example with bastion host:**

```json
{
  "connection_profiles": [
    {
      "name": "private-vpc-bastion",
      "bastion_host": "bastion.example.com",
      "bastion_user": "ubuntu",
      "bastion_key": "/home/user/.ssh/bastion-key.pem",
      "ssh_port": 22
    }
  ],
  "connection_rules": [
    {
      "name": "Private instances via bastion",
      "match_conditions": {
        "name_contains": "private",
        "region": "us-west-2"
      },
      "profile_name": "private-vpc-bastion"
    }
  ]
}
```

This configuration automatically uses the bastion host when connecting to any instance matching the rule (e.g., name contains "private" in `us-west-2`). When a bastion profile matches, the target host switches to the instance's **private IP** automatically.

**How proxy works internally:**
- If `bastion_key` is set → uses `ProxyCommand` with `-i` flag (allows separate key for bastion)
- If no `bastion_key` → uses simpler `ProxyJump` (`-J` flag)
- If `proxy_command` is set → uses the raw ProxyCommand as-is (advanced)

**Connection profile fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Profile identifier |
| `bastion_host` | string | Bastion hostname or IP |
| `bastion_user` | string | Username for bastion connection (default: `ec2-user`) |
| `bastion_key` | string | SSH key for bastion authentication (optional — if omitted, uses same key as target) |
| `proxy_command` | string | Custom ProxyCommand for advanced scenarios (optional — overrides bastion settings) |
| `ssh_port` | int | SSH port for bastion (default: 22) |

**Connection rule fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Rule description |
| `match_conditions` | object | Conditions to match instances (same as scan rules) |
| `profile_name` | string | Name of ConnectionProfile to apply |

Rules are evaluated in order — the first matching rule wins.

## Development

For development without installing via `pipx`:

```bash
# Clone and navigate to project
git clone https://github.com/zb-ss/ec2-ssh.git
cd ec2-ssh

# Install dependencies (or use venv)
pip install -e ".[dev]"

# Run directly
PYTHONPATH=src python3 -m ec2_ssh.main
```

Or run the main script:

```bash
python src/ec2_ssh/main.py
```

To update an existing `pipx` installation after changes:

```bash
pipx install . --force
```

## Architecture

EC2 Connect v2.0 uses a modular architecture built on Textual TUI framework:

**Packages:**

- `config/` — Configuration management (JSON schema, migration, loading)
- `services/` — Business logic services with interfaces (AWS, SSH, SCP, scanning, caching, terminal)
- `screens/` — Textual screens (main menu, instance list, search, settings, file browser, etc.)
- `widgets/` — Reusable UI components (instance table, remote tree, status bar, progress)
- `utils/` — Utilities (formatting, platform detection, SSH helpers)

**Key patterns:**

- All services implement abstract interfaces (`services/interfaces.py`)
- Screens access services via `self.app.<service>` (dependency injection)
- Configuration is dataclass-based with schema versioning and migration support
- SSH uses ProxyJump (`-J`) for bastion hosts and `IdentitiesOnly=yes` (only when a key is specified) to prevent "Too many authentication failures"

## Instance Caching

EC2 Connect uses a **stale-while-revalidate** caching strategy for fast startup:

| Scenario | Behavior |
|----------|----------|
| **First launch** (no cache) | Fetches from AWS with progress indicator |
| **Restart within TTL** (cache fresh) | Instant load from cache — no AWS call |
| **Restart after TTL** (cache stale) | Shows stale data immediately, refreshes from AWS in the background |
| **Manual refresh** (`R` key) | Force-fetches from AWS with progress indicator |

When a background refresh completes, a notification shows the result:
- *"Refreshed: 12 instances (2 more)"* — new servers appeared
- *"Refreshed: 10 instances (1 fewer)"* — one was terminated
- *"Refreshed: 11 instances (up to date)"* — no changes

**Default TTL is 1 hour** (`cache_ttl_seconds: 3600`). Cache is stored at `~/.ec2_ssh_cache.json`.

## Logging & Debugging

Logs are always written to `~/.ec2_ssh_logs/ec2_ssh.log`. This includes SSH commands, terminal detection, connection profile resolution, and cache status.

For verbose output on stderr (useful for debugging):

```bash
ec2-ssh --debug
```

When SSH fails, the terminal window **stays open** showing the error message and exit code — press Enter to close it.

## Troubleshooting

### AWS Credentials

Ensure your AWS credentials are correctly configured:

```bash
aws configure
aws sts get-caller-identity
```

Verify permissions for `ec2:DescribeInstances` and `ec2:DescribeRegions`.

### SSH Connection Fails (window closes immediately)

Check the terminal window — it now stays open on failure showing the SSH error. Common causes:

1. **Wrong key**: Check `instance_keys` in config, or set `default_key`
2. **Wrong username**: Default is `ec2-user`; Ubuntu uses `ubuntu`, Amazon Linux uses `ec2-user`
3. **No key configured**: If no key is set and no agent key matches, SSH falls back to password auth (which EC2 doesn't support)
4. **Security group**: Ensure port 22 is open from your IP

Check the log for the exact SSH command: `cat ~/.ec2_ssh_logs/ec2_ssh.log | grep "SSH command"`

### Bastion Connection Hangs

If the terminal opens but SSH hangs:

1. **No connection profile configured**: Check that `connection_profiles` and `connection_rules` are set in `~/.ec2_ssh_config.json`
2. **Wrong bastion host**: Verify the bastion is reachable: `ssh -i key.pem user@bastion-host`
3. **Wrong bastion key**: If the bastion uses a different key, set `bastion_key` in the profile
4. **Private IP unreachable**: The bastion must be able to reach the target's private IP

### SSH Agent Not Running

If you see "Could not open a connection to your authentication agent":

```bash
eval $(ssh-agent -s)
ssh-add ~/.ssh/your-key.pem
```

### Key Permissions

SSH keys require strict permissions (600 or 400). The tool will warn you and offer to fix permissions automatically.

```bash
chmod 600 ~/.ssh/your-key.pem
```

### Too Many Authentication Failures

The tool automatically uses `IdentitiesOnly=yes` when specifying a key with `-i`, which prevents this error. If you still encounter it, check your SSH agent and remove unwanted keys:

```bash
ssh-add -D  # Remove all keys from agent
```

### Automatic Key Discovery

Auto-discovery searches `~/.ssh/` directory using multiple patterns:
- Exact match on AWS key name
- Key name with `.pem` extension
- Keys matching `id_rsa_*`, `aws_*`, etc.
- Fuzzy matching on filename stems

If keys are stored elsewhere, provide the full path manually.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
