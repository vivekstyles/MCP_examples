"""
Database MCP Server
Demonstrates MCP Tools, Resources, and Prompts in a single server.
Simulates an e-commerce customer and order database.
"""
import json
from mcp.server.mcpserver import MCPServer

server = MCPServer("database-server")

# In-memory customer and orders data
_CUSTOMERS = [
    {"id": "CUST-101", "name": "Alice Johnson", "email": "alice@example.com", "tier": "Gold", "spend_usd": 4250.00},
    {"id": "CUST-102", "name": "Bob Smith", "email": "bob@example.com", "tier": "Silver", "spend_usd": 850.50},
    {"id": "CUST-103", "name": "Charlie Lee", "email": "charlie@example.com", "tier": "Bronze", "spend_usd": 120.00},
    {"id": "CUST-104", "name": "Diana Ross", "email": "diana@example.com", "tier": "Platinum", "spend_usd": 12890.00},
]

_ORDERS = {
    "ORD-901": {"id": "ORD-901", "customer_id": "CUST-101", "item": "Ergonomic Mechanical Keyboard", "amount": 189.99, "status": "Delivered"},
    "ORD-902": {"id": "ORD-902", "customer_id": "CUST-101", "item": "4K Ultra-wide Monitor", "amount": 799.00, "status": "Shipped"},
    "ORD-903": {"id": "ORD-903", "customer_id": "CUST-102", "item": "USB-C Multiport Hub", "amount": 49.99, "status": "Processing"},
    "ORD-904": {"id": "ORD-904", "customer_id": "CUST-104", "item": "Autonomous AI Server Rack", "amount": 12000.00, "status": "Delivered"},
}


# ==============================================================================
# MCP TOOLS (Executable actions)
# ==============================================================================

@server.tool()
def query_customers(search_term: str = "") -> list[dict]:
    """Search and retrieve customer accounts matching a name, email, or tier.
    
    Args:
        search_term: Optional substring to filter customers by name, tier, or email.
                     If empty, returns all customers.
    """
    if not search_term:
        return _CUSTOMERS
    
    term = search_term.lower()
    return [
        c for c in _CUSTOMERS
        if term in c["name"].lower() or term in c["email"].lower() or term in c["tier"].lower()
    ]


@server.tool()
def get_order_details(order_id: str) -> dict:
    """Retrieve comprehensive order details by order ID (e.g., 'ORD-901').
    
    Args:
        order_id: The unique order identifier.
    """
    normalized = order_id.strip().upper()
    if normalized in _ORDERS:
        return _ORDERS[normalized]
    raise ValueError(f"Order '{order_id}' was not found in database records.")


# ==============================================================================
# MCP RESOURCES (Read-only data endpoints like files or schemas)
# ==============================================================================

@server.resource("db://schema/customers")
def get_customers_schema() -> str:
    """Returns the JSON schema definition for the Customers table."""
    return json.dumps({
        "table": "customers",
        "description": "Registered customer accounts and lifetime spend metrics",
        "columns": {
            "id": {"type": "VARCHAR(16)", "primary_key": True},
            "name": {"type": "VARCHAR(128)", "nullable": False},
            "email": {"type": "VARCHAR(128)", "unique": True},
            "tier": {"type": "ENUM('Bronze', 'Silver', 'Gold', 'Platinum')"},
            "spend_usd": {"type": "DECIMAL(10, 2)"},
        }
    }, indent=2)


@server.resource("db://schema/orders")
def get_orders_schema() -> str:
    """Returns the JSON schema definition for the Orders table."""
    return json.dumps({
        "table": "orders",
        "description": "Customer purchase transaction records",
        "columns": {
            "id": {"type": "VARCHAR(16)", "primary_key": True},
            "customer_id": {"type": "VARCHAR(16)", "foreign_key": "customers.id"},
            "item": {"type": "VARCHAR(256)"},
            "amount": {"type": "DECIMAL(10, 2)"},
            "status": {"type": "ENUM('Processing', 'Shipped', 'Delivered', 'Cancelled')"},
        }
    }, indent=2)


# ==============================================================================
# MCP PROMPTS (Pre-configured reusable prompt templates)
# ==============================================================================

@server.prompt()
def customer_summary_prompt(customer_name: str) -> str:
    """
    Pre-configured prompt template to summarize a customer's loyalty profile.
    
    Args:
        customer_name: The name of the customer to summarize.
    """
    return (
        f"You are a Senior Customer Relations Manager. Please look up customer '{customer_name}' "
        f"using the database tools, review their spending tier and past orders, and write a polite "
        f"3-bullet summary highlighting their loyalty status and upsell opportunities."
    )


if __name__ == "__main__":
    server.run(transport="stdio")
