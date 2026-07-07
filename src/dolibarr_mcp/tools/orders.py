"""Order tools: list and CRUD."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext, DETAIL_PARAMS, LIST_PARAMS, extract_list_kwargs

TOOLS: list[Tool] = [
    # Order Management CRUD
    Tool(
        name="get_orders",
        description=(
            "Get a paginated list of orders from Dolibarr, optionally filtered by status. "
            "Use this for overviews or reporting. Not suitable for searching specific orders by customer, project "
            "or reference (there is no server-side search here)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of orders to return (default: 20)",
                    "default": 20,
                },
                "page": {
                    "type": "integer",
                    "description": "Page number for pagination (default: 1)",
                    "default": 1,
                },
                "status": {
                    "type": "string",
                    "description": "Order status filter",
                },
                **LIST_PARAMS,
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_order_by_id",
        description=(
            "Get the details of exactly one order by numeric ID. "
            "Use this only when you already know the internal Dolibarr order_id. "
            "Do not pass order reference here."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": "Exact numeric Dolibarr order ID.",
                },
                **DETAIL_PARAMS,
            },
            "required": ["order_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="create_order",
        description=(
            "Create a new customer order. Use this only when you have already resolved the correct customer "
            "ID (socid) using search_customers or related tools. This tool does not update existing orders."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": "Customer ID (socid)",
                },
                "date": {
                    "type": "string",
                    "description": "Order date (YYYY-MM-DD)",
                },
            },
            "required": ["customer_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="update_order",
        description="Update an existing order",
        inputSchema={
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": "Order ID to update",
                },
                "date": {
                    "type": "string",
                    "description": "Order date (YYYY-MM-DD)",
                },
            },
            "required": ["order_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="delete_order",
        description="Delete an order",
        inputSchema={
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": "Order ID to delete",
                }
            },
            "required": ["order_id"],
            "additionalProperties": False,
        },
    ),
]


async def get_orders(ctx: ToolContext):
    lk = extract_list_kwargs(ctx.arguments, ctx.config)
    return await ctx.client.get_orders(**lk, status=ctx.arguments.get('status'), properties=ctx.properties)


async def get_order_by_id(ctx: ToolContext):
    return await ctx.client.get_order_by_id(ctx.arguments['order_id'])


async def create_order(ctx: ToolContext):
    return await ctx.client.create_order(**{k: v for k, v in ctx.arguments.items() if k != "fields"})


async def update_order(ctx: ToolContext):
    args = dict(ctx.arguments)
    order_id = args.pop('order_id')
    return await ctx.client.update_order(order_id, **{k: v for k, v in args.items() if k != "fields"})


async def delete_order(ctx: ToolContext):
    return await ctx.client.delete_order(ctx.arguments['order_id'])


HANDLERS = {
    "get_orders": get_orders,
    "get_order_by_id": get_order_by_id,
    "create_order": create_order,
    "update_order": update_order,
    "delete_order": delete_order,
}
