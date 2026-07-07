"""Proposal (quote / devis) tools: lifecycle create -> validate -> sign -> convert."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext, DETAIL_PARAMS, LIST_PARAMS, extract_list_kwargs

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
        name="get_proposals",
        description="Get a paginated list of proposals (quotes). Use search_customers/get_customer_by_id to resolve a customer first.",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "integer",
                    "enum": [0, 1, 2, 3, 4],
                    "description": "0=draft, 1=open/validated, 2=signed, 3=declined, 4=billed",
                },
                "limit": {"type": "integer", "description": "Maximum number of results (default 20)", "default": 20},
                "page": {"type": "integer", "description": "Page number for pagination", "default": 1},
                **LIST_PARAMS,
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_proposal_by_id",
        description="Get one proposal by numeric ID, including its lines.",
        inputSchema={
            "type": "object",
            "properties": {
                "proposal_id": {"type": "integer", "description": "Proposal ID"},
                **DETAIL_PARAMS,
            },
            "required": ["proposal_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="create_proposal",
        description=(
            "Create a draft proposal (quote). Resolve the customer id first. Lines can be passed "
            "inline or added afterwards with add_proposal_line."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "Customer ID (Dolibarr socid)"},
                "date": {"type": "string", "description": "Proposal date (YYYY-MM-DD)"},
                "project_id": {"type": "integer", "description": "Linked project ID (optional)"},
                "payment_mode_id": {"type": "integer", "description": "Payment mode ID (optional)"},
                "note_public": {"type": "string", "description": "Public note (optional)"},
                "lines": {
                    "type": "array",
                    "description": "Proposal lines (optional)",
                    "items": {"type": "object", "properties": _LINE_PROPS, "additionalProperties": True},
                },
            },
            "required": ["customer_id", "date"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="update_proposal",
        description="Update a draft proposal header (date, project, note). Only draft proposals can be edited.",
        inputSchema={
            "type": "object",
            "properties": {
                "proposal_id": {"type": "integer", "description": "Proposal ID"},
                "date": {"type": "string", "description": "Proposal date (YYYY-MM-DD)"},
                "project_id": {"type": "integer", "description": "Linked project ID"},
                "note_public": {"type": "string", "description": "Public note"},
            },
            "required": ["proposal_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="delete_proposal",
        description="Delete a proposal.",
        inputSchema={
            "type": "object",
            "properties": {"proposal_id": {"type": "integer", "description": "Proposal ID"}},
            "required": ["proposal_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="add_proposal_line",
        description="Add a line to a draft proposal.",
        inputSchema={
            "type": "object",
            "properties": {
                "proposal_id": {"type": "integer", "description": "Proposal ID"},
                **_LINE_PROPS,
                "rang": {"type": "integer", "description": "Line order/position (optional)"},
            },
            "required": ["proposal_id", "desc", "qty", "subprice"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="update_proposal_line",
        description="Update a line in a draft proposal (unprovided fields are preserved).",
        inputSchema={
            "type": "object",
            "properties": {
                "proposal_id": {"type": "integer", "description": "Proposal ID"},
                "line_id": {"type": "integer", "description": "Proposal line ID"},
                **_LINE_PROPS,
            },
            "required": ["proposal_id", "line_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="delete_proposal_line",
        description="Delete a line from a draft proposal.",
        inputSchema={
            "type": "object",
            "properties": {
                "proposal_id": {"type": "integer", "description": "Proposal ID"},
                "line_id": {"type": "integer", "description": "Proposal line ID"},
            },
            "required": ["proposal_id", "line_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="validate_proposal",
        description="Validate a draft proposal (assigns its ref and opens it).",
        inputSchema={
            "type": "object",
            "properties": {"proposal_id": {"type": "integer", "description": "Proposal ID"}},
            "required": ["proposal_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="sign_proposal",
        description="Sign an open proposal (mark it accepted by the customer).",
        inputSchema={
            "type": "object",
            "properties": {
                "proposal_id": {"type": "integer", "description": "Proposal ID"},
                "note": {"type": "string", "description": "Optional private note recorded on signing"},
            },
            "required": ["proposal_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="convert_proposal_to_order",
        description="Convert a signed proposal into a customer order; returns the new order id.",
        inputSchema={
            "type": "object",
            "properties": {"proposal_id": {"type": "integer", "description": "Proposal ID"}},
            "required": ["proposal_id"],
            "additionalProperties": False,
        },
    ),
]


async def get_proposals(ctx: ToolContext):
    lk = extract_list_kwargs(ctx.arguments, ctx.config)
    return await ctx.client.get_proposals(**lk, status=ctx.arguments.get("status"), properties=ctx.properties)


async def get_proposal_by_id(ctx: ToolContext):
    return await ctx.client.get_proposal_by_id(ctx.arguments["proposal_id"])


async def create_proposal(ctx: ToolContext):
    return await ctx.client.create_proposal(**{k: v for k, v in ctx.arguments.items() if k != "fields"})


async def update_proposal(ctx: ToolContext):
    args = dict(ctx.arguments)
    proposal_id = args.pop("proposal_id")
    return await ctx.client.update_proposal(proposal_id, **{k: v for k, v in args.items() if k != "fields"})


async def delete_proposal(ctx: ToolContext):
    return await ctx.client.delete_proposal(ctx.arguments["proposal_id"])


async def add_proposal_line(ctx: ToolContext):
    args = dict(ctx.arguments)
    proposal_id = args.pop("proposal_id")
    return await ctx.client.add_proposal_line(proposal_id, **{k: v for k, v in args.items() if k != "fields"})


async def update_proposal_line(ctx: ToolContext):
    args = dict(ctx.arguments)
    proposal_id = args.pop("proposal_id")
    line_id = args.pop("line_id")
    return await ctx.client.update_proposal_line(proposal_id, line_id, **{k: v for k, v in args.items() if k != "fields"})


async def delete_proposal_line(ctx: ToolContext):
    return await ctx.client.delete_proposal_line(ctx.arguments["proposal_id"], ctx.arguments["line_id"])


async def validate_proposal(ctx: ToolContext):
    return await ctx.client.validate_proposal(ctx.arguments["proposal_id"])


async def sign_proposal(ctx: ToolContext):
    return await ctx.client.sign_proposal(ctx.arguments["proposal_id"], note=ctx.arguments.get("note"))


async def convert_proposal_to_order(ctx: ToolContext):
    return await ctx.client.convert_proposal_to_order(ctx.arguments["proposal_id"])


HANDLERS = {
    "get_proposals": get_proposals,
    "get_proposal_by_id": get_proposal_by_id,
    "create_proposal": create_proposal,
    "update_proposal": update_proposal,
    "delete_proposal": delete_proposal,
    "add_proposal_line": add_proposal_line,
    "update_proposal_line": update_proposal_line,
    "delete_proposal_line": delete_proposal_line,
    "validate_proposal": validate_proposal,
    "sign_proposal": sign_proposal,
    "convert_proposal_to_order": convert_proposal_to_order,
}
