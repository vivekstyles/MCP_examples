"""
Multi-Server MCP Client Aggregator.
Connects to multiple independent MCP servers concurrently and aggregates
their tools, resources, and prompts under a single unified agent interface.
"""
from __future__ import annotations
import sys
from contextlib import AsyncExitStack
from typing import Any, Optional
from core.client import MCPClient
from core.tool_registry import MCPToolRegistry
from rich.console import Console
from rich.table import Table

console = Console()


class MultiServerMCPClient:
    """
    Connects to multiple MCP servers simultaneously.
    Registers all discovered tools into a central registry with optional namespacing.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._servers: dict[str, MCPClient] = {}
        self.registry = MCPToolRegistry()
        self._exit_stack = AsyncExitStack()

    def add_server(
        self,
        server_id: str,
        script_path: str,
        python_exe: str = sys.executable,
        env: Optional[dict[str, str]] = None,
    ):
        """Register a server definition to be started upon connection."""
        client = MCPClient(
            name=server_id,
            command=python_exe,
            args=[script_path],
            env=env,
            verbose=self.verbose,
        )
        self._servers[server_id] = client

    async def __aenter__(self) -> MultiServerMCPClient:
        await self.connect_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_all()

    async def connect_all(self):
        """Start all registered servers and aggregate their tools."""
        if self.verbose:
            console.print(f"[bold blue]Starting {len(self._servers)} MCP Servers concurrently...[/bold blue]")

        for server_id, client in self._servers.items():
            await self._exit_stack.enter_async_context(client)
            tools = await client.list_tools()
            for t in tools:
                # Register with namespace prefix, e.g., 'math__add'
                self.registry.register_tool(t, server_name=server_id, prefix_namespace=True)

        if self.verbose:
            self._render_tools_table()

    def _render_tools_table(self):
        """Render a summary table of all aggregated tools."""
        table = Table(title="Aggregated MCP Tool Ecosystem", show_header=True, header_style="bold magenta")
        table.add_column("Namespace / Tool", style="cyan")
        table.add_column("Server", style="yellow")
        table.add_column("Description", style="white")

        for name in self.registry.all_names:
            tool = self.registry.get_tool(name)
            server = self.registry.get_server_for_tool(name)
            desc = (tool.description or "").split("\n")[0][:60]
            table.add_row(name, server, desc)

        console.print(table)

    async def call_tool(self, tool_call_name: str, arguments: dict[str, Any]) -> Any:
        """
        Dispatches a tool call to the originating server based on the namespace.
        Example: 'math__add' -> calls 'add' on server 'math'.
        """
        server_name = self.registry.get_server_for_tool(tool_call_name)
        if not server_name or server_name not in self._servers:
            raise ValueError(f"Unknown or unrouted tool: '{tool_call_name}'")

        target_client = self._servers[server_name]
        # Strip the namespace prefix when passing to the actual server
        raw_tool_name = tool_call_name.split("__", 1)[-1]
        return await target_client.call_tool(raw_tool_name, arguments)

    async def close_all(self):
        """Gracefully close all server sessions."""
        await self._exit_stack.aclose()
        if self.verbose:
            console.print("[dim]All MCP servers shut down successfully.[/dim]")
