"""Command overlay modal for EC2 Connect v2.0."""

from __future__ import annotations
import subprocess
import logging
from typing import List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from ec2_ssh.widgets.command_output import CommandOutput

logger = logging.getLogger(__name__)


class CommandOverlay(ModalScreen):
    """Modal screen for executing SSH commands on a remote server.

    Displays a command output log at top and an input field at bottom.
    Commands are executed via SSH and output is displayed in real-time.
    Maintains command history for navigation with up/down arrows.
    """

    BINDINGS = [
        Binding("escape", "close_overlay", "Close", show=True),
        Binding("ctrl+c", "close_overlay", "Close", show=False),
        Binding("up", "history_prev", "Previous", show=False),
        Binding("down", "history_next", "Next", show=False),
    ]

    def __init__(self, instance: dict) -> None:
        """Initialize command overlay.

        Args:
            instance: Instance dictionary with connection details.
        """
        super().__init__()
        self._instance = instance
        self._history: List[str] = []
        self._history_index = -1

        # Resolve connection details
        self._profile = None
        self._host = None
        self._proxy_jump = None
        self._username = None
        self._key_path = None

    def compose(self) -> ComposeResult:
        """Compose the command overlay UI."""
        yield Container(
            Static(self._build_header_text(), id="command_header"),
            CommandOutput(id="command_output"),
            Input(
                placeholder="Enter command to execute...",
                id="command_input"
            ),
            id="command_overlay_container"
        )

    def on_mount(self) -> None:
        """Initialize connection details and focus input on mount."""
        # Resolve connection details
        self._profile = self.app.connection_service.resolve_profile(self._instance)
        self._host = self.app.connection_service.get_target_host(
            self._instance,
            self._profile
        )
        if self._profile:
            self._proxy_jump = self.app.connection_service.get_proxy_jump_string(
                self._profile
            )

        config = self.app.config_manager.get()
        self._username = config.default_username
        self._key_path = self.app.ssh_service.get_key_path(self._instance['id'])

        # Show welcome message
        output = self.query_one("#command_output", CommandOutput)
        output.append_output(
            f"[dim]Connected to {self._instance.get('name') or self._instance.get('id')}[/dim]"
        )
        output.append_output(
            f"[dim]Type commands below. Press Escape or Ctrl+C to close.[/dim]\n"
        )

        # Focus input
        self.query_one("#command_input", Input).focus()

    def _build_header_text(self) -> str:
        """Build header text with server name and prompt.

        Returns:
            Rich-formatted header string.
        """
        name = self._instance.get('name') or self._instance.get('id', 'unknown')
        return f"[bold cyan]Command Execution:[/bold cyan] {name}"

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command input submission.

        Args:
            event: Input submitted event.
        """
        if event.input.id != "command_input":
            return

        command = event.value.strip()
        if not command:
            return

        # Clear input
        event.input.value = ""

        # Add to history
        if command not in self._history or self._history[-1] != command:
            self._history.append(command)
        self._history_index = len(self._history)

        # Execute command
        self._execute_command(command)

    def _execute_command(self, command: str) -> None:
        """Execute a command on the remote server via SSH.

        Args:
            command: Command string to execute.
        """
        output_widget = self.query_one("#command_output", CommandOutput)

        # Show command in output
        prompt = f"{self._username}@{self._instance.get('name', 'server')}:~"
        output_widget.append_command(f"{prompt}$ {command}")

        # Build SSH command
        ssh_cmd = self.app.ssh_service.build_ssh_command(
            host=self._host,
            username=self._username,
            key_path=self._key_path,
            proxy_jump=self._proxy_jump,
            remote_command=command
        )

        logger.debug("Executing SSH command: %s", ' '.join(ssh_cmd))

        # Run in worker to avoid blocking UI
        self.run_worker(
            self._run_ssh_command(ssh_cmd, output_widget),
            name=f"exec_{len(self._history)}",
            exclusive=False
        )

    async def _run_ssh_command(
        self,
        ssh_cmd: List[str],
        output_widget: CommandOutput
    ) -> None:
        """Run SSH command in subprocess and display output.

        Args:
            ssh_cmd: SSH command list from build_ssh_command.
            output_widget: CommandOutput widget to write results to.
        """
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Display output
            if result.stdout:
                output_widget.append_output(result.stdout)

            # Display errors
            if result.stderr:
                output_widget.append_error(result.stderr)

            # Show return code if non-zero
            if result.returncode != 0:
                output_widget.append_error(
                    f"[dim]Command exited with code {result.returncode}[/dim]"
                )

        except subprocess.TimeoutExpired:
            output_widget.append_error("❌ Command timed out (30s limit)")
            logger.warning("SSH command timed out")
            self.app.notify("Command timed out after 30 seconds", severity="error")

        except Exception as e:
            error_str = str(e)
            if "Connection refused" in error_str:
                output_widget.append_error("❌ Connection refused. Check if instance is accessible.")
                self.app.notify("SSH connection refused", severity="error")
            elif "timed out" in error_str.lower():
                output_widget.append_error("❌ Connection timed out. Check network and security groups.")
                self.app.notify("SSH connection timed out", severity="error")
            elif "permission denied" in error_str.lower():
                output_widget.append_error("❌ Permission denied. Check SSH key and username.")
                self.app.notify("SSH authentication failed", severity="error")
            else:
                output_widget.append_error(f"❌ Error: {error_str}")
                self.app.notify(f"SSH error: {error_str}", severity="error")
            logger.error("SSH command failed: %s", e)

        # Add separator
        output_widget.append_output("")

    def action_close_overlay(self) -> None:
        """Close the command overlay modal."""
        self.app.pop_screen()

    def action_history_prev(self) -> None:
        """Navigate to previous command in history."""
        if not self._history:
            return

        if self._history_index > 0:
            self._history_index -= 1
            command_input = self.query_one("#command_input", Input)
            command_input.value = self._history[self._history_index]
            command_input.cursor_position = len(command_input.value)

    def action_history_next(self) -> None:
        """Navigate to next command in history."""
        if not self._history:
            return

        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            command_input = self.query_one("#command_input", Input)
            command_input.value = self._history[self._history_index]
            command_input.cursor_position = len(command_input.value)
        else:
            # Clear input if at end of history
            self._history_index = len(self._history)
            command_input = self.query_one("#command_input", Input)
            command_input.value = ""
