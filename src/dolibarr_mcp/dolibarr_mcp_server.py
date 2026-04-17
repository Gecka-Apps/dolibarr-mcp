"""Professional Dolibarr MCP Server with comprehensive CRUD operations."""

import asyncio
import json
import sys
import logging
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

# Import MCP components
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool, TextContent

# Import our Dolibarr components
from .config import Config
from .dolibarr_client import DolibarrClient, DolibarrAPIError
from .response_shaper import format_response, get_properties_param, TOOL_RESPONSE_CONFIG
from .analytics import (
    get_top_selling_products,
    get_sales_summary,
    get_low_stock_products,
    AnalyticsUnavailableError,
)

# HTTP transport imports
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.routing import Route
from starlette.types import Receive, Scope, Send
import uvicorn


# Configure logging to stderr so it doesn't interfere with MCP protocol
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise in MCP communication
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)

# Create server instance
server = Server("dolibarr-mcp")


def _escape_sqlfilter(value: str) -> str:
    """Escape single quotes for SQL filters."""
    return value.replace("'", "''")


# Common schema fragments injected into list/search/detail tool schemas.
_LIST_PARAMS = {
    "fields": {
        "type": "string",
        "description": "Comma-separated list of fields to return (e.g. 'id,ref,label,price'). Default: optimized summary set.",
    },
    "sortfield": {
        "type": "string",
        "description": "Field to sort by (e.g. 'date', 'ref', 'total_ttc')",
    },
    "sortorder": {
        "type": "string",
        "enum": ["ASC", "DESC"],
        "description": "Sort direction (default: ASC)",
    },
}

_DETAIL_PARAMS = {
    "fields": {
        "type": "string",
        "description": "Comma-separated fields to return. Default: all fields.",
    },
}


@server.list_tools()
async def handle_list_tools():
    """List all available tools."""
    return [
        # System & Info
        Tool(
            name="test_connection",
            description="Test Dolibarr API connection",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        Tool(
            name="get_status",
            description="Get Dolibarr system status and version information",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),

        # Search Tools
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
                    "ref_prefix": {
                        "type": "string",
                        "description": "Prefix of the product reference",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 20,
                    },
                    "fields": _LIST_PARAMS["fields"],
                },
                "required": ["ref_prefix"],
                "additionalProperties": False,
            },
        ),
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
                    "fields": _LIST_PARAMS["fields"],
                },
                "required": ["query"],
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
                    "label_search": {
                        "type": "string",
                        "description": "Search term in product label",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 20,
                    },
                    "fields": _LIST_PARAMS["fields"],
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
                "properties": {
                    "ref": {"type": "string", "description": "Exact product reference"}
                },
                "required": ["ref"],
                "additionalProperties": False,
            },
        ),

        # User Management CRUD
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
                    **_LIST_PARAMS,
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
                    **_DETAIL_PARAMS,
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

        # Customer/Third Party Management CRUD
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
                    **_LIST_PARAMS,
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
                    **_DETAIL_PARAMS,
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

        # Product Management CRUD
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
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of products to return (default: 20)",
                        "default": 20,
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination (default: 1)",
                        "default": 1,
                    },
                    **_LIST_PARAMS,
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
                    "product_id": {
                        "type": "integer",
                        "description": "Exact numeric Dolibarr product ID (not ref).",
                    },
                    **_DETAIL_PARAMS,
                },
                "required": ["product_id"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="create_product",
            description="Create a new product",
            inputSchema={
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "Product name/label"},
                    "price": {"type": "number", "description": "Product price"},
                    "description": {"type": "string", "description": "Product description"},
                    "stock": {
                        "type": "integer",
                        "description": "Initial stock quantity",
                    },
                },
                "required": ["label", "price"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="update_product",
            description="Update an existing product",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Product ID to update",
                    },
                    "label": {"type": "string", "description": "Product name/label"},
                    "price": {"type": "number", "description": "Product price"},
                    "description": {
                        "type": "string",
                        "description": "Product description",
                    },
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
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Product ID to delete",
                    }
                },
                "required": ["product_id"],
                "additionalProperties": False,
            },
        ),

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
                    **_LIST_PARAMS,
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
                    **_DETAIL_PARAMS,
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
                                "vat": {"type": "number", "description": "VAT rate"},
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
                    "vat": {
                        "type": "number",
                        "description": "VAT rate (optional)",
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
                    "vat": {
                        "type": "number",
                        "description": "New VAT rate",
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
                    **_LIST_PARAMS,
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
                    **_DETAIL_PARAMS,
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

        # Contact Management CRUD
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
                    **_LIST_PARAMS,
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
                    **_DETAIL_PARAMS,
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

        # Project Management CRUD
        Tool(
            name="get_projects",
            description=(
                "Get a paginated list of projects from Dolibarr, optionally filtered by status. "
                "Use this for overviews or when you need to iterate through project pages. "
                "Do not use this to search for a project by name or reference (use search_projects instead)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of projects to return (default: 20)",
                        "default": 20,
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination (default: 1)",
                        "default": 1,
                    },
                    "status": {
                        "type": "integer",
                        "description": "Project status filter (e.g. 0=draft, 1=open, 2=closed)",
                        "default": 1,
                    },
                    **_LIST_PARAMS,
                },
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_project_by_id",
            description=(
                "Get the details of exactly one project by numeric ID. "
                "Use this only when you already know the internal Dolibarr project_id. "
                "Do not pass project reference here."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Exact numeric Dolibarr project ID.",
                    },
                    **_DETAIL_PARAMS,
                },
                "required": ["project_id"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="search_projects",
            description=(
                "Search projects by reference or title. Use this when you have a partial or full project ref/title "
                "and need to find matching projects without loading full project lists."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term for project ref or title",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 20,
                    },
                    "fields": _LIST_PARAMS["fields"],
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="create_project",
            description="Create a new project",
            inputSchema={
                "type": "object",
                "properties": {
                    "ref": {
                        "type": "string",
                        "description": "Project reference (optional, if Dolibarr auto-generates)",
                    },
                    "title": {"type": "string", "description": "Project title"},
                    "description": {
                        "type": "string",
                        "description": "Project description",
                    },
                    "socid": {
                        "type": "integer",
                        "description": "Linked customer ID (thirdparty)",
                    },
                    "status": {
                        "type": "integer",
                        "description": "Project status (e.g. 1=open)",
                        "default": 1,
                    },
                },
                "required": ["title"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="update_project",
            description="Update an existing project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID to update",
                    },
                    "title": {"type": "string", "description": "Project title"},
                    "description": {
                        "type": "string",
                        "description": "Project description",
                    },
                    "status": {
                        "type": "integer",
                        "description": "Project status",
                    },
                },
                "required": ["project_id"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="delete_project",
            description="Delete a project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID to delete",
                    }
                },
                "required": ["project_id"],
                "additionalProperties": False,
            },
        ),

        # Category Management
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
                    **_LIST_PARAMS,
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
                    "fields": _LIST_PARAMS["fields"],
                },
                "required": ["query"],
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
                    "category_id": {
                        "type": "integer",
                        "description": "Category ID",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of products to return (default: 50)",
                        "default": 50,
                    },
                    "fields": _LIST_PARAMS["fields"],
                },
                "required": ["category_id"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_product_categories",
            description=(
                "Get the list of categories assigned to a specific product."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "Product ID",
                    },
                },
                "required": ["product_id"],
                "additionalProperties": False,
            },
        ),

        # Analytics (requires database connection)
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

        # Raw API Access
        Tool(
            name="dolibarr_raw_api",
            description=(
                "Low-level escape hatch to call any Dolibarr REST endpoint directly. "
                "Use this ONLY if there is no dedicated high-level tool available for your use case. "
                "You must pass a valid Dolibarr API path and parameters yourself; the server does not validate them. "
                "Incorrect usage can cause errors or side effects (such as creating or deleting unexpected data)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                    },
                    "endpoint": {
                        "type": "string",
                        "description": "Dolibarr API endpoint path (e.g. '/thirdparties', '/invoices/123'). Must be a valid existing endpoint.",
                    },
                    "params": {
                        "type": "object",
                        "description": "Query parameters",
                    },
                    "data": {
                        "type": "object",
                        "description": "Request payload for POST/PUT requests",
                    },
                },
                "required": ["method", "endpoint"],
                "additionalProperties": False,
            },
        ),
    ]


def _extract_list_kwargs(arguments: dict, config: Config) -> dict:
    """Extract common list/search parameters from tool arguments."""
    kwargs = {}
    limit = arguments.get("limit", config.default_list_limit)
    kwargs["limit"] = limit
    page = arguments.get("page")
    if page is not None:
        kwargs["page"] = page
    sortfield = arguments.get("sortfield")
    if sortfield:
        kwargs["sortfield"] = sortfield
        kwargs["sortorder"] = arguments.get("sortorder", "ASC")
    return kwargs


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """Handle all tool calls using the DolibarrClient."""

    try:
        # Initialize the config and client
        config = Config()

        # Compute server-side field selection via Dolibarr ?properties= param
        properties = get_properties_param(
            TOOL_RESPONSE_CONFIG.get(name, {}).get("entity_type"),
            TOOL_RESPONSE_CONFIG.get(name, {}).get("field_set", "full"),
            [f.strip() for f in arguments["fields"].split(",") if f.strip()]
            if arguments.get("fields") else None,
        )

        async with DolibarrClient(config) as client:

            # System & Info
            if name == "test_connection":
                result = await client.get_status()
                if 'success' not in result:
                    result = {"status": "success", "message": "API connection working", "data": result}

            elif name == "get_status":
                result = await client.get_status()

            # Search Tools
            elif name == "search_products_by_ref":
                ref_prefix = _escape_sqlfilter(arguments['ref_prefix'])
                limit = arguments.get('limit', 20)
                sqlfilters = f"(t.ref:like:'{ref_prefix}%')"
                result = await client.search_products(sqlfilters=sqlfilters, limit=limit, properties=properties)

            elif name == "search_customers":
                query = _escape_sqlfilter(arguments['query'])
                limit = arguments.get('limit', 20)
                sqlfilters = f"((t.nom:like:'%{query}%') OR (t.name_alias:like:'%{query}%'))"
                result = await client.search_customers(sqlfilters=sqlfilters, limit=limit, properties=properties)

            elif name == "search_products_by_label":
                label_search = _escape_sqlfilter(arguments['label_search'])
                limit = arguments.get('limit', 20)
                sqlfilters = f"(t.label:like:'%{label_search}%')"
                result = await client.search_products(sqlfilters=sqlfilters, limit=limit, properties=properties)

            elif name == "resolve_product_ref":
                ref = arguments['ref']
                ref_esc = _escape_sqlfilter(ref)
                sqlfilters = f"(t.ref:like:'{ref_esc}')"
                products = await client.search_products(sqlfilters=sqlfilters, limit=2)

                if not products:
                    result = {"status": "not_found", "message": f"Product with ref '{ref}' not found"}
                elif len(products) == 1:
                    result = {"status": "ok", "product": products[0]}
                else:
                    exact_matches = [p for p in products if p.get('ref') == ref]
                    if len(exact_matches) == 1:
                        result = {"status": "ok", "product": exact_matches[0]}
                    else:
                        result = {"status": "ambiguous", "message": f"Multiple products found for ref '{ref}'", "products": products}

            # User Management
            elif name == "get_users":
                lk = _extract_list_kwargs(arguments, config)
                result = await client.get_users(**lk, properties=properties)

            elif name == "get_user_by_id":
                result = await client.get_user_by_id(arguments['user_id'])

            elif name == "create_user":
                result = await client.create_user(**{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "update_user":
                user_id = arguments.pop('user_id')
                result = await client.update_user(user_id, **{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "delete_user":
                result = await client.delete_user(arguments['user_id'])

            # Customer Management
            elif name == "get_customers":
                lk = _extract_list_kwargs(arguments, config)
                result = await client.get_customers(**lk, properties=properties)

            elif name == "get_customer_by_id":
                result = await client.get_customer_by_id(arguments['customer_id'])

            elif name == "create_customer":
                result = await client.create_customer(**{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "update_customer":
                customer_id = arguments.pop('customer_id')
                result = await client.update_customer(customer_id, **{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "delete_customer":
                result = await client.delete_customer(arguments['customer_id'])

            # Product Management
            elif name == "get_products":
                lk = _extract_list_kwargs(arguments, config)
                result = await client.get_products(**lk, properties=properties)

            elif name == "get_product_by_id":
                result = await client.get_product_by_id(arguments['product_id'])

            elif name == "create_product":
                result = await client.create_product(**{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "update_product":
                product_id = arguments.pop('product_id')
                result = await client.update_product(product_id, **{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "delete_product":
                result = await client.delete_product(arguments['product_id'])

            # Invoice Management
            elif name == "get_invoices":
                lk = _extract_list_kwargs(arguments, config)
                result = await client.get_invoices(**lk, status=arguments.get('status'), properties=properties)

            elif name == "get_invoice_by_id":
                result = await client.get_invoice_by_id(arguments['invoice_id'])

            elif name == "create_invoice":
                result = await client.create_invoice(**{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "update_invoice":
                invoice_id = arguments.pop('invoice_id')
                result = await client.update_invoice(invoice_id, **{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "delete_invoice":
                result = await client.delete_invoice(arguments['invoice_id'])

            elif name == "create_invoice_draft":
                if "customer_id" in arguments:
                    arguments["socid"] = arguments.pop("customer_id")
                if "project_id" in arguments:
                    arguments["fk_project"] = arguments.pop("project_id")
                result = await client.create_invoice(**{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "add_invoice_line":
                invoice_id = arguments.pop("invoice_id")
                result = await client.add_invoice_line(invoice_id, **{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "update_invoice_line":
                invoice_id = arguments.pop("invoice_id")
                line_id = arguments.pop("line_id")
                result = await client.update_invoice_line(invoice_id, line_id, **{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "delete_invoice_line":
                invoice_id = arguments.pop("invoice_id")
                line_id = arguments.pop("line_id")
                result = await client.delete_invoice_line(invoice_id, line_id)

            elif name == "set_invoice_project":
                invoice_id = arguments.pop("invoice_id")
                project_id = arguments.pop("project_id")
                result = await client.update_invoice(invoice_id, fk_project=project_id)

            elif name == "validate_invoice":
                invoice_id = arguments.pop("invoice_id")
                result = await client.validate_invoice(invoice_id, **{k: v for k, v in arguments.items() if k != "fields"})

            # Order Management
            elif name == "get_orders":
                lk = _extract_list_kwargs(arguments, config)
                result = await client.get_orders(**lk, status=arguments.get('status'), properties=properties)

            elif name == "get_order_by_id":
                result = await client.get_order_by_id(arguments['order_id'])

            elif name == "create_order":
                result = await client.create_order(**{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "update_order":
                order_id = arguments.pop('order_id')
                result = await client.update_order(order_id, **{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "delete_order":
                result = await client.delete_order(arguments['order_id'])

            # Contact Management
            elif name == "get_contacts":
                lk = _extract_list_kwargs(arguments, config)
                result = await client.get_contacts(**lk, properties=properties)

            elif name == "get_contact_by_id":
                result = await client.get_contact_by_id(arguments['contact_id'])

            elif name == "create_contact":
                result = await client.create_contact(**{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "update_contact":
                contact_id = arguments.pop('contact_id')
                result = await client.update_contact(contact_id, **{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "delete_contact":
                result = await client.delete_contact(arguments['contact_id'])

            # Project Management
            elif name == "get_projects":
                lk = _extract_list_kwargs(arguments, config)
                result = await client.get_projects(**lk, status=arguments.get("status"), properties=properties)

            elif name == "get_project_by_id":
                result = await client.get_project_by_id(arguments["project_id"])

            elif name == "search_projects":
                query = _escape_sqlfilter(arguments["query"])
                limit = arguments.get("limit", 20)
                sqlfilters = f"((t.ref:like:'%{query}%') OR (t.title:like:'%{query}%'))"
                result = await client.search_projects(sqlfilters=sqlfilters, limit=limit, properties=properties)

            elif name == "create_project":
                result = await client.create_project(**{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "update_project":
                project_id = arguments.pop("project_id")
                result = await client.update_project(project_id, **{k: v for k, v in arguments.items() if k != "fields"})

            elif name == "delete_project":
                result = await client.delete_project(arguments["project_id"])

            # Category Management
            elif name == "get_categories":
                lk = _extract_list_kwargs(arguments, config)
                result = await client.get_categories(
                    type=arguments.get("type", "product"), **lk, properties=properties,
                )

            elif name == "search_categories":
                query = _escape_sqlfilter(arguments["query"])
                limit = arguments.get("limit", 20)
                sqlfilters = f"(t.label:like:'%{query}%')"
                result = await client.search_categories(
                    sqlfilters=sqlfilters,
                    type=arguments.get("type", "product"),
                    limit=limit,
                    properties=properties,
                )

            elif name == "get_products_by_category":
                result = await client.get_products_by_category(
                    category_id=arguments["category_id"],
                    limit=arguments.get("limit", 50),
                    properties=properties,
                )

            elif name == "get_product_categories":
                result = await client.get_product_categories(arguments["product_id"])

            # Analytics
            elif name == "get_top_selling_products":
                result = await get_top_selling_products(
                    config,
                    period_months=arguments.get("period_months", 12),
                    limit=arguments.get("limit", 20),
                    category_id=arguments.get("category_id"),
                )

            elif name == "get_sales_summary":
                result = await get_sales_summary(
                    config,
                    period_months=arguments.get("period_months", 12),
                    group_by=arguments.get("group_by", "month"),
                )

            elif name == "get_low_stock_products":
                result = await get_low_stock_products(
                    config,
                    limit=arguments.get("limit", 20),
                    include_zero_stock=arguments.get("include_zero_stock", True),
                )

            # Raw API Access
            elif name == "dolibarr_raw_api":
                result = await client.dolibarr_raw_api(**arguments)

            else:
                result = {"error": f"Unknown tool: {name}"}

        return format_response(
            result,
            tool_name=name,
            arguments=arguments,
            max_response_chars=config.max_response_chars,
        )

    except AnalyticsUnavailableError as e:
        return [TextContent(type="text", text=json.dumps(
            {"error": "Analytics Unavailable", "message": str(e)},
            separators=(",", ":"),
        ))]

    except DolibarrAPIError as e:
        error_payload = e.response_data or {
            "error": "Dolibarr API Error",
            "status": e.status_code or 500,
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        return [TextContent(type="text", text=json.dumps(error_payload, separators=(",", ":")))]

    except Exception as e:
        correlation_id = str(uuid.uuid4())
        error_result = {
            "error": "Internal Server Error",
            "status": 500,
            "message": f"Tool execution failed: {str(e)}",
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        print(f"Tool execution error ({correlation_id}): {e}", file=sys.stderr)
        return [TextContent(type="text", text=json.dumps(error_result, separators=(",", ":")))]


@asynccontextmanager
async def test_api_connection(config: Config | None = None):
    """Test API connection and yield client if successful."""
    created_config = False
    api_ok = False
    try:
        if config is None:
            config = Config()
            created_config = True
        
        # Check if environment variables are set
        if not config.dolibarr_url or config.dolibarr_url == "https://your-dolibarr-instance.com/api/index.php":
            print("⚠️  Warning: DOLIBARR_URL not configured in .env file", file=sys.stderr)
            print("⚠️  Using placeholder URL - API calls will fail", file=sys.stderr)
            print("📝 Please configure your .env file with valid Dolibarr credentials", file=sys.stderr)
            yield False  # Configuration incomplete
            return
            
        if not config.api_key or config.api_key == "your_dolibarr_api_key_here":
            print("⚠️  Warning: DOLIBARR_API_KEY not configured in .env file", file=sys.stderr)
            print("⚠️  API authentication will fail", file=sys.stderr)
            print("📝 Please configure your .env file with valid Dolibarr credentials", file=sys.stderr)
            yield False  # Configuration incomplete
            return
        
        async with DolibarrClient(config) as client:
            print("🧪 Testing Dolibarr API connection...", file=sys.stderr)
            result = await client.get_status()
            if 'success' in result or 'dolibarr_version' in str(result):
                print("✅ Dolibarr API connection successful", file=sys.stderr)
                print("🎯 Full CRUD operations available for all Dolibarr modules", file=sys.stderr)
                api_ok = True
            else:
                print(f"⚠️  API test returned unexpected result: {result}", file=sys.stderr)
                print("⚠️  Server will start but API calls may fail", file=sys.stderr)
                api_ok = False
    except Exception as e:
        print(f"⚠️  API test error: {e}", file=sys.stderr)
        if config is None or created_config:
            print("💡 Check your .env file configuration", file=sys.stderr)
        print("⚠️  Server will start but API calls may fail", file=sys.stderr)
        api_ok = False
    
    yield api_ok


async def _run_stdio_server(_config: Config) -> None:
    """Run the MCP server over STDIO (default)."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="dolibarr-mcp",
                server_version="1.0.1",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


class _UrlTokenMiddleware:
    """Require a shared secret as the first path segment, then strip it.

    Requests that do not match return 404 (not 401) to avoid leaking the
    existence of a valid endpoint to scanners.
    """

    def __init__(self, app, token: str):
        self.app = app
        self.prefix = f"/{token}"
        self.prefix_bytes = self.prefix.encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path != self.prefix and not path.startswith(self.prefix + "/"):
            await Response(status_code=404)(scope, receive, send)
            return

        new_scope = dict(scope)
        new_scope["path"] = path[len(self.prefix):] or "/"
        raw_path = scope.get("raw_path")
        if raw_path:
            if raw_path.startswith(self.prefix_bytes):
                new_scope["raw_path"] = raw_path[len(self.prefix_bytes):] or b"/"
        await self.app(new_scope, receive, send)


def _build_http_app(session_manager: StreamableHTTPSessionManager) -> Starlette:
    """Create Starlette app that forwards to the StreamableHTTP session manager."""

    class ASGIEndpoint:
        """Lightweight adapter so Route treats our handler as an ASGI app."""

        def __init__(self, handler):
            self.handler = handler

        async def __call__(self, scope: Scope, receive: Receive, send: Send):
            await self.handler(scope, receive, send)

    async def options_handler(request):
        """Lightweight CORS-friendly response for preflight requests."""
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
                "Access-Control-Allow-Headers": "*",
            },
        )

    async def lifespan(app):
        async with session_manager.run():
            yield

    async def asgi_handler(scope, receive, send):
        """Adapter to call the StreamableHTTPSessionManager with ASGI signature."""
        await session_manager.handle_request(scope, receive, send)

    asgi_endpoint = ASGIEndpoint(asgi_handler)

    app = Starlette(
        routes=[
            Route("/", asgi_endpoint, methods=["GET", "POST", "DELETE"]),
            Route("/{path:path}", asgi_endpoint, methods=["GET", "POST", "DELETE"]),
            Route("/", options_handler, methods=["OPTIONS"]),
            Route("/{path:path}", options_handler, methods=["OPTIONS"]),
        ],
        lifespan=lifespan,
    )

    # Allow cross-origin requests from MCP-enabled web UIs and dashboards.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    return app


async def _run_http_server(config: Config) -> None:
    """Run the MCP server over HTTP (StreamableHTTP)."""
    session_manager = StreamableHTTPSessionManager(server, json_response=False, stateless=False)
    app = _build_http_app(session_manager)
    if config.mcp_url_token:
        app = _UrlTokenMiddleware(app, config.mcp_url_token)
        print("🔒 URL token auth enabled — requests must include the secret path prefix", file=sys.stderr)
    print(
        f"🌐 Starting MCP HTTP server on {config.mcp_http_host}:{config.mcp_http_port}",
        file=sys.stderr,
    )
    uvicorn_config = uvicorn.Config(
        app,
        host=config.mcp_http_host,
        port=config.mcp_http_port,
        log_level=config.log_level.lower(),
        loop="asyncio",
        access_log=False,
    )
    uvicorn_server = uvicorn.Server(uvicorn_config)
    await uvicorn_server.serve()


async def main():
    """Run the Dolibarr MCP server."""
    config = Config()

    # Test API connection but don't fail if it's not working
    async with test_api_connection(config) as api_ok:
        if not api_ok:
            print("⚠️  Starting server without valid API connection", file=sys.stderr)
            print("📝 Configure your .env file to enable API functionality", file=sys.stderr)
        else:
            print("✅ API connection validated", file=sys.stderr)
    
    # Test database connection for analytics
    if config.db_available:
        try:
            from .analytics import _get_connection
            print("🧪 Testing database connection...", file=sys.stderr)
            conn = await _get_connection(config)
            conn.close()
            print("✅ Database connection successful", file=sys.stderr)
            print("📊 Analytics tools available (top sellers, sales summary, low stock)", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  Database connection failed: {e}", file=sys.stderr)
            print("⚠️  Analytics tools will not work, but API tools remain available", file=sys.stderr)
    else:
        print("ℹ️  Database not configured — analytics tools disabled", file=sys.stderr)
        print("📝 Set DB_HOST, DB_NAME, DB_USER, DB_PASSWORD to enable analytics", file=sys.stderr)

    # Run server regardless of API/DB status
    print("🚀 Starting Dolibarr MCP server...", file=sys.stderr)
    print("✅ Server ready", file=sys.stderr)

    try:
        if config.mcp_transport == "http":
            await _run_http_server(config)
        else:
            await _run_stdio_server(config)
    except Exception as e:
        print(f"💥 Server error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Server startup error: {e}", file=sys.stderr)
        sys.exit(1)
