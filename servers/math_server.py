"""
Math MCP Server
Exposes arithmetic and mathematical calculation tools via Model Context Protocol.
"""
import math
from mcp.server.mcpserver import MCPServer

# Create an MCP Server instance named "math-server"
server = MCPServer("math-server")


@server.tool()
def add(a: float, b: float) -> float:
    """Calculate the sum of two numbers (a + b).
    
    Use this tool when you need to perform addition between two numerical values.
    
    Args:
        a: The first number to add.
        b: The second number to add.
    """
    return a + b


@server.tool()
def multiply(a: float, b: float) -> float:
    """Calculate the product of two numbers (a * b).
    
    Use this tool when you need to multiply two numerical values.
    
    Args:
        a: The first factor.
        b: The second factor.
    """
    return a * b


@server.tool()
def factorial(n: int) -> int:
    """Compute the factorial of a non-negative integer (n!).
    
    Args:
        n: A non-negative integer (between 0 and 20).
    """
    if n < 0:
        raise ValueError("Factorial is only defined for non-negative integers.")
    if n > 20:
        raise ValueError("Integer too large. Please use n <= 20.")
    return math.factorial(n)


@server.tool()
def power(base: float, exponent: float) -> float:
    """Calculate base raised to the power of exponent (base ^ exponent).
    
    Args:
        base: The base number.
        exponent: The exponent power.
    """
    return math.pow(base, exponent)


if __name__ == "__main__":
    # When executed directly, run using standard input/output (stdio) transport
    server.run(transport="stdio")
