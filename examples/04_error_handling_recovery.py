"""
Example 04: Error Handling, Exception Propagation & Agent Self-Correction (INTERMEDIATE)
========================================================================================
Demonstrates what happens when a tool execution fails or receives invalid parameters:
1. How MCP captures and propagates errors (is_error: True, JSON-RPC error responses).
2. How the error message is fed back into the agent's context.
3. How an agent uses the error feedback to self-correct its parameters or provide
   actionable guidance to the user.
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

console = Console()


async def main():
    parser = argparse.ArgumentParser(description="Demonstrate MCP error handling and recovery")
    parser.add_argument("--mock", action="store_true", help="Run with deterministic mock agent")
    parser.add_argument("--model", type=str, default="gemma4:12b", help="Ollama model name")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]Example 04: Tool Error Handling & Agent Self-Correction[/bold cyan]\n"
        "[dim]Observe how MCP returns errors and how the agent inspects the error to recover.[/dim]",
        border_style="cyan"
    ))

    math_script = str(PROJECT_ROOT / "servers" / "math_server.py")
    registry = MCPToolRegistry()

    async with MCPClient("MathServer", sys.executable, [math_script], verbose=True) as client:
        tools = await client.list_tools()
        for t in tools:
            registry.register_tool(t)

        console.print("\n[bold yellow]Demonstration 1: Direct Protocol Error Inspection[/bold yellow]")
        console.print("[dim]We deliberately call factorial(-5) which violates domain rules.[/dim]\n")

        try:
            res = await client.call_tool("factorial", {"n": -5})
            console.print(f"[bold red]Tool returned error result:[/bold red] {res}")
        except Exception as e:
            console.print(f"[bold red]Client intercepted exception:[/bold red] {e}")

        console.print("\n[bold yellow]Demonstration 2: Agent Encountering & Explaining a Tool Error[/bold yellow]")
        user_prompt = "Calculate the factorial of -5 using the math tools."
        ollama_tools = registry.to_ollama_format()

        if args.mock:
            console.print("[dim]Running in --mock mode...[/dim]")
            console.print("  -> Agent attempts to call: factorial(n=-5)")
            try:
                err_res = await client.call_tool("factorial", {"n": -5})
                err_msg = str(err_res)
            except Exception as ex:
                err_msg = str(ex)

            console.print(f"  -> MCP Error received: [bold red]{err_msg}[/bold red]")
            console.print("  -> Agent self-correction: Reads error 'Factorial is only defined for non-negative integers.'")
            recovery_msg = (
                "I attempted to calculate the factorial of -5, but the tool reported an error: "
                "'Factorial is only defined for non-negative integers.' "
                "Factorial is not defined for negative numbers in standard mathematics. "
                "Did you mean positive 5 (which would be 120)?"
            )
            console.print(Panel(recovery_msg, title="🏁 [bold green]Agent Self-Corrected Response[/bold green]", border_style="green"))

        else:
            console.print(f"[dim]Running with local Ollama ({args.model})...[/dim]")
            agent = OllamaAgent(
                model=args.model,
                system_prompt=(
                    "You are an AI assistant equipped with math tools. If a tool reports an error "
                    "or fails, read the error message carefully and explain the problem clearly to the user."
                ),
                verbose=True
            )
            await agent.run(user_prompt, ollama_tools, client.call_tool)


if __name__ == "__main__":
    asyncio.run(main())
