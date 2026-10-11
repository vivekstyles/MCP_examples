"""
Filesystem MCP Server
Demonstrates safe, sandboxed file operations via Model Context Protocol.
"""
from pathlib import Path
from mcp.server.mcpserver import MCPServer

server = MCPServer("filesystem-server")

# Base directory for the safe sandbox (relative to project root)
SANDBOX_DIR = Path(__file__).resolve().parent.parent / "sandbox_storage"
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)


def _safe_path(filename: str) -> Path:
    """Ensure paths cannot escape the sandbox directory."""
    clean_name = Path(filename).name  # Prevent directory traversal ../../
    target = (SANDBOX_DIR / clean_name).resolve()
    if not str(target).startswith(str(SANDBOX_DIR.resolve())):
        raise PermissionError("Access denied: Path attempts to escape sandbox.")
    return target


@server.tool()
def list_sandbox_files() -> list[dict]:
    """
    List all accessible files inside the sandbox directory.
    
    Use this tool to see what documents, logs, or reports are currently stored.
    """
    files = []
    for item in SANDBOX_DIR.iterdir():
        if item.is_file():
            files.append({
                "name": item.name,
                "size_bytes": item.stat().st_size,
                "is_file": True,
            })
    return files


@server.tool()
def read_sandbox_file(filename: str) -> str:
    """
    Read the full text content of a file within the sandbox.
    
    Args:
        filename: Name of the file to read (e.g. 'notes.txt', 'report.md').
    """
    target = _safe_path(filename)
    if not target.exists():
        raise FileNotFoundError(f"File '{filename}' does not exist in sandbox.")
    return target.read_text(encoding="utf-8")


@server.tool()
def write_sandbox_file(filename: str, content: str) -> str:
    """
    Write or overwrite text content to a file inside the sandbox.
    
    Args:
        filename: Name of the destination file (e.g., 'summary.txt').
        content: The text content to write.
    """
    target = _safe_path(filename)
    target.write_text(content, encoding="utf-8")
    return f"Successfully saved {len(content)} characters to '{target.name}'."


if __name__ == "__main__":
    server.run(transport="stdio")
