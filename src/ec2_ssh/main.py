#!/usr/bin/env python3
"""EC2 Connect — Interactive TUI for managing AWS EC2 SSH connections."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path


def _setup_logging(debug: bool = False) -> Path:
    """Configure logging to file (and optionally stderr).

    Args:
        debug: If True, also log to stderr and use DEBUG level.

    Returns:
        Path to the log file.
    """
    log_dir = Path.home() / '.ec2-ssh' / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'ec2_ssh.log'

    level = logging.DEBUG if debug else logging.INFO
    fmt = '%(asctime)s %(levelname)-7s [%(name)s] %(message)s'

    handlers: list[logging.Handler] = [
        logging.FileHandler(log_file, encoding='utf-8'),
    ]
    if debug:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(level=level, format=fmt, handlers=handlers)

    # Quiet noisy libraries
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('textual').setLevel(logging.WARNING)

    logging.getLogger(__name__).info("EC2 Connect started — log: %s", log_file)
    return log_file


def main() -> None:
    """Entry point for ec2-ssh command."""
    parser = argparse.ArgumentParser(
        description='EC2 Connect — Interactive TUI for managing AWS EC2 SSH connections'
    )
    parser.add_argument('--version', action='version', version='ec2-ssh 2.0.0')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging (also prints to stderr)')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to config file (default: ~/.ec2-ssh/config.json)')
    args = parser.parse_args()

    log_file = _setup_logging(debug=args.debug)

    from ec2_ssh.app import EC2ConnectApp
    app = EC2ConnectApp()
    app.run()

if __name__ == '__main__':
    main()
