"""
Example 02: How LLM Agents Select Tools (INTERMEDIATE)
=====================================================
Demonstrates the exact mechanism by which an AI agent decides WHICH tool to call:
1. Converting MCP Tool JSON Schemas into the model's function-calling context.
2. The role of Tool Names, Docstrings/Descriptions, and Parameter Types in guiding
   the model's attention probabilities.
3. Live reasoning and tool dispatch using local Ollama (e.g., gemma4:12b).
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

from core.client import MCPClient
from core.tool_registry import MCPToolRegistry
from core.llm_adapter import OllamaAgent, MockAgent
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


async def run_scenario(agent, client, registry, user_prompt: str, scenario_num: int):
    console.print(f"\n[bold green]{'=' * 68}[/bold green]")
    console.print(f"[bold yellow]Scenario {scenario_num}:[/bold yellow] [bold white]\"{user_prompt}\"[/bold white]")
    console.print(f"[bold green]{'=' * 68}[/bold green]")

    # Convert registered MCP tools to Ollama function calling format
    ollama_tools = registry.to_ollama_format()

    # The tool executor callback dispatches the call back to the MCP Client
    async def executor(name: str, args: dict):
        return await client.call_tool(name, args)

    await agent.run(user_prompt, ollama_tools, executor)


async def main():
    parser = argparse.ArgumentParser(description="Demonstrate LLM tool selection via MCP")
    parser.add_argument("--mock", action="store_true", help="Run with deterministic mock agent instead of Ollama")
    parser.add_argument("--model", type=str, default="gemma4:12b", help="Ollama model name (default: gemma4:12b)")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]Example 02: How Agents Decide Which MCP Tool to Call[/bold cyan]\n"
        "[dim]Observe how tool descriptions & parameter schemas direct the LLM's choice.[/dim]",
        border_style="cyan"
    ))

    weather_script = str(PROJECT_ROOT / "servers" / "weather_server.py")
    registry = MCPToolRegistry()

    # Connect to the Weather MCP Server
    async with MCPClient("WeatherServer", sys.executable, [weather_script], verbose=False) as client:
        tools = await client.list_tools()
        for t in tools:
            registry.register_tool(t)

        # Display the schemas exposed to the model
        table = Table(title="Exposed Tools & Schemas", show_header=True, header_style="bold magenta")
        table.add_column("Tool Name", style="cyan")
        table.add_column("Input Schema", style="green")
        table.add_column("Docstring / Purpose", style="white")

        for t in tools:
            schema = getattr(t, "input_schema", getattr(t, "inputSchema", {})) or {}
            table.add_row(t.name, str(schema.get("properties", {})), (t.description or "").strip().split("\n")[0])
        console.print(table)

        # Initialize either local Ollama or educational Mock agent
        if args.mock:
            console.print("[dim]Running in --mock mode (deterministic simulation)[/dim]\n")
            agent = MockAgent(verbose=True)
        else:
            console.print(f"[dim]Connecting to local Ollama model '{args.model}'...[/dim]\n")
            agent = OllamaAgent(model=args.model, verbose=True)

        # Scenario A: Real-time query -> LLM should select get_current_weather
        await run_scenario(
            agent, client, registry,
            user_prompt="What is the current atmospheric condition and temperature in Tokyo right now?",
            scenario_num=1
        )

        # Scenario B: Forecast query with parameter extraction -> LLM should select get_weather_forecast with days=4
        await run_scenario(
            agent, client, registry,
            user_prompt="Will it rain in Paris over the next 4 days? Please check the upcoming forecast.",
            scenario_num=2
        )


if __name__ == "__main__":
    asyncio.run(main())
