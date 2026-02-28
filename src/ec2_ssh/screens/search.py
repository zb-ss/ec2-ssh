"""Search screen for EC2 Connect v2.0."""

from __future__ import annotations
from typing import List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Static, Label


class SearchScreen(Screen):
    """Screen for searching instances and keyword matches."""

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose the search UI."""
        yield Header()
        yield Container(
            Input(placeholder="Search instances and keywords...", id="search_input"),
            Vertical(
                Label("[bold]Instance Matches:[/bold]", id="instance_matches_label"),
                VerticalScroll(id="instance_matches_container"),
                Label("[bold]Keyword Matches:[/bold]", id="keyword_matches_label"),
                VerticalScroll(id="keyword_matches_container"),
                id="results_container"
            ),
            id="search_container"
        )
        yield Footer()

    def on_mount(self) -> None:
        """Focus search input when screen is mounted."""
        search_input = self.query_one("#search_input", Input)
        search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes.

        Args:
            event: Input changed event.
        """
        if event.input.id == "search_input":
            query = event.value.strip()
            if len(query) >= 2:  # Only search with 2+ characters
                self._perform_search(query)
            else:
                self._clear_results()

    def _perform_search(self, query: str) -> None:
        """Perform search across instances and keywords.

        Args:
            query: Search query string.
        """
        # Search instances
        instance_matches = self._search_instances(query)
        self._display_instance_matches(instance_matches)

        # Search keyword store
        keyword_matches = self._search_keywords(query)
        self._display_keyword_matches(keyword_matches)

    def _search_instances(self, query: str) -> List[dict]:
        """Search instances by name, ID, or type.

        Args:
            query: Search query string.

        Returns:
            List of matching instance dictionaries.
        """
        query_lower = query.lower()
        instances = self.app.instances

        matches = [
            inst for inst in instances
            if query_lower in inst.get('name', '').lower()
            or query_lower in inst.get('id', '').lower()
            or query_lower in inst.get('type', '').lower()
        ]

        return matches

    def _search_keywords(self, query: str) -> List[dict]:
        """Search keyword store for matches.

        Args:
            query: Search query string.

        Returns:
            List of keyword match dictionaries.
        """
        try:
            return self.app.keyword_store.search(query)
        except Exception as e:
            self.app.notify(f"Error searching keywords: {e}", severity="error")
            return []

    def _display_instance_matches(self, matches: List[dict]) -> None:
        """Display instance search results.

        Args:
            matches: List of matching instance dictionaries.
        """
        container = self.query_one("#instance_matches_container", VerticalScroll)
        container.remove_children()

        if not matches:
            container.mount(Static("[dim]No instance matches[/dim]"))
            return

        for instance in matches[:20]:  # Limit to 20 results
            name = instance.get('name', '(unnamed)')
            instance_id = instance.get('id', '')
            region = instance.get('region', '')
            state = instance.get('state', '')

            result_text = (
                f"[bold]{name}[/bold]\n"
                f"  ID: {instance_id} | Region: {region} | State: {state}\n"
            )
            container.mount(Static(result_text))

    def _display_keyword_matches(self, matches: List[dict]) -> None:
        """Display keyword search results.

        Args:
            matches: List of keyword match dictionaries.
        """
        container = self.query_one("#keyword_matches_container", VerticalScroll)
        container.remove_children()

        if not matches:
            container.mount(Static("[dim]No keyword matches[/dim]"))
            return

        for match in matches[:20]:  # Limit to 20 results
            server_id = match.get('server_id', '')
            source = match.get('source', '')
            content = match.get('content', '')

            # Truncate content if too long
            if len(content) > 200:
                content = content[:200] + "..."

            result_text = (
                f"[bold]Server: {server_id}[/bold]\n"
                f"  Source: {source}\n"
                f"  [dim]{content}[/dim]\n"
            )
            container.mount(Static(result_text))

    def _clear_results(self) -> None:
        """Clear all search results."""
        instance_container = self.query_one("#instance_matches_container", VerticalScroll)
        keyword_container = self.query_one("#keyword_matches_container", VerticalScroll)

        instance_container.remove_children()
        keyword_container.remove_children()

        instance_container.mount(Static("[dim]Enter 2+ characters to search[/dim]"))
        keyword_container.mount(Static("[dim]Enter 2+ characters to search[/dim]"))

    def action_back(self) -> None:
        """Navigate back to main menu."""
        self.app.pop_screen()
