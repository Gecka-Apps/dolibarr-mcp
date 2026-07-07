"""System and raw-access tools."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext

TOOLS: list[Tool] = [
    Tool(
        name="test_connection",
        description="Test Dolibarr API connection",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    Tool(
        name="get_status",
        description="Get Dolibarr system status and version information",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    Tool(
        name="dolibarr_raw_api",
        description=(
            "Low-level escape hatch to call any Dolibarr REST endpoint directly. "
            "Use this ONLY if there is no dedicated high-level tool available for your use case. "
            "You must pass a valid Dolibarr API path and parameters yourself; the server does not validate them. "
            "Incorrect usage can cause errors or side effects (such as creating or deleting unexpected data)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "HTTP method",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                },
                "endpoint": {
                    "type": "string",
                    "description": "Dolibarr API endpoint path (e.g. '/thirdparties', '/invoices/123'). Must be a valid existing endpoint.",
                },
                "params": {"type": "object", "description": "Query parameters"},
                "data": {"type": "object", "description": "Request payload for POST/PUT requests"},
            },
            "required": ["method", "endpoint"],
            "additionalProperties": False,
        },
    ),
]


async def test_connection(ctx: ToolContext):
    result = await ctx.client.get_status()
    if "success" not in result:
        result = {"status": "success", "message": "API connection working", "data": result}
    return result


async def get_status(ctx: ToolContext):
    return await ctx.client.get_status()


async def dolibarr_raw_api(ctx: ToolContext):
    return await ctx.client.dolibarr_raw_api(**ctx.arguments)


HANDLERS = {
    "test_connection": test_connection,
    "get_status": get_status,
    "dolibarr_raw_api": dolibarr_raw_api,
}
