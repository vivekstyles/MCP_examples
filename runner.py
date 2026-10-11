"""
MCP Interactive CLI Learning Hub & Runner.
Provides a rich interactive terminal menu to explore and execute all MCP examples.
"""
import os
import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console()
PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable

EXAMPLES = [
    {
        "id": "1",
        "title": "Protocol Handshake & Direct Calls",
        "level": "Basic",
        "script": "examples/01_protocol_handshake.py",
        "desc": "Inspect the raw JSON-RPC 2.0 initialize handshake, tools/list, and tools/call.",
    },
    {
        "id": "2",
        "title": "How LLM Agents Select Tools",
        "level": "Intermediate",
        "script": "examples/02_llm_tool_selection.py",
        "desc": "See how tool docstrings and parameter schemas guide the model's decision.",
    },
    {
        "id": "3",
        "title": "Multi-Turn Tool Chaining (ReAct)",
        "level": "Intermediate",
        "script": "examples/03_multi_turn_chaining.py",
        "desc": "Sequential tool chaining: Database Query -> Math Calculation -> Synthesis.",
    },
    {
        "id": "4",
        "title": "Error Handling & Self-Correction",
        "level": "Intermediate",
        "script": "examples/04_error_handling_recovery.py",
        "desc": "Observe how tool errors propagate back to the agent and how it recovers.",
    },
    {
        "id": "5",
        "title": "Multi-Server MCP Hub",
        "level": "Advanced",
        "script": "examples/05_multi_server_hub.py",
        "desc": "Aggregate Weather, Filesystem, and Math servers into one unified agent.",
    },
    {
        "id": "6",
        "title": "Dynamic Tool Routing & Pruning",
        "level": "Advanced",
        "script": "examples/06_dynamic_tool_routing.py",
        "desc": "Scale to 50+ tools using dynamic semantic retrieval (Tool RAG).",
    },
    {
        "id": "7",
        "title": "Beyond Tools: Resources & Prompts",
        "level": "Advanced",
        "script": "examples/07_resources_and_prompts.py",
        "desc": "Read passive schema resources (db://) and fetch reusable prompt templates.",
    },
    {
        "id": "8",
        "title": "Run Pytest Verification Suite",
        "level": "Testing",
        "script": "pytest",
        "desc": "Execute automated pytest suite across all servers and client logic.",
    },
]


def display_menu():
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Model Context Protocol (MCP) Interactive Learning Hub[/bold cyan]\n"
        "[dim]Explore how agents connect, reason, and decide which MCP tools to execute.[/dim]",
        border_style="cyan"
    ))

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("#", style="bold yellow", width=4)
    table.add_column("Level", style="dim", width=14)
    table.add_column("Example Title", style="bold white", width=34)
    table.add_column("Description", style="cyan")

    for item in EXAMPLES:
        table.add_row(item["id"], item["level"], item["title"], item["desc"])

    console.print(table)
    console.print("[dim]Options: Enter a number (1-8), [bold]q[/bold] to quit, or append [bold]--mock[/bold] for mock mode (e.g. '2 --mock')[/dim]\n")


def run_example(choice_str: str):
    parts = choice_str.strip().split()
    if not parts:
        return True

    cmd_id = parts[0]
    extra_flags = parts[1:]

    if cmd_id.lower() in ("q", "quit", "exit"):
        console.print("[green]Goodbye![/green]")
        return False

    matched = next((item for item in EXAMPLES if item["id"] == cmd_id), None)
    if not matched:
        console.print(f"[bold red]Invalid option:[/bold red] '{cmd_id}'. Please select 1-8.")
        return True

    console.rule(f"[bold green]Running: {matched['title']}[/bold green]")

    if matched["script"] == "pytest":
        cmd = [PYTHON_EXE, "-m", "pytest", "tests/", "-v"]
    else:
        cmd = [PYTHON_EXE, matched["script"]] + extra_flags

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env, check=False)
    except Exception as e:
        console.print(f"[bold red]Execution error:[/bold red] {e}")

    console.rule("[dim]End of Execution[/dim]")
    return True


def main():
    while True:
        display_menu()
        try:
            choice = input("Select an example (1-8) or 'q' to quit: ")
            if not run_example(choice):
                break
        except (KeyboardInterrupt, EOFError):
            console.print("\n[green]Exiting learning hub.[/green]")
            break


if __name__ == "__main__":
    main()
