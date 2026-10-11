"""
Example 07: Beyond Tools: MCP Resources and Prompts (ADVANCED)
==============================================================
MCP is not just a tool-calling protocol! It provides three first-class primitives:
1. Tools: Dynamic functions executed by servers with side effects.
2. Resources: Read-only context sources exposed via URI (e.g. 'db://schema/customers').
3. Prompts: Standardized prompt templates served from the backend to ensure
   consistent behavior across different AI clients.
"""
import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.client import MCPClient
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


async def main():
    console.print(Panel.fit(
        "[bold cyan]Example 07: MCP Resources and Prompts[/bold cyan]\n"
        "[dim]Explore the two other pillars of MCP: Passive Resources & Reusable Prompt Templates.[/dim]",
        border_style="cyan"
    ))

    db_script = str(PROJECT_ROOT / "servers" / "database_server.py")

    async with MCPClient("DatabaseServer", sys.executable, [db_script], verbose=False) as client:
        
        # ======================================================================
        # Part 1: MCP Resources
        # ======================================================================
        console.print("\n[bold yellow]Part 1: Discovering and Reading MCP Resources[/bold yellow]")
        console.print("[dim]Resources are context items (like schemas, files, or configs) referenced by URI.[/dim]\n")

        resources = await client.list_resources()

        table = Table(title="Exposed Database Resources", show_header=True, header_style="bold magenta")
        table.add_column("Resource URI", style="cyan")
        table.add_column("Description", style="white")

        for r in resources:
            table.add_row(str(r.uri), r.description or "(Schema Definition)")
        console.print(table)

        # Read the customers table schema resource
        target_uri = "db://schema/customers"
        console.print(f"\n[bold green]Reading Resource:[/bold green] [cyan]{target_uri}[/cyan]")
        schema_content = await client.read_resource(target_uri)
        syntax = Syntax(schema_content, "json", theme="monokai", word_wrap=True)
        console.print(Panel(syntax, title=f"📋 Resource Content ({target_uri})", border_style="green"))

        # ======================================================================
        # Part 2: MCP Prompts
        # ======================================================================
        console.print("\n[bold yellow]Part 2: Discovering and Fetching Server Prompts[/bold yellow]")
        console.print("[dim]Prompts allow server owners to define standard prompts/instructions for agents.[/dim]\n")

        prompts = await client.list_prompts()
        for p in prompts:
            console.print(f"• Discovered Prompt: [bold cyan]{p.name}[/bold cyan] - [dim]{p.description}[/dim]")

        # Fetch the rendered prompt with arguments
        console.print("\n[bold green]Fetching Prompt:[/bold green] 'customer_summary_prompt' for customer 'Alice Johnson'")
        rendered_prompt = await client.get_prompt("customer_summary_prompt", {"customer_name": "Alice Johnson"})
        
        # Display the prompt messages
        for msg in rendered_prompt.messages:
            console.print(Panel(
                str(getattr(msg.content, "text", msg.content)),
                title=f"📝 Server Prompt Message (Role: {msg.role})",
                border_style="yellow"
            ))


if __name__ == "__main__":
    asyncio.run(main())
