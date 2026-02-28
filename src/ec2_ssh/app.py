"""Main Textual application for EC2 Connect v2.0."""

from __future__ import annotations
from typing import Optional, List

from textual.app import App
from textual.binding import Binding


class EC2ConnectApp(App):
    """EC2 Connect TUI application."""

    CSS_PATH = "app.css"
    TITLE = "EC2 Connect"
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("question_mark", "show_help", "Help", show=True),
    ]

    # Service instances - created in on_mount
    config_manager = None
    aws_service = None
    cache_service = None
    ssh_service = None
    connection_service = None
    scan_service = None
    keyword_store = None
    terminal_service = None
    scp_service = None

    # Shared state
    instances: List[dict] = []  # all fetched instances

    def on_mount(self) -> None:
        """Initialize services and push main menu."""
        from ec2_ssh.screens.main_menu import MainMenuScreen

        self._init_services()
        self.push_screen(MainMenuScreen())

    def _init_services(self) -> None:
        """Create all service instances."""
        from ec2_ssh.config.manager import ConfigManager
        from ec2_ssh.services.cache_service import CacheService
        from ec2_ssh.services.aws_service import AWSService
        from ec2_ssh.services.ssh_service import SSHService
        from ec2_ssh.services.connection_service import ConnectionService
        from ec2_ssh.services.scan_service import ScanService
        from ec2_ssh.services.keyword_store import KeywordStore
        from ec2_ssh.services.terminal_service import TerminalService
        from ec2_ssh.services.scp_service import SCPService

        self.config_manager = ConfigManager()
        config = self.config_manager.get()
        self.cache_service = CacheService(ttl_seconds=config.cache_ttl_seconds)
        self.aws_service = AWSService(self.cache_service)
        self.ssh_service = SSHService(self.config_manager)
        self.connection_service = ConnectionService(self.config_manager)
        self.scan_service = ScanService(self.config_manager)
        self.keyword_store = KeywordStore(config.keyword_store_path)
        self.terminal_service = TerminalService(preferred=config.terminal_emulator)
        self.scp_service = SCPService()

    def action_show_help(self) -> None:
        """Show help screen from any context."""
        from ec2_ssh.screens.help import HelpScreen
        self.push_screen(HelpScreen())

