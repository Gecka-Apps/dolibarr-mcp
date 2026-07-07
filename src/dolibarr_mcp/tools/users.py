"""User management tools: list, detail, and CRUD."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext, DETAIL_PARAMS, LIST_PARAMS, extract_list_kwargs

TOOLS: list[Tool] = [
    Tool(
        name="get_users",
        description=(
            "Get an unfiltered paginated list of users from Dolibarr. "
            "Use this only when you explicitly need a page of users for inspection or debugging. "
            "Do not use this tool to search by name, login or email (there is no server-side filter here)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of users to return (default: 20)",
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
        name="get_user_by_id",
        description=(
            "Get the details of exactly one user by numeric ID. "
            "Use this only when you already know the internal Dolibarr user_id. "
            "Do not pass login, email or name here."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "Exact numeric Dolibarr user ID (not login, not email).",
                },
                **DETAIL_PARAMS,
            },
            "required": ["user_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="create_user",
        description="Create a new user",
        inputSchema={
            "type": "object",
            "properties": {
                "login": {"type": "string", "description": "User login"},
                "lastname": {"type": "string", "description": "Last name"},
                "firstname": {"type": "string", "description": "First name"},
                "email": {"type": "string", "description": "Email address"},
                "password": {"type": "string", "description": "Password"},
                "admin": {
                    "type": "integer",
                    "description": "Admin level (0=No, 1=Yes)",
                    "default": 0,
                },
            },
            "required": ["login", "lastname"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="update_user",
        description="Update an existing user",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "User ID to update"},
                "login": {"type": "string", "description": "User login"},
                "lastname": {"type": "string", "description": "Last name"},
                "firstname": {"type": "string", "description": "First name"},
                "email": {"type": "string", "description": "Email address"},
                "admin": {
                    "type": "integer",
                    "description": "Admin level (0=No, 1=Yes)",
                },
            },
            "required": ["user_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="delete_user",
        description="Delete a user",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "User ID to delete"}
            },
            "required": ["user_id"],
            "additionalProperties": False,
        },
    ),
]


async def get_users(ctx: ToolContext):
    lk = extract_list_kwargs(ctx.arguments, ctx.config)
    return await ctx.client.get_users(**lk, properties=ctx.properties)


async def get_user_by_id(ctx: ToolContext):
    return await ctx.client.get_user_by_id(ctx.arguments["user_id"])


async def create_user(ctx: ToolContext):
    return await ctx.client.create_user(**{k: v for k, v in ctx.arguments.items() if k != "fields"})


async def update_user(ctx: ToolContext):
    args = dict(ctx.arguments)
    user_id = args.pop("user_id")
    return await ctx.client.update_user(user_id, **{k: v for k, v in args.items() if k != "fields"})


async def delete_user(ctx: ToolContext):
    return await ctx.client.delete_user(ctx.arguments["user_id"])


HANDLERS = {
    "get_users": get_users,
    "get_user_by_id": get_user_by_id,
    "create_user": create_user,
    "update_user": update_user,
    "delete_user": delete_user,
}
