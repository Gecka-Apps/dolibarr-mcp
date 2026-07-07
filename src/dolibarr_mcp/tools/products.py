"""Product tools: search, CRUD, and category links."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext, DETAIL_PARAMS, LIST_PARAMS, escape_sqlfilter, extract_list_kwargs

TOOLS: list[Tool] = [
    Tool(
        name="search_products_by_ref",
        description=(
            "Search products by (partial) reference. Use this when a product reference appears in the text "
            "but may be incomplete or slightly uncertain. This tool returns a small, filtered list and should "
            "be preferred over get_products for any kind of lookup by reference."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ref_prefix": {"type": "string", "description": "Prefix of the product reference"},
                "limit": {"type": "integer", "description": "Maximum number of results", "default": 20},
                "fields": LIST_PARAMS["fields"],
            },
            "required": ["ref_prefix"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="search_products_by_label",
        description=(
            "Search products by label/description text. Use this when you only know the human-readable product "
            "name or part of it. Prefer this over get_products for any label-based lookup to keep result sets small."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "label_search": {"type": "string", "description": "Search term in product label"},
                "limit": {"type": "integer", "description": "Maximum number of results", "default": 20},
                "fields": LIST_PARAMS["fields"],
            },
            "required": ["label_search"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="resolve_product_ref",
        description=(
            "Resolve an exact product reference (ref) to a single product. Use this only when the exact reference "
            "string is known and you need a deterministic mapping to a product ID before creating orders or invoices. "
            "Returns a structured result with status 'ok', 'not_found', or 'ambiguous'. Do not use this for fuzzy search."
        ),
        inputSchema={
            "type": "object",
            "properties": {"ref": {"type": "string", "description": "Exact product reference"}},
            "required": ["ref"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_products",
        description=(
            "Get an unfiltered paginated list of products from Dolibarr. "
            "Intended for debugging or bulk inspection only. DO NOT use this tool to search by reference or label "
            "(use search_products_by_ref or search_products_by_label instead)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of products to return (default: 20)", "default": 20},
                "page": {"type": "integer", "description": "Page number for pagination (default: 1)", "default": 1},
                **LIST_PARAMS,
            },
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_product_by_id",
        description=(
            "Get the details of exactly one product by numeric ID. "
            "Use this only when you already know the internal Dolibarr product_id. "
            "Do not pass reference or label here."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "Exact numeric Dolibarr product ID (not ref)."},
                **DETAIL_PARAMS,
            },
            "required": ["product_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="create_product",
        description="Create a new product or service",
        inputSchema={
            "type": "object",
            "properties": {
                "ref": {"type": "string", "description": "Product reference / SKU (required by Dolibarr)"},
                "label": {"type": "string", "description": "Product name/label"},
                "type": {
                    "type": ["string", "integer"],
                    "enum": ["product", "service", 0, 1],
                    "description": "0/'product' for a physical product, 1/'service' for a service",
                },
                "price": {"type": "number", "description": "Unit price excl. tax (HT). Provide price or price_ttc."},
                "price_ttc": {"type": "number", "description": "Unit price incl. tax (TTC). Alternative to price."},
                "tva_tx": {"type": "number", "description": "VAT rate, e.g. 20.0"},
                "description": {"type": "string", "description": "Product description"},
                "stock": {"type": "integer", "description": "Initial stock quantity"},
            },
            "required": ["ref", "label", "type"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="update_product",
        description="Update an existing product",
        inputSchema={
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "Product ID to update"},
                "label": {"type": "string", "description": "Product name/label"},
                "price": {"type": "number", "description": "Product price"},
                "description": {"type": "string", "description": "Product description"},
            },
            "required": ["product_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="delete_product",
        description="Delete a product",
        inputSchema={
            "type": "object",
            "properties": {"product_id": {"type": "integer", "description": "Product ID to delete"}},
            "required": ["product_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_products_by_category",
        description=(
            "Get all products belonging to a specific category. "
            "Use get_categories or search_categories first to find the category ID."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "category_id": {"type": "integer", "description": "Category ID"},
                "limit": {"type": "integer", "description": "Maximum number of products to return (default: 50)", "default": 50},
                "fields": LIST_PARAMS["fields"],
            },
            "required": ["category_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_product_categories",
        description="Get the list of categories assigned to a specific product.",
        inputSchema={
            "type": "object",
            "properties": {"product_id": {"type": "integer", "description": "Product ID"}},
            "required": ["product_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_product_purchase_prices",
        description="List the supplier (purchase) prices configured for a product.",
        inputSchema={
            "type": "object",
            "properties": {"product_id": {"type": "integer", "description": "Product ID"}},
            "required": ["product_id"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="add_product_purchase_price",
        description="Add a supplier price tier to a product. supplier_ref (the supplier's SKU) is required by Dolibarr.",
        inputSchema={
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "Product ID"},
                "supplier_id": {"type": "integer", "description": "Supplier third-party ID (fourn_id)"},
                "price": {"type": "number", "description": "Purchase price"},
                "supplier_ref": {"type": "string", "description": "Supplier reference / SKU (ref_fourn)"},
                "qty": {"type": "number", "description": "Quantity tier (default 1)", "default": 1},
                "tva_tx": {"type": "number", "description": "VAT/TGC rate (default 0)"},
                "price_base_type": {"type": "string", "enum": ["HT", "TTC"], "description": "Price base (default HT)"},
                "availability": {"type": "integer", "description": "Availability delay id (optional)"},
            },
            "required": ["product_id", "supplier_id", "price", "supplier_ref"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="delete_product_purchase_price",
        description="Delete a supplier price tier from a product.",
        inputSchema={
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "Product ID"},
                "price_id": {"type": "integer", "description": "Purchase price entry ID"},
            },
            "required": ["product_id", "price_id"],
            "additionalProperties": False,
        },
    ),
]


async def search_products_by_ref(ctx: ToolContext):
    ref_prefix = escape_sqlfilter(ctx.arguments["ref_prefix"])
    limit = ctx.arguments.get("limit", 20)
    sqlfilters = f"(t.ref:like:'{ref_prefix}%')"
    return await ctx.client.search_products(sqlfilters=sqlfilters, limit=limit, properties=ctx.properties)


async def search_products_by_label(ctx: ToolContext):
    label_search = escape_sqlfilter(ctx.arguments["label_search"])
    limit = ctx.arguments.get("limit", 20)
    sqlfilters = f"(t.label:like:'%{label_search}%')"
    return await ctx.client.search_products(sqlfilters=sqlfilters, limit=limit, properties=ctx.properties)


async def resolve_product_ref(ctx: ToolContext):
    ref = ctx.arguments["ref"]
    sqlfilters = f"(t.ref:like:'{escape_sqlfilter(ref)}')"
    products = await ctx.client.search_products(sqlfilters=sqlfilters, limit=2)

    if not products:
        return {"status": "not_found", "message": f"Product with ref '{ref}' not found"}
    if len(products) == 1:
        return {"status": "ok", "product": products[0]}
    exact_matches = [p for p in products if p.get("ref") == ref]
    if len(exact_matches) == 1:
        return {"status": "ok", "product": exact_matches[0]}
    return {"status": "ambiguous", "message": f"Multiple products found for ref '{ref}'", "products": products}


async def get_products(ctx: ToolContext):
    lk = extract_list_kwargs(ctx.arguments, ctx.config)
    return await ctx.client.get_products(**lk, properties=ctx.properties)


async def get_product_by_id(ctx: ToolContext):
    return await ctx.client.get_product_by_id(ctx.arguments["product_id"])


async def create_product(ctx: ToolContext):
    return await ctx.client.create_product(**{k: v for k, v in ctx.arguments.items() if k != "fields"})


async def update_product(ctx: ToolContext):
    args = dict(ctx.arguments)
    product_id = args.pop("product_id")
    return await ctx.client.update_product(product_id, **{k: v for k, v in args.items() if k != "fields"})


async def delete_product(ctx: ToolContext):
    return await ctx.client.delete_product(ctx.arguments["product_id"])


async def get_products_by_category(ctx: ToolContext):
    return await ctx.client.get_products_by_category(
        category_id=ctx.arguments["category_id"],
        limit=ctx.arguments.get("limit", 50),
        properties=ctx.properties,
    )


async def get_product_categories(ctx: ToolContext):
    return await ctx.client.get_product_categories(ctx.arguments["product_id"])


async def get_product_purchase_prices(ctx: ToolContext):
    return await ctx.client.get_product_purchase_prices(ctx.arguments["product_id"])


async def add_product_purchase_price(ctx: ToolContext):
    args = dict(ctx.arguments)
    product_id = args.pop("product_id")
    return await ctx.client.add_product_purchase_price(product_id, **{k: v for k, v in args.items() if k != "fields"})


async def delete_product_purchase_price(ctx: ToolContext):
    return await ctx.client.delete_product_purchase_price(ctx.arguments["product_id"], ctx.arguments["price_id"])


HANDLERS = {
    "search_products_by_ref": search_products_by_ref,
    "search_products_by_label": search_products_by_label,
    "resolve_product_ref": resolve_product_ref,
    "get_products": get_products,
    "get_product_by_id": get_product_by_id,
    "create_product": create_product,
    "update_product": update_product,
    "delete_product": delete_product,
    "get_products_by_category": get_products_by_category,
    "get_product_categories": get_product_categories,
    "get_product_purchase_prices": get_product_purchase_prices,
    "add_product_purchase_price": add_product_purchase_price,
    "delete_product_purchase_price": delete_product_purchase_price,
}
