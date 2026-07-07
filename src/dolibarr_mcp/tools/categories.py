"""Category tools: listing and label search."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext, LIST_PARAMS, escape_sqlfilter, extract_list_kwargs

TOOLS: list[Tool] = [
    Tool(
        name="get_categories",
        description=(
            "Get a list of categories, optionally filtered by type (product, customer, supplier). "
            "Use this to discover available product categories before filtering products."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["product", "customer", "supplier", "contact"],
                    "description": "Category type (default: product)",
                    "default": "product",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of categories to return (default: 50)",
                    "default": 50,
                },
                "page": {
                    "type": "integer",
                    "description": "Page number for pagination (default: 1)",
                    "default": 1,
                },
                **LIST_PARAMS,
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="search_categories",
        description=(
            "Search categories by label. Use this to find a specific product category "
            "before listing its products with get_products_by_category."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term for category label",
                },
                "type": {
                    "type": "string",
                    "enum": ["product", "customer", "supplier", "contact"],
                    "description": "Category type (default: product)",
                    "default": "product",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 20,
                },
                "fields": LIST_PARAMS["fields"],
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="link_category",
        description="Link an existing category to an object (product, customer, supplier, contact...).",
        inputSchema={
            "type": "object",
            "properties": {
                "category_id": {"type": "integer", "description": "Category ID"},
                "object_type": {
                    "type": "string",
                    "enum": ["product", "customer", "supplier", "contact", "member", "project"],
                    "description": "Type of object to tag",
                },
                "object_id": {"type": "integer", "description": "ID of the object to tag"},
            },
            "required": ["category_id", "object_type", "object_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="unlink_category",
        description="Remove a category link from an object.",
        inputSchema={
            "type": "object",
            "properties": {
                "category_id": {"type": "integer", "description": "Category ID"},
                "object_type": {
                    "type": "string",
                    "enum": ["product", "customer", "supplier", "contact", "member", "project"],
                    "description": "Type of object",
                },
                "object_id": {"type": "integer", "description": "ID of the object"},
            },
            "required": ["category_id", "object_type", "object_id"],
            "additionalProperties": False,
        },
    ),
]


async def get_categories(ctx: ToolContext):
    lk = extract_list_kwargs(ctx.arguments, ctx.config)
    return await ctx.client.get_categories(
        type=ctx.arguments.get("type", "product"), **lk, properties=ctx.properties,
    )


async def search_categories(ctx: ToolContext):
    query = escape_sqlfilter(ctx.arguments["query"])
    limit = ctx.arguments.get("limit", 20)
    sqlfilters = f"(t.label:like:'%{query}%')"
    return await ctx.client.search_categories(
        sqlfilters=sqlfilters,
        type=ctx.arguments.get("type", "product"),
        limit=limit,
        properties=ctx.properties,
    )


async def link_category(ctx: ToolContext):
    return await ctx.client.link_category(
        ctx.arguments["category_id"], ctx.arguments["object_type"], ctx.arguments["object_id"],
    )


async def unlink_category(ctx: ToolContext):
    return await ctx.client.unlink_category(
        ctx.arguments["category_id"], ctx.arguments["object_type"], ctx.arguments["object_id"],
    )


HANDLERS = {
    "get_categories": get_categories,
    "search_categories": search_categories,
    "link_category": link_category,
    "unlink_category": unlink_category,
}
