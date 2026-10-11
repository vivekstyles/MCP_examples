"""
MCP Client Wrapper with Protocol Transparency & JSON-RPC Telemetry.
Provides a clean async interface to connect to any MCP server over stdio.
"""
from __future__ import annotations
import sys
import json
from contextlib import AsyncExitStack
from typing import Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool, Resource, Prompt
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


class MCPClient:
    """
    Manages an MCP client session over stdio with an external server process.
    Provides methods for tool listing, execution, resource access, and prompt retrieval.
    """

    def __init__(
        self,
        name: str,
        command: str = sys.executable,
        args: Optional[list[str]] = None,
        env: Optional[dict[str, str]] = None,
        verbose: bool = True,
    ):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env
        self.verbose = verbose
        self._exit_stack = AsyncExitStack()
        self.session: Optional[ClientSession] = None
        self._tools_cache: list[Tool] = []

    def _log_rpc(self, direction: str, method: str, data: Any):
        """Format and log raw JSON-RPC protocol activity if verbose mode is on."""
        if not self.verbose:
            return

        arrow = "[bold cyan]--> REQUEST[/bold cyan]" if direction == "out" else "[bold green]<-- RESPONSE[/bold green]"
        json_str = json.dumps(data, indent=2, default=str)
        syntax = Syntax(json_str, "json", theme="monokai", word_wrap=True)
        console.print(
            Panel(
                syntax,
                title=f"{arrow} [yellow]{self.name}[/yellow] :: [bold]{method}[/bold]",
                border_style="dim",
                expand=False,
            )
        )

    async def __aenter__(self) -> MCPClient:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Spawns the server subprocess and performs the MCP initialize handshake."""
        params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env,
        )

        if self.verbose:
            console.print(f"[dim]Spawning server process: {self.command} {' '.join(self.args)}[/dim]")

        # 1. Open stdio transport
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(params)
        )

        # 2. Establish ClientSession
        self.session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        # 3. Perform initialization handshake
        self._log_rpc("out", "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
            "clientInfo": {"name": "mcp-deepdive-client", "version": "1.0.0"}
        })

        init_result = await self.session.initialize()

        self._log_rpc("in", "initialize_result", {
            "protocolVersion": init_result.protocol_version,
            "serverInfo": {
                "name": init_result.server_info.name,
                "version": init_result.server_info.version,
            },
            "capabilities": str(init_result.capabilities),
        })

        if self.verbose:
            console.print(
                f"[bold green]Connected successfully to '{init_result.server_info.name}' "
                f"(v{init_result.server_info.version})![/bold green]\n"
            )

    async def list_tools(self) -> list[Tool]:
        """Discover tools exposed by this MCP server."""
        if not self.session:
            raise RuntimeError("Client is not connected. Call connect() first.")

        self._log_rpc("out", "tools/list", {})
        result = await self.session.list_tools()
        self._tools_cache = result.tools

        summary = [
            {
                "name": t.name,
                "description": t.description,
                "parameters": getattr(t, "input_schema", getattr(t, "inputSchema", {})),
            }
            for t in result.tools
        ]
        self._log_rpc("in", "tools/list_result", summary)
        return self._tools_cache

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Execute an MCP tool call on the remote server.
        
        Args:
            tool_name: The name of the tool to execute.
            arguments: The JSON-serializable argument dictionary matching tool inputSchema.
        """
        if not self.session:
            raise RuntimeError("Client is not connected. Call connect() first.")

        self._log_rpc("out", "tools/call", {"name": tool_name, "arguments": arguments})

        result = await self.session.call_tool(tool_name, arguments)

        # Content is typically a list of Content objects (TextContent, ImageContent, etc.)
        parsed_content = []
        for c in result.content:
            if hasattr(c, "text"):
                try:
                    # Attempt to parse as JSON if it's formatted as JSON string
                    parsed_content.append(json.loads(c.text))
                except Exception:
                    parsed_content.append(c.text)
            else:
                parsed_content.append(str(c))

        output = {
            "is_error": result.is_error if hasattr(result, "is_error") else False,
            "content": parsed_content[0] if len(parsed_content) == 1 else parsed_content,
        }

        self._log_rpc("in", "tools/call_result", output)
        return output

    async def list_resources(self) -> list[Resource]:
        """List resources exposed by this server."""
        if not self.session:
            raise RuntimeError("Client is not connected.")
        self._log_rpc("out", "resources/list", {})
        result = await self.session.list_resources()
        self._log_rpc("in", "resources/list_result", [r.uri for r in result.resources])
        return result.resources

    async def read_resource(self, uri: str) -> str:
        """Read resource content by URI (e.g. 'db://schema/customers')."""
        if not self.session:
            raise RuntimeError("Client is not connected.")
        self._log_rpc("out", "resources/read", {"uri": uri})
        result = await self.session.read_resource(uri)
        content_text = ""
        for content in result.contents:
            if hasattr(content, "text"):
                content_text += content.text
        self._log_rpc("in", "resources/read_result", {"uri": uri, "preview": content_text[:200]})
        return content_text

    async def list_prompts(self) -> list[Prompt]:
        """List prompt templates provided by this server."""
        if not self.session:
            raise RuntimeError("Client is not connected.")
        self._log_rpc("out", "prompts/list", {})
        result = await self.session.list_prompts()
        self._log_rpc("in", "prompts/list_result", [p.name for p in result.prompts])
        return result.prompts

    async def get_prompt(self, name: str, arguments: Optional[dict[str, str]] = None) -> Any:
        """Retrieve a rendered prompt template."""
        if not self.session:
            raise RuntimeError("Client is not connected.")
        args = arguments or {}
        self._log_rpc("out", "prompts/get", {"name": name, "arguments": args})
        result = await self.session.get_prompt(name, args)
        self._log_rpc("in", "prompts/get_result", {"messages": [m.content for m in result.messages]})
        return result

    async def close(self):
        """Gracefully terminate session and subprocess."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self.session = None
            if self.verbose:
                console.print(f"[dim]Disconnected from '{self.name}'.[/dim]")
