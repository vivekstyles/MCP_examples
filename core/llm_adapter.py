"""
Agent Brain & LLM Adapter.
Demonstrates how AI agents parse tool schemas, evaluate user requests,
decide which tool to call, and execute the multi-turn ReAct loop.
Supports local Ollama models (e.g., gemma4:12b) and an educational Mock LLM.
"""
from __future__ import annotations
import json
import re
from typing import Any, Callable, Optional, Union
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

console = Console()


class OllamaAgent:
    """
    An autonomous agent powered by a local Ollama model.
    Implements the standard ReAct (Reasoning + Acting) loop with MCP tools.
    """

    def __init__(
        self,
        model: str = "gemma4:12b",
        host: str = "http://localhost:11434",
        system_prompt: Optional[str] = None,
        verbose: bool = True,
    ):
        self.model = model
        self.client = ollama.Client(host=host)
        self.system_prompt = system_prompt or (
            "You are a helpful, precise AI assistant equipped with Model Context Protocol (MCP) tools. "
            "Whenever you need external calculations, weather, data, or file operations, choose the "
            "most appropriate tool. Always explain your reasoning before or during tool use."
        )
        self.verbose = verbose

    async def run(
        self,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_executor: Callable[[str, dict[str, Any]], Any],
        max_turns: int = 5,
    ) -> str:
        """
        Executes a multi-turn ReAct loop:
        1. Submits messages + MCP tool schemas to Ollama.
        2. Inspects model response for tool calls.
        3. If tool calls exist: executes them via `tool_executor` (MCP client).
        4. Appends tool results to conversation and repeats until final answer.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if self.verbose:
            console.print(Panel(
                f"[bold cyan]User Request:[/bold cyan] {user_prompt}\n"
                f"[dim]Available MCP Tools exposed to Ollama:[/dim] {[t['function']['name'] for t in tools]}",
                title=f"🤖 [bold green]Agent ({self.model}) Execution Started[/bold green]",
                border_style="green",
            ))

        turn = 0
        while turn < max_turns:
            turn += 1
            if self.verbose:
                console.print(f"\n[bold yellow]─── Step {turn} / {max_turns}: Model Reasoning ───[/bold yellow]")

            # Call Ollama with messages and tools
            try:
                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    tools=tools if tools else None,
                )
            except Exception as e:
                console.print(f"[bold red]Ollama chat error:[/bold red] {e}")
                raise

            assistant_msg = response.message

            # Display model thinking or reasoning if present
            if hasattr(assistant_msg, "thinking") and assistant_msg.thinking:
                if self.verbose:
                    console.print(Panel(
                        f"[italic dim]{assistant_msg.thinking.strip()}[/italic dim]",
                        title="🧠 [bold]Model Internal Monologue / Attention[/bold]",
                        border_style="cyan",
                    ))

            # Check if the model decided to call any tools
            tool_calls = getattr(assistant_msg, "tool_calls", None)

            if not tool_calls:
                # The model reached its final textual response
                final_answer = assistant_msg.content or "(No text returned)"
                if self.verbose:
                    console.print(Panel(
                        final_answer,
                        title="🏁 [bold green]Final Agent Response[/bold green]",
                        border_style="bright_green",
                    ))
                return final_answer

            # Add assistant message with tool calls to history
            messages.append(assistant_msg)

            # Execute each requested tool call
            for tc in tool_calls:
                func_name = tc.function.name
                func_args = tc.function.arguments or {}

                if self.verbose:
                    console.print(
                        f"👉 [bold magenta]Decision:[/bold magenta] Model chose tool "
                        f"[bold yellow]'{func_name}'[/bold yellow] with args: [cyan]{func_args}[/cyan]"
                    )

                # Execute through the MCP Client / Tool Executor
                try:
                    result = await tool_executor(func_name, func_args)
                    result_str = json.dumps(result, default=str)
                except Exception as ex:
                    result_str = json.dumps({"error": str(ex)})
                    if self.verbose:
                        console.print(f"[bold red]Tool execution exception:[/bold red] {ex}")

                if self.verbose:
                    console.print(f"📥 [bold dim]Result returned to Agent context:[/bold dim] {result_str[:200]}")

                # Append tool response message into context
                messages.append({
                    "role": "tool",
                    "content": result_str,
                })

        return "Agent stopped: Reached maximum turn iterations."


class MockAgent:
    """
    An educational, deterministic mock agent.
    Simulates the exact internal decision process of how an LLM evaluates tool schemas
    without needing a live model. Ideal for testing, continuous integration, and learning.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    async def run(
        self,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_executor: Callable[[str, dict[str, Any]], Any],
    ) -> str:
        """Simulates tool selection based on schema token matching."""
        if self.verbose:
            console.print(Panel(
                f"[bold cyan]User Request:[/bold cyan] {user_prompt}",
                title="🎓 [bold magenta]Mock Agent (Educational Simulation)[/bold magenta]",
                border_style="magenta",
            ))

        # 1. Scoring & Decision logic: Evaluate which tool description matches the prompt
        scored = []
        words = set(re.findall(r"\w+", user_prompt.lower()))
        for t in tools:
            fn = t["function"]
            desc_words = set(re.findall(r"\w+", (fn["name"] + " " + fn.get("description", "")).lower()))
            overlap = len(words.intersection(desc_words))
            scored.append((overlap, fn))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_fn = scored[0]

        if best_score == 0:
            return "I am not sure which tool to use for this request."

        if self.verbose:
            console.print(f"🔍 [bold]LLM Attention Matching Analysis:[/bold]")
            for sc, fn in scored:
                console.print(f"  • Tool [yellow]{fn['name']}[/yellow] - Relevance Score: [cyan]{sc}[/cyan]")
            console.print(f"\n👉 [bold green]Selected Tool:[/bold green] [bold yellow]{best_fn['name']}[/bold yellow]")

        # Extract basic numbers or parameters from user prompt
        args: dict[str, Any] = {}
        numbers = [float(x) for x in re.findall(r"\b\d+\.?\d*\b", user_prompt)]
        
        param_props = best_fn.get("parameters", {}).get("properties", {})
        param_names = list(param_props.keys())

        if "city" in param_names:
            for city in ["tokyo", "paris", "new york", "london", "bengaluru"]:
                if city in user_prompt.lower():
                    args["city"] = city.title()
                    break
            if "city" not in args:
                args["city"] = "Paris"

        elif len(numbers) >= 2 and len(param_names) >= 2:
            args[param_names[0]] = numbers[0]
            args[param_names[1]] = numbers[1]
        elif len(numbers) >= 1 and len(param_names) >= 1:
            args[param_names[0]] = int(numbers[0])

        if self.verbose:
            console.print(f"👉 [bold magenta]Synthesized Tool Arguments:[/bold magenta] [cyan]{args}[/cyan]")

        # Execute
        result = await tool_executor(best_fn["name"], args)

        final_answer = (
            f"Based on the tool call '{best_fn['name']}' with arguments {args}, "
            f"the result obtained was: {result}."
        )

        if self.verbose:
            console.print(Panel(
                final_answer,
                title="🏁 [bold green]Agent Synthesis[/bold green]",
                border_style="green",
            ))

        return final_answer
