"""
Tool Registry and Schema Transformer.
Converts MCP Tool schemas into LLM function signatures (Ollama / OpenAI formats)
and provides routing and parameter validation.
"""
from __future__ import annotations
import re
from typing import Any, Optional
from mcp.types import Tool


class MCPToolRegistry:
    """
    Central repository for tools collected from one or more MCP servers.
    Handles schema translation, namespacing, and tool retrieval.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._server_map: dict[str, str] = {}  # tool_name -> server_name

    def register_tool(self, tool: Tool, server_name: str = "default", prefix_namespace: bool = False) -> str:
        """
        Register an MCP tool into the registry.
        
        Args:
            tool: The MCP Tool definition.
            server_name: The originating server identifier.
            prefix_namespace: If True, prefixes tool name with '{server_name}__{tool.name}'.
        
        Returns:
            The registered tool identifier name.
        """
        registered_name = f"{server_name}__{tool.name}" if prefix_namespace else tool.name
        self._tools[registered_name] = tool
        self._server_map[registered_name] = server_name
        return registered_name

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def get_server_for_tool(self, name: str) -> Optional[str]:
        return self._server_map.get(name)

    def to_ollama_format(self, tool_name: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Convert registered MCP tools to Ollama function calling format.
        
        Ollama uses:
        {
          "type": "function",
          "function": {
             "name": "...",
             "description": "...",
             "parameters": { ...JSON Schema... }
          }
        }
        """
        tools_to_convert = (
            [self._tools[tool_name]] if tool_name and tool_name in self._tools
            else list(self._tools.values())
        )

        ollama_tools = []
        for t in tools_to_convert:
            # Find the registered key for this tool
            reg_name = next((k for k, v in self._tools.items() if v == t), t.name)
            
            schema = getattr(t, "input_schema", getattr(t, "inputSchema", None)) or {"type": "object", "properties": {}}
            
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": reg_name,
                    "description": t.description or f"Tool: {reg_name}",
                    "parameters": schema,
                }
            })
        return ollama_tools

    def find_relevant_tools(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """
        Dynamic Tool Pruning / Semantic Ranking:
        When an agent has access to dozens of tools, passing all of them in the prompt:
        1. Consumes precious context tokens
        2. Increases latency
        3. Distracts the LLM, leading to hallucinations or incorrect tool selection.
        
        This ranking scores tools by relevance against the user's intent so only the
        top-k most relevant tools are exposed to the model.
        """
        stop_words = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "over", "after",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "can", "could", "will", "would", "shall", "should",
            "i", "you", "he", "she", "it", "we", "they", "what", "which", "who",
            "when", "where", "why", "how", "all", "any", "both", "each", "few",
            "more", "most", "other", "some", "such", "no", "nor", "not", "only",
            "own", "same", "so", "than", "too", "very", "just", "now", "please", "me"
        }
        raw_words = set(re.findall(r"\w+", query.lower()))
        query_words = raw_words - stop_words
        scored_tools = []

        for name, tool in self._tools.items():
            schema = getattr(tool, "input_schema", getattr(tool, "inputSchema", {})) or {}
            # Extract keywords from tool name, description, and parameter names
            text_corpus = f"{name} {tool.description or ''}"
            if "properties" in schema:
                text_corpus += " " + " ".join(schema["properties"].keys())
                for prop in schema["properties"].values():
                    if isinstance(prop, dict) and "description" in prop:
                        text_corpus += " " + prop["description"]
            
            corpus_words = set(re.findall(r"\w+", text_corpus.lower())) - stop_words
            overlap = query_words.intersection(corpus_words)
            score = len(overlap)

            # Extra weight if tool name or keyword directly appears in query
            clean_name = name.split("__")[-1]
            if clean_name in query.lower():
                score += 5
            for part in clean_name.split("_"):
                if part and len(part) > 2 and part in query_words:
                    score += 2

            scored_tools.append((score, name, tool))

        # Sort descending by score
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        top_tools = scored_tools[:top_k]

        selected = []
        for score, reg_name, tool in top_tools:
            t_schema = getattr(tool, "input_schema", getattr(tool, "inputSchema", {})) or {}
            selected.append({
                "type": "function",
                "function": {
                    "name": reg_name,
                    "description": tool.description or "",
                    "parameters": t_schema,
                },
                "_score": score,
            })
        return selected

    @property
    def all_names(self) -> list[str]:
        return list(self._tools.keys())
