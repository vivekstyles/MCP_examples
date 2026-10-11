"""
Example 01: MCP Protocol Handshake & Direct Tool Calling (BASIC)
================================================================
This example demonstrates the fundamental physical mechanics of MCP:
1. Spawning a server process over standard input/output (stdio).
2. The JSON-RPC 2.0 'initialize' handshake and capability negotiation.
3. Discovering tools via 'tools/list'.
4. Executing a tool directly via 'tools/call'.

No LLM is needed for this example — it inspects the raw protocol layer!
"""
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.client import MCPClient
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


async def main():
    console.print(Panel.fit(
        "[bold cyan]Example 01: MCP Protocol Handshake & Direct Calls[/bold cyan]\n"
        "[dim]Inspect the low-level JSON-RPC 2.0 communication between client and server.[/dim]",
        border_style="cyan"
    ))

    server_script = str(PROJECT_ROOT / "servers" / "math_server.py")

    # Connect to the Math MCP Server over stdio
    # verbose=True will print every JSON-RPC request and response!
    async with MCPClient("MathServer", sys.executable, [server_script], verbose=True) as client:
        
        console.print("\n[bold yellow]Step 1: Listing Tools via MCP protocol[/bold yellow]")
        tools = await client.list_tools()

        # Render discovered tools in a nice table
        table = Table(title="Discovered Tools on MathServer", show_header=True, header_style="bold magenta")
        table.add_column("Tool Name", style="cyan")
        table.add_column("Parameters", style="green")
        table.add_column("Description", style="white")

        for t in tools:
            schema = getattr(t, "input_schema", getattr(t, "inputSchema", {})) or {}
            params = list(schema.get("properties", {}).keys())
            table.add_row(t.name, str(params), (t.description or "").split("\n")[0])
        console.print(table)

        console.print("\n[bold yellow]Step 2: Executing 'add' tool via MCP[/bold yellow]")
        result_add = await client.call_tool("add", {"a": 27.5, "b": 14.5})
        console.print(f"[bold green]Result of add(27.5, 14.5):[/bold green] {result_add['content']}")

        console.print("\n[bold yellow]Step 3: Executing 'factorial' tool via MCP[/bold yellow]")
        result_fact = await client.call_tool("factorial", {"n": 5})
        console.print(f"[bold green]Result of factorial(5):[/bold green] {result_fact['content']}")


if __name__ == "__main__":
    asyncio.run(main())
