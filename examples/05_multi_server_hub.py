"""
Example 05: Multi-Server MCP Aggregation Hub (ADVANCED)
=======================================================
Demonstrates how enterprise AI agents connect to multiple heterogeneous MCP servers:
1. Concurrently managing Weather, Filesystem, and Math MCP servers.
2. Namespacing tools ('weather__*', 'fs__*', 'math__*') to avoid collisions.
3. Cross-server workflow: Fetching real-time weather and persisting a report
   to disk through the sandboxed filesystem server.
"""
import argparse
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

from core.multi_client import MultiServerMCPClient
from core.llm_adapter import OllamaAgent, MockAgent
from rich.console import Console
from rich.panel import Panel

console = Console()


async def main():
    parser = argparse.ArgumentParser(description="Demonstrate multi-server MCP aggregation")
    parser.add_argument("--mock", action="store_true", help="Run in deterministic mock mode")
    parser.add_argument("--model", type=str, default="gemma4:12b", help="Ollama model name")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]Example 05: Multi-Server MCP Aggregation Hub[/bold cyan]\n"
        "[dim]Coordinate actions across multiple servers: Weather -> Filesystem -> Math.[/dim]",
        border_style="cyan"
    ))

    weather_script = str(PROJECT_ROOT / "servers" / "weather_server.py")
    filesystem_script = str(PROJECT_ROOT / "servers" / "filesystem_server.py")
    math_script = str(PROJECT_ROOT / "servers" / "math_server.py")

    hub = MultiServerMCPClient(verbose=True)
    hub.add_server("weather", weather_script)
    hub.add_server("fs", filesystem_script)
    hub.add_server("math", math_script)

    async with hub:
        user_prompt = (
            "Check the current weather in New York, and write a summary markdown file named "
            "'ny_weather_report.md' in the sandbox filesystem with the temperature and condition."
        )

        tools = hub.registry.to_ollama_format()

        if args.mock:
            console.print("\n[dim]Running in --mock mode...[/dim]")
            console.print("\n[bold yellow]Step 1: Calling 'weather__get_current_weather'[/bold yellow]")
            w_res = await hub.call_tool("weather__get_current_weather", {"city": "New York"})
            weather_data = w_res["content"]
            console.print(f"  -> Weather received: {weather_data}")

            console.print("\n[bold yellow]Step 2: Calling 'fs__write_sandbox_file'[/bold yellow]")
            md_content = (
                f"# Weather Report: New York\n\n"
                f"- **Temperature:** {weather_data['temperature_c']}°C ({weather_data['temperature_f']}°F)\n"
                f"- **Condition:** {weather_data['condition']}\n"
                f"- **Humidity:** {weather_data['humidity_pct']}%\n"
                f"- **Wind:** {weather_data['wind_kmh']} km/h\n"
            )
            fs_res = await hub.call_tool("fs__write_sandbox_file", {
                "filename": "ny_weather_report.md",
                "content": md_content,
            })
            console.print(f"  -> Filesystem result: [bold green]{fs_res['content']}[/bold green]")

            console.print("\n[bold yellow]Step 3: Verifying file content via 'fs__read_sandbox_file'[/bold yellow]")
            read_res = await hub.call_tool("fs__read_sandbox_file", {"filename": "ny_weather_report.md"})
            console.print(Panel(read_res["content"], title="📄 Saved Sandbox File", border_style="cyan"))

        else:
            console.print(f"\n[dim]Connecting to local Ollama ({args.model})...[/dim]")
            agent = OllamaAgent(
                model=args.model,
                system_prompt=(
                    "You are a helpful assistant with access to weather and filesystem MCP tools. "
                    "When asked to check weather and save a file, call 'weather__get_current_weather' first, "
                    "then format the result and call 'fs__write_sandbox_file' to save it."
                ),
                verbose=True
            )
            await agent.run(user_prompt, tools, hub.call_tool)


if __name__ == "__main__":
    asyncio.run(main())
