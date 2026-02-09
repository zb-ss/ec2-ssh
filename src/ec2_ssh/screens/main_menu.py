"""Main menu screen for EC2 Connect v2.0."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Static, Button, Header, Footer


class MainMenuScreen(Screen):
    """Main menu screen with option selection."""

    BINDINGS = [
        Binding("1", "option_1", "List Instances", show=True),
        Binding("2", "option_2", "Search", show=True),
        Binding("3", "option_3", "SSH Keys", show=True),
        Binding("4", "option_4", "Scan Servers", show=True),
        Binding("5", "option_5", "Settings", show=True),
        Binding("6", "quit", "Quit", show=True),
        Binding("l", "option_1", "List", show=False),
        Binding("s", "option_2", "Search", show=False),
        Binding("k", "option_3", "Keys", show=False),
        Binding("c", "option_4", "Scan", show=False),
        Binding("t", "option_5", "Settings", show=False),
        Binding("q", "quit", "Quit", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Compose the main menu UI."""
        yield Header()
        yield Container(
            Static(
                "[bold cyan]EC2 Connect v2.0[/bold cyan]\n\n"
                "[dim]AWS EC2 Instance Manager with SSH[/dim]",
                id="banner"
            ),
            Vertical(
                Button("1. List Instances", id="btn_list", variant="primary"),
                Button("2. Search", id="btn_search"),
                Button("3. Manage SSH Keys", id="btn_keys"),
                Button("4. Scan Servers", id="btn_scan"),
                Button("5. Settings", id="btn_settings"),
                Button("6. Quit", id="btn_quit", variant="error"),
                id="menu_buttons"
            ),
            id="menu_container"
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button pressed event.
        """
        button_id = event.button.id

        if button_id == "btn_list":
            self.action_option_1()
        elif button_id == "btn_search":
            self.action_option_2()
        elif button_id == "btn_keys":
            self.action_option_3()
        elif button_id == "btn_scan":
            self.action_option_4()
        elif button_id == "btn_settings":
            self.action_option_5()
        elif button_id == "btn_quit":
            self.action_quit()

    def action_option_1(self) -> None:
        """Navigate to List Instances screen."""
        from ec2_ssh.screens.instance_list import InstanceListScreen
        self.app.push_screen(InstanceListScreen())

    def action_option_2(self) -> None:
        """Navigate to Search screen."""
        from ec2_ssh.screens.search import SearchScreen
        self.app.push_screen(SearchScreen())

    def action_option_3(self) -> None:
        """Navigate to SSH Keys management."""
        from ec2_ssh.screens.key_management import KeyManagementScreen
        self.app.push_screen(KeyManagementScreen())

    def action_option_4(self) -> None:
        """Scan Servers — scan all running instances."""
        self.notify("Starting server scan...")
        self.run_worker(self._scan_all_servers(), name="scan_all", exclusive=True)

    async def _scan_all_servers(self) -> None:
        """Worker function to scan all running instances."""
        instances = self.app.instances
        running = [i for i in instances if i.get('state') == 'running']
        if not running:
            self.app.notify("No running instances to scan", severity="warning")
            return

        scanned = 0
        for instance in running:
            try:
                results = await self.app.scan_service.scan_server(
                    instance, self.app.ssh_service, self.app.connection_service
                )
                if results:
                    self.app.keyword_store.save_results(instance['id'], results)
                    scanned += 1
            except Exception as e:
                self.app.notify(f"Scan failed for {instance.get('name', instance['id'])}: {e}",
                               severity="error")

        self.app.notify(f"Scan complete. {scanned}/{len(running)} servers scanned.")

    def action_option_5(self) -> None:
        """Navigate to Settings."""
        from ec2_ssh.screens.settings import SettingsScreen
        self.app.push_screen(SettingsScreen())

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
