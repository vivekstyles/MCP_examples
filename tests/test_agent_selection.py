"""
Unit and integration tests for Tool Registry, Schema Transformer, and Agent Selection.
"""
import pytest
import sys
from pathlib import Path
from mcp.types import Tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.tool_registry import MCPToolRegistry
from core.llm_adapter import MockAgent


def test_registry_registration_and_namespacing():
    """Verify tool registration, namespacing, and retrieval."""
    registry = MCPToolRegistry()

    t1 = Tool(
        name="add",
        description="Add two numbers",
        inputSchema={"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}}
    )
    t2 = Tool(
        name="get_weather",
        description="Get current weather",
        inputSchema={"type": "object", "properties": {"city": {"type": "string"}}}
    )

    reg_name1 = registry.register_tool(t1, server_name="math", prefix_namespace=True)
    reg_name2 = registry.register_tool(t2, server_name="weather", prefix_namespace=True)

    assert reg_name1 == "math__add"
    assert reg_name2 == "weather__get_weather"

    assert registry.get_server_for_tool("math__add") == "math"
    assert registry.get_server_for_tool("weather__get_weather") == "weather"


def test_ollama_format_conversion():
    """Verify that MCP tool definitions are correctly transformed into Ollama format."""
    registry = MCPToolRegistry()
    t = Tool(
        name="calculate_tax",
        description="Calculate sales tax on an amount",
        inputSchema={"type": "object", "properties": {"amount": {"type": "number"}, "rate": {"type": "number"}}}
    )
    registry.register_tool(t)

    ollama_tools = registry.to_ollama_format()
    assert len(ollama_tools) == 1
    tool_def = ollama_tools[0]

    assert tool_def["type"] == "function"
    assert tool_def["function"]["name"] == "calculate_tax"
    assert tool_def["function"]["description"] == "Calculate sales tax on an amount"
    assert "amount" in tool_def["function"]["parameters"]["properties"]


def test_dynamic_tool_pruning_relevance():
    """Verify that dynamic tool pruning accurately selects relevant tools for a query."""
    registry = MCPToolRegistry()

    tools_data = [
        ("add", "Add two numbers together", {"a": {"type": "number"}, "b": {"type": "number"}}),
        ("get_weather", "Fetch current weather for a city", {"city": {"type": "string"}}),
        ("write_file", "Write text content to disk file", {"path": {"type": "string"}}),
        ("query_customers", "Search customers in database", {"query": {"type": "string"}}),
    ]

    for name, desc, props in tools_data:
        registry.register_tool(Tool(name=name, description=desc, inputSchema={"type": "object", "properties": props}))

    # Query 1: Weather
    pruned_weather = registry.find_relevant_tools("What is the current weather forecast for Tokyo?", top_k=1)
    assert len(pruned_weather) == 1
    assert pruned_weather[0]["function"]["name"] == "get_weather"

    # Query 2: File
    pruned_file = registry.find_relevant_tools("Save this text file to disk", top_k=1)
    assert len(pruned_file) == 1
    assert pruned_file[0]["function"]["name"] == "write_file"


@pytest.mark.asyncio
async def test_mock_agent_tool_selection():
    """Verify that MockAgent correctly selects tool and passes arguments based on query."""
    agent = MockAgent(verbose=False)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "multiply",
                "description": "Calculate product of two numbers",
                "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}},
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Retrieve current weather for city",
                "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
            }
        }
    ]

    executed_calls = []

    async def mock_executor(name: str, args: dict):
        executed_calls.append((name, args))
        return 42

    result = await agent.run("What is the weather in Tokyo?", tools, mock_executor)
    assert len(executed_calls) == 1
    assert executed_calls[0][0] == "get_current_weather"
    assert executed_calls[0][1]["city"] == "Tokyo"
    assert "42" in result
