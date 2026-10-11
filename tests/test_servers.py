"""
Unit and integration tests for MCP Servers.
Verifies tool functions, parameters, and protocol responses.
"""
import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from servers.math_server import add, multiply, factorial, power
from servers.weather_server import get_current_weather, get_weather_forecast
from servers.database_server import (
    query_customers,
    get_order_details,
    get_customers_schema,
    get_orders_schema,
    customer_summary_prompt,
)
from servers.filesystem_server import (
    write_sandbox_file,
    read_sandbox_file,
    list_sandbox_files,
)


def test_math_server_tools():
    """Verify math server tool logic."""
    assert add(10.5, 4.5) == 15.0
    assert multiply(6.0, 7.0) == 42.0
    assert factorial(5) == 120
    assert factorial(0) == 1
    assert power(2.0, 8.0) == 256.0

    with pytest.raises(ValueError, match="Factorial is only defined for non-negative"):
        factorial(-1)

    with pytest.raises(ValueError, match="Integer too large"):
        factorial(25)


def test_weather_server_tools():
    """Verify weather server tool responses."""
    tokyo = get_current_weather("Tokyo")
    assert tokyo["city"] == "Tokyo"
    assert "temperature_c" in tokyo
    assert "condition" in tokyo

    forecast = get_weather_forecast("Paris", days=3)
    assert forecast["city"] == "Paris"
    assert len(forecast["daily_forecast"]) == 3
    assert forecast["daily_forecast"][0]["day"] == 1


def test_database_server_tools_and_resources():
    """Verify database server tools, schema resources, and prompts."""
    # Tool: query_customers
    all_custs = query_customers()
    assert len(all_custs) >= 4

    alice = query_customers("Alice")
    assert len(alice) == 1
    assert alice[0]["name"] == "Alice Johnson"
    assert alice[0]["spend_usd"] == 4250.00

    # Tool: get_order_details
    order = get_order_details("ORD-901")
    assert order["customer_id"] == "CUST-101"
    assert order["amount"] == 189.99

    with pytest.raises(ValueError, match="was not found"):
        get_order_details("ORD-NONEXISTENT")

    # Resources
    cust_schema = get_customers_schema()
    assert "customers" in cust_schema
    assert "spend_usd" in cust_schema

    order_schema = get_orders_schema()
    assert "orders" in order_schema

    # Prompt
    prompt = customer_summary_prompt("Alice Johnson")
    assert "Alice Johnson" in prompt
    assert "Customer Relations Manager" in prompt


def test_filesystem_server_sandbox():
    """Verify safe sandboxed filesystem operations."""
    test_filename = "test_run.txt"
    test_content = "MCP sandboxed write test content."

    # Write
    res = write_sandbox_file(test_filename, test_content)
    assert "Successfully saved" in res

    # Read
    read_back = read_sandbox_file(test_filename)
    assert read_back == test_content

    # List
    file_list = list_sandbox_files()
    assert any(f["name"] == test_filename for f in file_list)

    # Path traversal protection
    with pytest.raises(Exception):
        read_sandbox_file("../../secret.txt")
