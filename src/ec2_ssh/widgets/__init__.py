"""Widgets package for EC2 Connect v2.0 TUI."""

from __future__ import annotations

from ec2_ssh.widgets.instance_table import InstanceTable
from ec2_ssh.widgets.status_bar import StatusBar
from ec2_ssh.widgets.progress_indicator import ProgressIndicator
from ec2_ssh.widgets.remote_tree import RemoteTree
from ec2_ssh.widgets.command_output import CommandOutput

__all__ = [
    'InstanceTable',
    'StatusBar',
    'ProgressIndicator',
    'RemoteTree',
    'CommandOutput',
]
