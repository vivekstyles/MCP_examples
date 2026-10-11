"""
Example 03: Multi-Turn Tool Chaining & Sequential Reasoning (INTERMEDIATE)
==========================================================================
Demonstrates how an AI Agent handles complex tasks requiring multiple MCP tools in sequence:
1. Connecting to multiple MCP servers (Database Server + Math Server).
2. The ReAct (Reasoning + Acting) loop where the output of Tool #1 feeds as input to Tool #2.
3. Live multi-turn decision loop with local Ollama or educational Mock Agent.
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
    parser = argparse.ArgumentParser(description="Demonstrate multi-turn tool chaining with MCP")
    parser.add_argument("--mock", action="store_true", help="Run with deterministic mock agent instead of live Ollama")
    parser.add_argument("--model", type=str, default="gemma4:12b", help="Ollama model name (default: gemma4:12b)")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]Example 03: Multi-Turn Sequential Tool Chaining (ReAct Loop)[/bold cyan]\n"
        "[dim]Watch the agent dynamically chain tools: Database Lookup -> Math Calculation -> Synthesis.[/dim]",
        border_style="cyan"
    ))

    db_script = str(PROJECT_ROOT / "servers" / "database_server.py")
    math_script = str(PROJECT_ROOT / "servers" / "math_server.py")

    # Connect to both Database Server and Math Server concurrently
    hub = MultiServerMCPClient(verbose=True)
    hub.add_server("db", db_script)
    hub.add_server("math", math_script)

    async with hub:
        # Prompt requiring sequential steps:
        user_prompt = (
            "Look up Alice's customer account details in our database to find her total spend. "
            "Then, calculate what a 15% VIP loyalty discount on that spend would be, "
            "and tell me how much discount she receives."
        )

        tools = hub.registry.to_ollama_format()

        if args.mock:
            console.print("\n[dim]Running in --mock mode...[/dim]")
            # In mock mode, we demonstrate the step-by-step chaining explicitly
            console.print("\n[bold yellow]Step 1: Agent decides to call 'db__query_customers'[/bold yellow]")
            cust_res = await hub.call_tool("db__query_customers", {"search_term": "Alice"})
            cust_data = cust_res["content"]
            if isinstance(cust_data, list):
                cust_data = cust_data[0]
            alice_spend = float(cust_data["spend_usd"])
            console.print(f"  -> Found Alice's lifetime spend: [bold green]${alice_spend:,.2f}[/bold green]")

            console.print("\n[bold yellow]Step 2: Agent decides to call 'math__multiply'[/bold yellow]")
            discount_res = await hub.call_tool("math__multiply", {"a": alice_spend, "b": 0.15})
            discount_amount = discount_res["content"]
            console.print(f"  -> Calculated 15% discount: [bold green]${discount_amount:.2f}[/bold green]")

            final_msg = (
                f"Alice Johnson has a total lifetime spend of ${alice_spend:,.2f}. "
                f"A 15% VIP loyalty discount amounts to ${discount_amount:,.2f}."
            )
            console.print(Panel(final_msg, title="🏁 [bold green]Final Agent Synthesis[/bold green]", border_style="green"))

        else:
            console.print(f"\n[dim]Connecting to local Ollama ({args.model})...[/dim]")
            agent = OllamaAgent(
                model=args.model,
                system_prompt=(
                    "You are a helpful AI assistant equipped with database and math tools via MCP. "
                    "When asked to retrieve data and compute values, first call the database tool to fetch "
                    "the data, then call the math tool to do the calculation, and finally summarize the result."
                ),
                verbose=True
            )
            await agent.run(user_prompt, tools, hub.call_tool)


if __name__ == "__main__":
    asyncio.run(main())
