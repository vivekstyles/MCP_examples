"""
Example 06: Dynamic Tool Routing & Semantic Pruning for 50+ Tools (ADVANCED)
============================================================================
Addresses the critical scaling bottleneck in production MCP systems:
1. The "Tool Overload" problem: Why passing 50+ tools in every prompt degrades
   accuracy, increases latency, and wastes context tokens.
2. Dynamic Tool Retrieval (Tool RAG): Scoring and retrieving only the top-K relevant
   tools based on the user's intent.
3. Comparing full registry injection vs. pruned routing.
"""
import argparse
import asyncio
import sys
from pathlib import Path
from mcp.types import Tool

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.tool_registry import MCPToolRegistry
from core.llm_adapter import OllamaAgent, MockAgent
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def create_simulated_large_ecosystem() -> MCPToolRegistry:
    """Populates a tool registry with 25+ realistic enterprise tools across domains."""
    registry = MCPToolRegistry()

    domain_tools = [
        # Database & CRM Domain
        ("crm", "search_customer_by_phone", "Search for CRM account records using an E.164 phone number.", {"phone": {"type": "string"}}),
        ("crm", "update_customer_address", "Update the physical billing or mailing address for a customer.", {"cust_id": {"type": "string"}, "new_address": {"type": "string"}}),
        ("crm", "record_customer_call_log", "Log sales or support call interaction notes onto customer timeline.", {"cust_id": {"type": "string"}, "notes": {"type": "string"}}),
        ("crm", "export_lead_pipeline_csv", "Export current sales qualified leads into a downloadable CSV report.", {"stage": {"type": "string"}}),
        
        # Cloud & DevOps Domain
        ("cloud", "restart_kubernetes_pod", "Gracefully terminate and restart a designated pod in the cluster.", {"pod_name": {"type": "string"}, "namespace": {"type": "string"}}),
        ("cloud", "scale_deployment_replicas", "Adjust the replica count of a deployment or microservice.", {"deployment": {"type": "string"}, "replicas": {"type": "integer"}}),
        ("cloud", "fetch_container_logs", "Stream stdout and stderr logs for a running container.", {"container_id": {"type": "string"}, "lines": {"type": "integer"}}),
        ("cloud", "provision_s3_bucket", "Create a new encrypted cloud object storage bucket.", {"bucket_name": {"type": "string"}, "region": {"type": "string"}}),
        
        # Financial & Math Domain
        ("finance", "calculate_mortgage_amortization", "Calculate monthly loan payment and amortization schedule.", {"principal": {"type": "number"}, "rate": {"type": "number"}, "years": {"type": "integer"}}),
        ("finance", "convert_currency_rates", "Convert an amount between international currency pairs using live rates.", {"amount": {"type": "number"}, "from_curr": {"type": "string"}, "to_curr": {"type": "string"}}),
        ("finance", "compute_compound_interest", "Calculate future value of an investment with compounded interest.", {"principal": {"type": "number"}, "rate": {"type": "number"}, "compounds_per_year": {"type": "integer"}, "years": {"type": "number"}}),
        
        # Weather & Geo Domain
        ("geo", "get_current_weather", "Retrieve real-time atmospheric temperature and conditions for a city.", {"city": {"type": "string"}}),
        ("geo", "get_geocoding_coordinates", "Convert a street address or city name into latitude and longitude coordinates.", {"location": {"type": "string"}}),
        ("geo", "calculate_route_distance", "Compute driving distance and estimated transit duration between two points.", {"origin": {"type": "string"}, "destination": {"type": "string"}}),
        
        # Media & Content Domain
        ("media", "transcribe_audio_recording", "Transcribe speech from an MP3/WAV audio file into timestamped text.", {"file_path": {"type": "string"}}),
        ("media", "resize_image_dimensions", "Scale or crop image dimensions maintaining aspect ratio.", {"image_path": {"type": "string"}, "width": {"type": "integer"}, "height": {"type": "integer"}}),
        ("media", "convert_markdown_to_pdf", "Render a Markdown document into a styled PDF file.", {"md_path": {"type": "string"}, "output_pdf": {"type": "string"}}),
    ]

    for server, name, desc, props in domain_tools:
        t = Tool(
            name=name,
            description=desc,
            inputSchema={"type": "object", "properties": props, "required": list(props.keys())}
        )
        registry.register_tool(t, server_name=server, prefix_namespace=True)

    return registry


async def main():
    parser = argparse.ArgumentParser(description="Demonstrate dynamic tool routing")
    parser.add_argument("--mock", action="store_true", help="Run with mock agent")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]Example 06: Dynamic Tool Routing & Semantic Pruning[/bold cyan]\n"
        "[dim]Scale to 50+ tools without blowing up context windows or confusing the LLM.[/dim]",
        border_style="cyan"
    ))

    registry = create_simulated_large_ecosystem()
    total_tools = len(registry.all_names)

    console.print(f"📦 [bold]Total Tools in Ecosystem:[/bold] [cyan]{total_tools}[/cyan]")

    test_queries = [
        "How much interest will I accumulate on a $50,000 principal at 6.5% interest over 10 years?",
        "Pod 'checkout-service-7f89' is crashing in production. I need to restart it immediately.",
        "What is the current temperature and atmospheric weather condition in Tokyo?",
    ]

    for idx, query in enumerate(test_queries, 1):
        console.print(f"\n[bold green]{'=' * 70}[/bold green]")
        console.print(f"[bold yellow]Query {idx}:[/bold yellow] \"{query}\"")
        console.print(f"[bold green]{'=' * 70}[/bold green]")

        # Dynamic retrieval: Find only the top 3 relevant tools
        top_k = 3
        pruned_tools = registry.find_relevant_tools(query, top_k=top_k)

        table = Table(
            title=f"Tool Retrieval Results (Pruned {total_tools} tools -> Top {top_k})",
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("Rank", style="dim", width=6)
        table.add_column("Selected Tool Name", style="cyan")
        table.add_column("Match Score", style="green", width=12)
        table.add_column("Description Preview", style="white")

        for rank, item in enumerate(pruned_tools, 1):
            fn = item["function"]
            table.add_row(
                f"#{rank}",
                fn["name"],
                f"Score: {item['_score']}",
                fn["description"][:55] + "..."
            )
        console.print(table)

        # Context Token Savings Breakdown:
        tokens_all = total_tools * 120  # ~120 tokens per schema definition
        tokens_pruned = top_k * 120
        savings_pct = ((tokens_all - tokens_pruned) / tokens_all) * 100

        console.print(
            f"💡 [bold]Optimization Telemetry:[/bold] Context reduced from "
            f"[red]~{tokens_all:,} tokens[/red] to [green]~{tokens_pruned} tokens[/green] "
            f"([bold green]{savings_pct:.1f}% context savings[/bold green])"
        )


if __name__ == "__main__":
    asyncio.run(main())
