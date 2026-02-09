#!/usr/bin/env python3
"""EC2 Connect — Interactive TUI for managing AWS EC2 SSH connections."""
from __future__ import annotations

import argparse

def main() -> None:
    """Entry point for ec2-ssh command."""
    parser = argparse.ArgumentParser(
        description='EC2 Connect — Interactive TUI for managing AWS EC2 SSH connections'
    )
    parser.add_argument('--version', action='version', version='ec2-ssh 2.0.0')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to config file (default: ~/.ec2_ssh_config.json)')
    parser.parse_args()

    from ec2_ssh.app import EC2ConnectApp
    app = EC2ConnectApp()
    app.run()

if __name__ == '__main__':
    main()
