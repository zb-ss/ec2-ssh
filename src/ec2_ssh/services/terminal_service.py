"""Terminal service for detecting and launching terminal emulators."""

from __future__ import annotations
import logging
import subprocess
import shutil
import shlex
from typing import List, Optional, Tuple

from ec2_ssh.services.interfaces import TerminalServiceInterface
from ec2_ssh.utils.platform_utils import get_os

logger = logging.getLogger(__name__)


class TerminalService(TerminalServiceInterface):
    """Terminal service for cross-platform terminal detection and SSH launching.

    Supports Linux, macOS, and Windows terminal emulators.
    """

    # Detection order per platform (name, command_template)
    LINUX_TERMINALS: List[Tuple[str, List[str]]] = [
        ("gnome-terminal", ["gnome-terminal", "--", "{ssh_cmd}"]),
        ("konsole", ["konsole", "-e", "{ssh_cmd}"]),
        ("xfce4-terminal", ["xfce4-terminal", "-e", "{ssh_cmd}"]),
        ("alacritty", ["alacritty", "-e", "{ssh_cmd}"]),
        ("xterm", ["xterm", "-e", "{ssh_cmd}"]),
    ]

    MACOS_TERMINALS: List[Tuple[str, str]] = [
        ("Terminal.app", "open -a Terminal"),
        ("iTerm.app", "open -a iTerm"),
    ]

    WINDOWS_TERMINALS: List[Tuple[str, List[str]]] = [
        ("wt.exe", ["wt.exe", "{ssh_cmd}"]),
        ("cmd.exe", ["cmd.exe", "/c", "start", "ssh", "{ssh_cmd}"]),
    ]

    def __init__(self, preferred: str = "auto") -> None:
        """Initialize terminal service.

        Args:
            preferred: Preferred terminal name, or "auto" for auto-detection.
        """
        self._preferred = preferred
        self._detected: Optional[str] = None

    def detect_terminal(self) -> str:
        """Detect available terminal emulator.

        Checks for preferred terminal first, then searches by platform.

        Returns:
            Terminal command name (e.g., 'gnome-terminal', 'Terminal.app', 'wt.exe'),
            or 'none' if no terminal found.
        """
        # Check preferred terminal if specified
        if self._preferred != "auto":
            if shutil.which(self._preferred):
                self._detected = self._preferred
                logger.info("Using preferred terminal: %s", self._preferred)
                return self._preferred
            else:
                logger.warning("Preferred terminal '%s' not found", self._preferred)

        os_name = get_os()

        # Get terminal list for current OS
        if os_name == 'linux':
            terminals = self.LINUX_TERMINALS
        elif os_name == 'darwin':
            terminals = self.MACOS_TERMINALS
        elif os_name == 'windows':
            terminals = self.WINDOWS_TERMINALS
        else:
            logger.warning("Unknown OS: %s, using Linux terminals", os_name)
            terminals = self.LINUX_TERMINALS

        # Search for available terminal
        for name, _ in terminals:
            if os_name == 'darwin':
                # macOS apps are in /Applications, assume available
                # User can override if needed
                self._detected = name
                logger.info("Detected macOS terminal: %s", name)
                return name
            else:
                # Linux/Windows: check PATH
                if shutil.which(name):
                    self._detected = name
                    logger.info("Detected terminal: %s", name)
                    return name

        logger.error("No terminal emulator detected")
        return 'none'

    def launch_ssh_in_terminal(self, ssh_command: List[str]) -> bool:
        """Launch SSH session in a new terminal window.

        Args:
            ssh_command: SSH command list from SSHServiceInterface.

        Returns:
            True if terminal launched successfully.
        """
        terminal = self._detected or self.detect_terminal()

        if terminal == 'none':
            logger.error("No terminal emulator available for launching SSH")
            return False

        os_name = get_os()
        ssh_cmd_str = shlex.join(ssh_command)

        try:
            if os_name == 'darwin':
                # macOS: use osascript to open Terminal with command
                return self._launch_macos_terminal(terminal, ssh_cmd_str)
            elif os_name == 'linux':
                # Linux: use terminal-specific command
                return self._launch_linux_terminal(terminal, ssh_command)
            elif os_name == 'windows':
                # Windows: use Windows terminal or cmd
                return self._launch_windows_terminal(terminal, ssh_command)
            else:
                logger.error("Unsupported OS: %s", os_name)
                return False

        except Exception as e:
            logger.error("Failed to launch terminal: %s", e)
            return False

    def _launch_macos_terminal(self, terminal: str, ssh_cmd_str: str) -> bool:
        """Launch SSH in macOS terminal using osascript.

        Args:
            terminal: Terminal app name.
            ssh_cmd_str: SSH command as string.

        Returns:
            True if launched successfully.
        """
        # Escape shell metacharacters for AppleScript context
        escaped_cmd = ssh_cmd_str.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')

        if 'Terminal.app' in terminal:
            script = f'tell application "Terminal" to do script "{escaped_cmd}"'
        elif 'iTerm.app' in terminal:
            script = f'tell application "iTerm" to create window with default profile command "{escaped_cmd}"'
        else:
            # Fallback to Terminal.app
            script = f'tell application "Terminal" to do script "{escaped_cmd}"'

        subprocess.Popen(['osascript', '-e', script])
        logger.info("Launched SSH in macOS terminal: %s", terminal)
        return True

    def _launch_linux_terminal(self, terminal: str, ssh_command: List[str]) -> bool:
        """Launch SSH in Linux terminal.

        Args:
            terminal: Terminal command name.
            ssh_command: SSH command as list.

        Returns:
            True if launched successfully.
        """
        # Find terminal config
        for name, cmd_template in self.LINUX_TERMINALS:
            if name == terminal:
                # Build command based on terminal type
                if name == 'gnome-terminal':
                    # gnome-terminal uses -- to separate args
                    cmd = ['gnome-terminal', '--'] + ssh_command
                elif name in ['konsole', 'xfce4-terminal', 'alacritty', 'xterm']:
                    # These terminals use -e flag
                    cmd = [name, '-e'] + ssh_command
                else:
                    logger.error("Unknown Linux terminal: %s", name)
                    return False

                subprocess.Popen(cmd)
                logger.info("Launched SSH in Linux terminal: %s", terminal)
                return True

        logger.error("Could not build launch command for terminal: %s", terminal)
        return False

    def _launch_windows_terminal(self, terminal: str, ssh_command: List[str]) -> bool:
        """Launch SSH in Windows terminal.

        Args:
            terminal: Terminal executable name.
            ssh_command: SSH command as list.

        Returns:
            True if launched successfully.
        """
        ssh_cmd_str = shlex.join(ssh_command)

        # Find terminal config
        for name, cmd_template in self.WINDOWS_TERMINALS:
            if name == terminal:
                # Build command - replace {ssh_cmd} placeholder
                cmd = []
                for part in cmd_template:
                    if '{ssh_cmd}' in part:
                        cmd.append(ssh_cmd_str)
                    else:
                        cmd.append(part)

                subprocess.Popen(cmd)
                logger.info("Launched SSH in Windows terminal: %s", terminal)
                return True

        logger.error("Could not build launch command for terminal: %s", terminal)
        return False
