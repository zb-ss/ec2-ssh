"""Utilities package for EC2 Connect v2.0."""

from __future__ import annotations

from ec2_ssh.utils.formatting import (
    format_timedelta,
    truncate_string,
    format_file_size,
)
from ec2_ssh.utils.platform_utils import (
    get_os,
    command_exists,
    get_home_dir,
    get_ssh_dir,
)

__all__ = [
    'format_timedelta',
    'truncate_string',
    'format_file_size',
    'get_os',
    'command_exists',
    'get_home_dir',
    'get_ssh_dir',
]
