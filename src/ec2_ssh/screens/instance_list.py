"""Instance list screen for EC2 Connect v2.0."""

from __future__ import annotations
from typing import Optional, List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Header, Footer, Input
from textual.worker import Worker

from ec2_ssh.widgets.instance_table import InstanceTable
from ec2_ssh.widgets.status_bar import StatusBar
from ec2_ssh.widgets.progress_indicator import ProgressIndicator


class InstanceListScreen(Screen):
    """Screen displaying list of EC2 instances with search/filter."""

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("/", "focus_search", "Search", show=True),
        Binding("enter", "select_instance", "Select", show=True),
        Binding("s", "ssh_connect", "SSH", show=True),
        Binding("b", "browse_files", "Browse", show=True),
        Binding("c", "run_command", "Command", show=True),
        Binding("t", "scp_transfer", "Transfer", show=True),
    ]

    def __init__(self) -> None:
        """Initialize instance list screen."""
        super().__init__()
        self._instances: List[dict] = []

    def compose(self) -> ComposeResult:
        """Compose the instance list UI."""
        yield Header()
        yield Container(
            Input(placeholder="Search instances...", id="search_input"),
            ProgressIndicator(),
            InstanceTable(),
            StatusBar(),
            id="instance_list_container"
        )
        yield Footer()

    def on_mount(self) -> None:
        """Load instances when screen is mounted."""
        self._fetch_instances()

    def _fetch_instances(self, force_refresh: bool = False) -> None:
        """Fetch instances from AWS via worker.

        Args:
            force_refresh: If True, bypass cache.
        """
        progress = self.query_one(ProgressIndicator)
        progress.start("Loading instances...")

        # Run async fetch in worker
        self.run_worker(
            self.app.aws_service.fetch_instances_cached(force_refresh=force_refresh),
            name="fetch_instances",
            exclusive=True
        )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes.

        Args:
            event: Worker state changed event.
        """
        if event.worker.name == "fetch_instances":
            if event.worker.is_finished:
                progress = self.query_one(ProgressIndicator)
                progress.stop()

                if event.worker.error:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error("Failed to fetch instances: %s", event.worker.error)

                    error_msg = str(event.worker.error)
                    if "NoCredentialsError" in error_msg or "credentials" in error_msg.lower():
                        self.app.notify(
                            "AWS credentials not found. Please configure AWS credentials.",
                            severity="error"
                        )
                    elif "EndpointConnectionError" in error_msg or "timed out" in error_msg.lower():
                        self.app.notify(
                            "Network error: Unable to connect to AWS. Check your connection.",
                            severity="error"
                        )
                    elif "AccessDenied" in error_msg or "UnauthorizedOperation" in error_msg:
                        self.app.notify(
                            "Access denied: Check your AWS IAM permissions for EC2.",
                            severity="error"
                        )
                    else:
                        self.app.notify(
                            f"Error loading instances: {error_msg}",
                            severity="error"
                        )
                    self._instances = []
                else:
                    self._instances = event.worker.result or []
                    self.app.instances = self._instances

                    if not self._instances:
                        self.app.notify(
                            "No EC2 instances found in any region.",
                            severity="information"
                        )

                self._update_table()
                self._update_status_bar()

    def _update_table(self) -> None:
        """Update instance table with current data."""
        table = self.query_one(InstanceTable)
        table.populate(self._instances)

    def _update_status_bar(self) -> None:
        """Update status bar with current counts and cache age."""
        status_bar = self.query_one(StatusBar)
        table = self.query_one(InstanceTable)

        # Update counts
        total = len(self._instances)
        filtered = len(table._filtered_instances)
        status_bar.update_instance_count(total, filtered)

        # Update cache age
        cache_age = self.app.cache_service.get_age()
        status_bar.update_cache_age(cache_age)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes.

        Args:
            event: Input changed event.
        """
        if event.input.id == "search_input":
            table = self.query_one(InstanceTable)
            table.filter(event.value)
            self._update_status_bar()

    def action_back(self) -> None:
        """Navigate back to main menu."""
        self.app.pop_screen()

    def action_refresh(self) -> None:
        """Refresh instance list from AWS."""
        self._fetch_instances(force_refresh=True)
        self.app.notify("Refreshing instances...", severity="information")

    def action_focus_search(self) -> None:
        """Focus the search input."""
        search_input = self.query_one("#search_input", Input)
        search_input.focus()

    def action_select_instance(self) -> None:
        """Handle instance selection."""
        from ec2_ssh.screens.server_actions import ServerActionsScreen

        table = self.query_one(InstanceTable)
        instance = table.get_selected_instance()

        if instance:
            self.app.push_screen(ServerActionsScreen(instance))
        else:
            self.app.notify("No instance selected", severity="warning")

    def _get_selected_running_instance(self) -> Optional[dict]:
        """Get the selected instance, validate it's running.

        Returns:
            Instance dict if valid, None otherwise.
        """
        table = self.query_one(InstanceTable)
        instance = table.get_selected_instance()

        if not instance:
            self.app.notify("No instance selected", severity="warning")
            return None

        if instance.get('state') != 'running':
            self.app.notify(
                f"Instance is {instance.get('state')}. Only running instances can connect.",
                severity="warning"
            )
            return None

        return instance

    def action_ssh_connect(self) -> None:
        """Quick SSH connect to selected instance."""
        instance = self._get_selected_running_instance()
        if not instance:
            return

        try:
            profile = self.app.connection_service.resolve_profile(instance)
            host = self.app.connection_service.get_target_host(instance, profile)
            proxy_args = []
            if profile:
                proxy_args = self.app.connection_service.get_proxy_args(profile)
            username = self.app.config_manager.get().default_username
            key_path = self.app.ssh_service.get_key_path(instance['id'])

            if not key_path and instance.get('key_name'):
                key_path = self.app.ssh_service.discover_key(instance['key_name'])

            ssh_cmd = self.app.ssh_service.build_ssh_command(host, username, key_path, proxy_args=proxy_args)

            if self.app.terminal_service.launch_ssh_in_terminal(ssh_cmd):
                self.app.notify(f"SSH session launched for {instance.get('name', 'instance')}")
            else:
                self.app.notify("No terminal emulator detected. Set 'terminal_emulator' in settings.", severity="error")
        except Exception as e:
            self.app.notify(f"SSH error: {e}", severity="error")

    def action_browse_files(self) -> None:
        """Open file browser for selected instance."""
        instance = self._get_selected_running_instance()
        if not instance:
            return
        from ec2_ssh.screens.file_browser import FileBrowserScreen
        self.app.push_screen(FileBrowserScreen(instance))

    def action_run_command(self) -> None:
        """Open command overlay for selected instance."""
        instance = self._get_selected_running_instance()
        if not instance:
            return
        from ec2_ssh.screens.command_overlay import CommandOverlay
        self.app.push_screen(CommandOverlay(instance))

    def action_scp_transfer(self) -> None:
        """Open SCP transfer for selected instance."""
        instance = self._get_selected_running_instance()
        if not instance:
            return
        from ec2_ssh.screens.scp_transfer import SCPTransferScreen
        self.app.push_screen(SCPTransferScreen(instance))
