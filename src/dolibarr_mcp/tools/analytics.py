"""Analytics tools: top sellers, sales summary, low stock (direct SQL layer)."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext
from ..analytics import (
    get_top_selling_products as _top_selling,
    get_sales_summary as _sales_summary,
    get_low_stock_products as _low_stock,
)

TOOLS: list[Tool] = [
    Tool(
        name="get_top_selling_products",
        description=(
            "Get the top selling products ranked by quantity sold in invoices. "
            "Requires database connection (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD in .env). "
            "Can be filtered by category and time period."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "period_months": {
                    "type": "integer",
                    "description": "Number of months to look back (default: 12)",
                    "default": 12,
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of top products to return (default: 20)",
                    "default": 20,
                },
                "category_id": {
                    "type": "integer",
                    "description": "Optional category ID to filter products",
                },
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_sales_summary",
        description=(
            "Get a sales summary with totals grouped by month or year. "
            "Requires database connection. "
            "Shows number of invoices, customers, and revenue per period."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "period_months": {
                    "type": "integer",
                    "description": "Number of months to look back (default: 12)",
                    "default": 12,
                },
                "group_by": {
                    "type": "string",
                    "enum": ["month", "year"],
                    "description": "Group results by month or year (default: month)",
                    "default": "month",
                },
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_low_stock_products",
        description=(
            "Get products with stock at or below their alert threshold. "
            "Requires database connection. "
            "Only returns physical products (not services) that are active for sale."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of products to return (default: 20)",
                    "default": 20,
                },
                "include_zero_stock": {
                    "type": "boolean",
                    "description": "Include products with zero stock (default: true)",
                    "default": True,
                },
            },
            "additionalProperties": False,
        },
    ),
]


async def get_top_selling_products(ctx: ToolContext):
    return await _top_selling(
        ctx.config,
        period_months=ctx.arguments.get("period_months", 12),
        limit=ctx.arguments.get("limit", 20),
        category_id=ctx.arguments.get("category_id"),
    )


async def get_sales_summary(ctx: ToolContext):
    return await _sales_summary(
        ctx.config,
        period_months=ctx.arguments.get("period_months", 12),
        group_by=ctx.arguments.get("group_by", "month"),
    )


async def get_low_stock_products(ctx: ToolContext):
    return await _low_stock(
        ctx.config,
        limit=ctx.arguments.get("limit", 20),
        include_zero_stock=ctx.arguments.get("include_zero_stock", True),
    )


HANDLERS = {
    "get_top_selling_products": get_top_selling_products,
    "get_sales_summary": get_sales_summary,
    "get_low_stock_products": get_low_stock_products,
}
