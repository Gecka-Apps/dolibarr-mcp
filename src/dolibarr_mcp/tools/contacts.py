"""Contact tools: list, detail, and CRUD."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext, DETAIL_PARAMS, LIST_PARAMS, extract_list_kwargs

TOOLS: list[Tool] = [
    Tool(
        name="get_contacts",
        description=(
            "Get a paginated list of contacts from Dolibarr. "
            "Use this only if you need a generic list of contacts. "
            "Do not treat this as a name search; if you need search-by-name, a dedicated search tool should be used."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of contacts to return (default: 20)",
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
        name="get_contact_by_id",
        description=(
            "Get the details of exactly one contact by numeric ID. "
            "Use this only when you already know the internal Dolibarr contact_id. "
            "Do not pass name or email here."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "integer",
                    "description": "Exact numeric Dolibarr contact ID.",
                },
                **DETAIL_PARAMS,
            },
            "required": ["contact_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="create_contact",
        description="Create a new contact",
        inputSchema={
            "type": "object",
            "properties": {
                "firstname": {"type": "string", "description": "First name"},
                "lastname": {"type": "string", "description": "Last name"},
                "email": {"type": "string", "description": "Email address"},
                "phone": {"type": "string", "description": "Phone number"},
                "socid": {
                    "type": "integer",
                    "description": "Associated company ID (thirdparty socid)",
                },
            },
            "required": ["firstname", "lastname"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="update_contact",
        description="Update an existing contact",
        inputSchema={
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "integer",
                    "description": "Contact ID to update",
                },
                "firstname": {"type": "string", "description": "First name"},
                "lastname": {"type": "string", "description": "Last name"},
                "email": {"type": "string", "description": "Email address"},
                "phone": {"type": "string", "description": "Phone number"},
            },
            "required": ["contact_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="delete_contact",
        description="Delete a contact",
        inputSchema={
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "integer",
                    "description": "Contact ID to delete",
                }
            },
            "required": ["contact_id"],
            "additionalProperties": False,
        },
    ),
]


async def get_contacts(ctx: ToolContext):
    lk = extract_list_kwargs(ctx.arguments, ctx.config)
    return await ctx.client.get_contacts(**lk, properties=ctx.properties)


async def get_contact_by_id(ctx: ToolContext):
    return await ctx.client.get_contact_by_id(ctx.arguments["contact_id"])


async def create_contact(ctx: ToolContext):
    return await ctx.client.create_contact(**{k: v for k, v in ctx.arguments.items() if k != "fields"})


async def update_contact(ctx: ToolContext):
    args = dict(ctx.arguments)
    contact_id = args.pop("contact_id")
    return await ctx.client.update_contact(contact_id, **{k: v for k, v in args.items() if k != "fields"})


async def delete_contact(ctx: ToolContext):
    return await ctx.client.delete_contact(ctx.arguments["contact_id"])


HANDLERS = {
    "get_contacts": get_contacts,
    "get_contact_by_id": get_contact_by_id,
    "create_contact": create_contact,
    "update_contact": update_contact,
    "delete_contact": delete_contact,
}
