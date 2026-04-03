"""
Agent tools — each tool is a function the agent can call.
The agent loop decides when to invoke tools based on LLM tool-use output.
"""
import math
import json
from typing import Any, Dict

# ─── Tool definitions (OpenAI function-calling format) ────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": (
                "Evaluate a mathematical expression. Use for arithmetic, algebra, "
                "unit conversions, and numerical computations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A valid Python math expression, e.g. '2 ** 10 + sqrt(144)'",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for current information. Use when the user asks about "
                "recent events, news, prices, or anything that may have changed recently."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Returns the current UTC date and time.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ─── Tool implementations ──────────────────────────────────────────────────────

def _calculator(expression: str) -> str:
    """
    Safely evaluate a math expression.
    Allows only math module names — no builtins that could be dangerous.
    """
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
    allowed_names.update({"abs": abs, "round": round, "pow": pow})
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)  # noqa: S307
        return f"Result: {result}"
    except Exception as e:
        return f"Calculator error: {e}"


def _web_search(query: str) -> str:
    """
    Stub web search — in production, wire this to SerpAPI, Brave, or Tavily.
    Returns a placeholder so the agent can continue reasoning.
    """
    return (
        f"[Web search for '{query}']\n"
        "Web search is not configured. To enable it, set SERPAPI_KEY in .env "
        "and implement the actual HTTP call in app/tools/executor.py. "
        "For now, please rely on your training knowledge."
    )


def _get_current_time() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("UTC: %Y-%m-%d %H:%M:%S")


# ─── Dispatcher ───────────────────────────────────────────────────────────────

TOOL_MAP = {
    "calculator": _calculator,
    "web_search": _web_search,
    "get_current_time": _get_current_time,
}


def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Run a tool by name and return its string result."""
    fn = TOOL_MAP.get(name)
    if fn is None:
        return f"Unknown tool: {name}"
    try:
        return fn(**arguments)
    except Exception as e:
        return f"Tool execution error ({name}): {e}"
