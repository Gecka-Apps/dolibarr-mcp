"""Customer (third party) tools: search and CRUD."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext, DETAIL_PARAMS, LIST_PARAMS, escape_sqlfilter, extract_list_kwargs

TOOLS: list[Tool] = [
    Tool(
        name="search_customers",
        description=(
            "Search customers/third parties by name or alias. Use this whenever you need to find a customer "
            "from a name in text instead of loading a full list. Pay attention to legal suffixes and exact matches "
            "(e.g. 'GmbH' vs 'OG', 'Inc', etc.). Do not use get_customers for name-based search."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term for name or alias",
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
        name="search_suppliers",
        description=(
            "Search suppliers (third parties flagged as suppliers) by name or alias. Same as "
            "search_customers but restricted to suppliers."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term for name or alias"},
                "limit": {"type": "integer", "description": "Maximum number of results", "default": 20},
                "fields": LIST_PARAMS["fields"],
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_customers",
        description=(
            "Get an unfiltered paginated list of customers/third parties from Dolibarr. "
            "Intended for debugging or browsing only. DO NOT use this tool to search by name or alias "
            "(use the dedicated search_* tools such as search_customers instead)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of customers to return (default: 20)",
                    "default": 20,
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
        name="get_customer_by_id",
        description=(
            "Get the details of exactly one customer by numeric ID. "
            "Use this only when you already know the internal Dolibarr customer_id. "
            "Do not pass name or email here."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": "Exact numeric Dolibarr customer ID (not name).",
                },
                **DETAIL_PARAMS,
            },
            "required": ["customer_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="create_customer",
        description="Create a new customer/third party",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Customer name"},
                "email": {"type": "string", "description": "Email address"},
                "phone": {"type": "string", "description": "Phone number"},
                "address": {"type": "string", "description": "Customer address"},
                "town": {"type": "string", "description": "City/Town"},
                "zip": {"type": "string", "description": "Postal code"},
                "country_id": {
                    "type": "integer",
                    "description": "Country ID (default: 1)",
                    "default": 1,
                },
                "type": {
                    "type": "integer",
                    "description": "Customer type (1=Customer, 2=Supplier, 3=Both)",
                    "default": 1,
                },
                "status": {
                    "type": "integer",
                    "description": "Status (1=Active, 0=Inactive)",
                    "default": 1,
                },
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="update_customer",
        description="Update an existing customer",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": "Customer ID to update",
                },
                "name": {"type": "string", "description": "Customer name"},
                "email": {"type": "string", "description": "Email address"},
                "phone": {"type": "string", "description": "Phone number"},
                "address": {"type": "string", "description": "Customer address"},
                "town": {"type": "string", "description": "City/Town"},
                "zip": {"type": "string", "description": "Postal code"},
                "status": {
                    "type": "integer",
                    "description": "Status (1=Active, 0=Inactive)",
                },
            },
            "required": ["customer_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="delete_customer",
        description="Delete a customer",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": "Customer ID to delete",
                }
            },
            "required": ["customer_id"],
            "additionalProperties": False,
        },
    ),
]


async def search_customers(ctx: ToolContext):
    query = escape_sqlfilter(ctx.arguments["query"])
    limit = ctx.arguments.get("limit", 20)
    sqlfilters = f"((t.nom:like:'%{query}%') OR (t.name_alias:like:'%{query}%'))"
    return await ctx.client.search_customers(sqlfilters=sqlfilters, limit=limit, properties=ctx.properties)


async def search_suppliers(ctx: ToolContext):
    query = escape_sqlfilter(ctx.arguments["query"])
    limit = ctx.arguments.get("limit", 20)
    sqlfilters = f"((t.nom:like:'%{query}%') OR (t.name_alias:like:'%{query}%')) and (t.fournisseur:>=:1)"
    return await ctx.client.search_customers(sqlfilters=sqlfilters, limit=limit, properties=ctx.properties)


async def get_customers(ctx: ToolContext):
    lk = extract_list_kwargs(ctx.arguments, ctx.config)
    return await ctx.client.get_customers(**lk, properties=ctx.properties)


async def get_customer_by_id(ctx: ToolContext):
    return await ctx.client.get_customer_by_id(ctx.arguments["customer_id"])


async def create_customer(ctx: ToolContext):
    return await ctx.client.create_customer(**{k: v for k, v in ctx.arguments.items() if k != "fields"})


async def update_customer(ctx: ToolContext):
    args = dict(ctx.arguments)
    customer_id = args.pop("customer_id")
    return await ctx.client.update_customer(customer_id, **{k: v for k, v in args.items() if k != "fields"})


async def delete_customer(ctx: ToolContext):
    return await ctx.client.delete_customer(ctx.arguments["customer_id"])


HANDLERS = {
    "search_customers": search_customers,
    "search_suppliers": search_suppliers,
    "get_customers": get_customers,
    "get_customer_by_id": get_customer_by_id,
    "create_customer": create_customer,
    "update_customer": update_customer,
    "delete_customer": delete_customer,
}
