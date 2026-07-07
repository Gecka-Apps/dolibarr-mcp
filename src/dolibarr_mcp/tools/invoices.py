"""Invoice tools: CRUD, line operations, project linking, and validation."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext, DETAIL_PARAMS, LIST_PARAMS, extract_list_kwargs

TOOLS: list[Tool] = [
    # Invoice Management CRUD
    Tool(
        name="get_invoices",
        description=(
            "Get a paginated list of invoices from Dolibarr, optionally filtered by status. "
            "Use this only if you really need a list of many invoices (e.g. overviews, reports). "
            "Do not use this as a search-by-customer or search-by-reference tool."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of invoices to return (default: 20)",
                    "default": 20,
                },
                "page": {
                    "type": "integer",
                    "description": "Page number for pagination (default: 1)",
                    "default": 1,
                },
                "status": {
                    "type": "string",
                    "description": "Invoice status filter (draft, unpaid, paid, etc.)",
                },
                **LIST_PARAMS,
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_invoice_by_id",
        description=(
            "Get the details of exactly one invoice by numeric ID, including line items. "
            "Use this only when you already know the internal Dolibarr invoice_id. "
            "Do not pass invoice reference here."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "description": "Exact numeric Dolibarr invoice ID.",
                },
                **DETAIL_PARAMS,
            },
            "required": ["invoice_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="create_invoice",
        description=(
            "ALWAYS creates a new invoice. Do not use this tool to modify an existing invoice. "
            "Before calling this, resolve the correct customer and product IDs using the appropriate search_* tools "
            "(e.g. search_customers, search_products_by_ref, resolve_product_ref). "
            "For lines: Use product_id for existing products whenever possible and set product_type=0 for goods "
            "and product_type=1 for services. Use free-text lines only if no matching product exists in Dolibarr."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": "Customer ID (Dolibarr socid of the third party to invoice)",
                },
                "date": {
                    "type": "string",
                    "description": "Invoice date (YYYY-MM-DD)",
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date (YYYY-MM-DD)",
                },
                "lines": {
                    "type": "array",
                    "description": "Invoice lines",
                    "items": {
                        "type": "object",
                        "properties": {
                            "desc": {
                                "type": "string",
                                "description": "Line description",
                            },
                            "qty": {"type": "number", "description": "Quantity"},
                            "subprice": {
                                "type": "number",
                                "description": "Unit price",
                            },
                            "total_ht": {
                                "type": "number",
                                "description": "Total excluding tax",
                            },
                            "total_ttc": {
                                "type": "number",
                                "description": "Total including tax",
                            },
                            "tva_tx": {"type": "number", "description": "VAT/TGC rate from the tax dictionary (use get_vat_rates for valid values)"},
                            "product_id": {
                                "type": "integer",
                                "description": "Product ID to link (optional)",
                            },
                            "product_type": {
                                "type": "integer",
                                "description": "Type of line (0=Product, 1=Service)",
                            },
                        },
                        "required": ["desc", "qty", "subprice"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["customer_id", "lines"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="update_invoice",
        description="Update an existing invoice",
        inputSchema={
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "description": "Invoice ID to update",
                },
                "date": {
                    "type": "string",
                    "description": "Invoice date (YYYY-MM-DD)",
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date (YYYY-MM-DD)",
                },
            },
            "required": ["invoice_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="delete_invoice",
        description="Delete an invoice",
        inputSchema={
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "description": "Invoice ID to delete",
                }
            },
            "required": ["invoice_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="create_invoice_draft",
        description=(
            "Create a new invoice draft (header only). "
            "Use this to start a new invoice, then use add_invoice_line to add items. "
            "Returns the new invoice_id."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": "Customer ID (Dolibarr socid)",
                },
                "date": {
                    "type": "string",
                    "description": "Invoice date (YYYY-MM-DD)",
                },
                "project_id": {
                    "type": "integer",
                    "description": "Linked project ID (optional)",
                },
            },
            "required": ["customer_id", "date"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="add_invoice_line",
        description="Add a line item to an existing draft invoice.",
        inputSchema={
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "description": "Invoice ID",
                },
                "desc": {
                    "type": "string",
                    "description": "Line description",
                },
                "qty": {
                    "type": "number",
                    "description": "Quantity",
                },
                "subprice": {
                    "type": "number",
                    "description": "Unit price (net)",
                },
                "product_id": {
                    "type": "integer",
                    "description": "Product ID (optional)",
                },
                "product_type": {
                    "type": "integer",
                    "description": "Type (0=Product, 1=Service)",
                    "default": 0,
                },
                "tva_tx": {
                    "type": "number",
                    "description": "VAT/TGC rate from the tax dictionary (optional; use get_vat_rates for valid values)",
                },
            },
            "required": ["invoice_id", "desc", "qty", "subprice"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="update_invoice_line",
        description="Update an existing line in a draft invoice.",
        inputSchema={
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "description": "Invoice ID",
                },
                "line_id": {
                    "type": "integer",
                    "description": "Line ID to update",
                },
                "desc": {
                    "type": "string",
                    "description": "New description",
                },
                "qty": {
                    "type": "number",
                    "description": "New quantity",
                },
                "subprice": {
                    "type": "number",
                    "description": "New unit price",
                },
                "tva_tx": {
                    "type": "number",
                    "description": "New VAT/TGC rate from the tax dictionary (use get_vat_rates for valid values)",
                },
            },
            "required": ["invoice_id", "line_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="delete_invoice_line",
        description="Delete a line from a draft invoice.",
        inputSchema={
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "description": "Invoice ID",
                },
                "line_id": {
                    "type": "integer",
                    "description": "Line ID to delete",
                },
            },
            "required": ["invoice_id", "line_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="set_invoice_project",
        description="Link an invoice to a project.",
        inputSchema={
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "description": "Invoice ID",
                },
                "project_id": {
                    "type": "integer",
                    "description": "Project ID",
                },
            },
            "required": ["invoice_id", "project_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="validate_invoice",
        description="Validate a draft invoice (change status to unpaid).",
        inputSchema={
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "description": "Invoice ID",
                },
                "warehouse_id": {
                    "type": "integer",
                    "description": "Warehouse ID for stock decrease (optional)",
                    "default": 0,
                },
            },
            "required": ["invoice_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="search_invoices",
        description=(
            "Search invoices by customer and/or status, server-side filtered. Prefer this over "
            "get_invoices when looking for a specific customer's invoices or a given status."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "Customer ID (Dolibarr socid) to filter by"},
                "status": {
                    "type": "integer",
                    "enum": [0, 1, 2, 3],
                    "description": "Invoice status: 0=draft, 1=unpaid/validated, 2=paid, 3=abandoned",
                },
                "limit": {"type": "integer", "description": "Maximum number of results (default 20)", "default": 20},
                "fields": {"type": "string", "description": "Comma-separated fields to return"},
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="set_invoice_to_draft",
        description="Revert a validated invoice back to draft so its lines can be edited, then re-validated.",
        inputSchema={
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer", "description": "Invoice ID"},
                "idwarehouse": {
                    "type": "integer",
                    "description": "Warehouse for stock movement; -1 (default) means no stock movement",
                    "default": -1,
                },
            },
            "required": ["invoice_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="add_payment_to_invoice",
        description=(
            "Register a payment for the full remaining amount of an invoice. The bank account and "
            "payment mode are resolved automatically when omitted (single bank account, wire-transfer "
            "mode); if the choice is ambiguous the tool returns an error listing the options."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer", "description": "Invoice ID"},
                "date": {"type": "string", "description": "Payment date (YYYY-MM-DD)"},
                "payment_mode_id": {"type": "integer", "description": "Payment type id (optional; defaults to wire transfer)"},
                "account_id": {"type": "integer", "description": "Bank account id (optional; defaults to the single configured account)"},
                "num_payment": {"type": "string", "description": "Payment reference/number (optional)"},
                "close_paid": {"type": "boolean", "description": "Mark the invoice as paid if fully covered (default true)", "default": True},
            },
            "required": ["invoice_id", "date"],
            "additionalProperties": False,
        },
    ),
]


async def get_invoices(ctx: ToolContext):
    lk = extract_list_kwargs(ctx.arguments, ctx.config)
    return await ctx.client.get_invoices(**lk, status=ctx.arguments.get('status'), properties=ctx.properties)


async def get_invoice_by_id(ctx: ToolContext):
    return await ctx.client.get_invoice_by_id(ctx.arguments['invoice_id'])


async def create_invoice(ctx: ToolContext):
    return await ctx.client.create_invoice(**{k: v for k, v in ctx.arguments.items() if k != "fields"})


async def update_invoice(ctx: ToolContext):
    args = dict(ctx.arguments)
    invoice_id = args.pop('invoice_id')
    return await ctx.client.update_invoice(invoice_id, **{k: v for k, v in args.items() if k != "fields"})


async def delete_invoice(ctx: ToolContext):
    return await ctx.client.delete_invoice(ctx.arguments['invoice_id'])


async def create_invoice_draft(ctx: ToolContext):
    args = dict(ctx.arguments)
    if "customer_id" in args:
        args["socid"] = args.pop("customer_id")
    if "project_id" in args:
        args["fk_project"] = args.pop("project_id")
    return await ctx.client.create_invoice(**{k: v for k, v in args.items() if k != "fields"})


async def add_invoice_line(ctx: ToolContext):
    args = dict(ctx.arguments)
    invoice_id = args.pop("invoice_id")
    return await ctx.client.add_invoice_line(invoice_id, **{k: v for k, v in args.items() if k != "fields"})


async def update_invoice_line(ctx: ToolContext):
    args = dict(ctx.arguments)
    invoice_id = args.pop("invoice_id")
    line_id = args.pop("line_id")
    return await ctx.client.update_invoice_line(invoice_id, line_id, **{k: v for k, v in args.items() if k != "fields"})


async def delete_invoice_line(ctx: ToolContext):
    args = dict(ctx.arguments)
    invoice_id = args.pop("invoice_id")
    line_id = args.pop("line_id")
    return await ctx.client.delete_invoice_line(invoice_id, line_id)


async def set_invoice_project(ctx: ToolContext):
    args = dict(ctx.arguments)
    invoice_id = args.pop("invoice_id")
    project_id = args.pop("project_id")
    return await ctx.client.update_invoice(invoice_id, fk_project=project_id)


async def validate_invoice(ctx: ToolContext):
    args = dict(ctx.arguments)
    invoice_id = args.pop("invoice_id")
    return await ctx.client.validate_invoice(invoice_id, **{k: v for k, v in args.items() if k != "fields"})


async def search_invoices(ctx: ToolContext):
    return await ctx.client.search_invoices(
        customer_id=ctx.arguments.get("customer_id"),
        status=ctx.arguments.get("status"),
        limit=ctx.arguments.get("limit", 20),
        properties=ctx.properties,
    )


async def set_invoice_to_draft(ctx: ToolContext):
    args = dict(ctx.arguments)
    invoice_id = args.pop("invoice_id")
    return await ctx.client.set_invoice_to_draft(invoice_id, **{k: v for k, v in args.items() if k != "fields"})


async def add_payment_to_invoice(ctx: ToolContext):
    args = dict(ctx.arguments)
    invoice_id = args.pop("invoice_id")
    return await ctx.client.add_payment_to_invoice(invoice_id, **{k: v for k, v in args.items() if k != "fields"})


HANDLERS = {
    "get_invoices": get_invoices,
    "get_invoice_by_id": get_invoice_by_id,
    "create_invoice": create_invoice,
    "update_invoice": update_invoice,
    "delete_invoice": delete_invoice,
    "create_invoice_draft": create_invoice_draft,
    "add_invoice_line": add_invoice_line,
    "update_invoice_line": update_invoice_line,
    "delete_invoice_line": delete_invoice_line,
    "set_invoice_project": set_invoice_project,
    "validate_invoice": validate_invoice,
    "search_invoices": search_invoices,
    "set_invoice_to_draft": set_invoice_to_draft,
    "add_payment_to_invoice": add_payment_to_invoice,
}
