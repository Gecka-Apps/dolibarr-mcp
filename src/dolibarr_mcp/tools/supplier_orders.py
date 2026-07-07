"""Supplier order (purchase order) tools."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext, LIST_PARAMS, extract_list_kwargs

_LINE_PROPS = {
    "desc": {"type": "string", "description": "Line description"},
    "qty": {"type": "number", "description": "Quantity"},
    "subprice": {"type": "number", "description": "Unit price (net / HT)"},
    "product_id": {"type": "integer", "description": "Product ID (optional)"},
    "product_type": {"type": "integer", "description": "0=Product, 1=Service", "default": 0},
    "tva_tx": {"type": "number", "description": "VAT/TGC rate (use get_vat_rates for valid values)"},
}

TOOLS: list[Tool] = [
    Tool(
        name="get_supplier_orders",
        description="Get a paginated list of supplier (purchase) orders.",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {"type": "integer", "description": "Status filter (optional)"},
                "limit": {"type": "integer", "description": "Maximum number of results (default 20)", "default": 20},
                "page": {"type": "integer", "description": "Page number", "default": 1},
                **LIST_PARAMS,
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_supplier_order_by_id",
        description="Get one supplier order by numeric ID, including its lines.",
        inputSchema={
            "type": "object",
            "properties": {"order_id": {"type": "integer", "description": "Supplier order ID"}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="create_supplier_order",
        description=(
            "Create a supplier (purchase) order. Resolve the supplier id first (search_suppliers). "
            "Lines are provided inline; there is no separate line endpoint for supplier orders."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "supplier_id": {"type": "integer", "description": "Supplier third-party ID (socid)"},
                "date": {"type": "string", "description": "Order date (YYYY-MM-DD)"},
                "lines": {
                    "type": "array",
                    "description": "Order lines",
                    "items": {"type": "object", "properties": _LINE_PROPS, "additionalProperties": True},
                },
            },
            "required": ["supplier_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="update_supplier_order",
        description="Update a supplier order header.",
        inputSchema={
            "type": "object",
            "properties": {
                "order_id": {"type": "integer", "description": "Supplier order ID"},
                "date": {"type": "string", "description": "Order date (YYYY-MM-DD)"},
                "note_public": {"type": "string", "description": "Public note"},
            },
            "required": ["order_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="delete_supplier_order",
        description="Delete a supplier order.",
        inputSchema={
            "type": "object",
            "properties": {"order_id": {"type": "integer", "description": "Supplier order ID"}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
    ),
]


async def get_supplier_orders(ctx: ToolContext):
    lk = extract_list_kwargs(ctx.arguments, ctx.config)
    return await ctx.client.get_supplier_orders(**lk, status=ctx.arguments.get("status"), properties=ctx.properties)


async def get_supplier_order_by_id(ctx: ToolContext):
    return await ctx.client.get_supplier_order_by_id(ctx.arguments["order_id"])


async def create_supplier_order(ctx: ToolContext):
    return await ctx.client.create_supplier_order(**{k: v for k, v in ctx.arguments.items() if k != "fields"})


async def update_supplier_order(ctx: ToolContext):
    args = dict(ctx.arguments)
    order_id = args.pop("order_id")
    return await ctx.client.update_supplier_order(order_id, **{k: v for k, v in args.items() if k != "fields"})


async def delete_supplier_order(ctx: ToolContext):
    return await ctx.client.delete_supplier_order(ctx.arguments["order_id"])


HANDLERS = {
    "get_supplier_orders": get_supplier_orders,
    "get_supplier_order_by_id": get_supplier_order_by_id,
    "create_supplier_order": create_supplier_order,
    "update_supplier_order": update_supplier_order,
    "delete_supplier_order": delete_supplier_order,
}
