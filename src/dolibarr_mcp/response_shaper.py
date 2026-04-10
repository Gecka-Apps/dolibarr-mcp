"""Response shaping for MCP tool outputs.

Filters Dolibarr API responses to return only relevant fields,
formats them compactly, and applies truncation when needed.
"""

import json
from typing import Any, Dict, List, Optional

from mcp.types import TextContent


# ---------------------------------------------------------------------------
# Default maximum response size (characters). Configurable via Config.
# ---------------------------------------------------------------------------
DEFAULT_MAX_RESPONSE_CHARS = 100_000


# ---------------------------------------------------------------------------
# Entity field sets
# ---------------------------------------------------------------------------
# Three tiers per entity type:
#   summary  — list operations (minimal, compact)
#   standard — search results (useful detail without bloat)
#   full     — get-by-id (no filtering, return everything)
#
# None means "no filtering".

ENTITY_FIELD_SETS: Dict[str, Dict[str, Optional[List[str]]]] = {
    "product": {
        "summary": [
            "id", "ref", "label", "price", "price_ttc", "status", "type",
            "stock_reel", "barcode", "tva_tx",
        ],
        "standard": [
            "id", "ref", "label", "description", "price", "price_ttc",
            "price_min", "price_min_ttc", "tva_tx", "status", "type",
            "stock_reel", "barcode", "weight", "tosell", "tobuy",
            "date_creation", "date_modification",
        ],
        "full": None,
    },
    "invoice": {
        "summary": [
            "id", "ref", "socid", "date", "date_lim_reglement",
            "total_ht", "total_tva", "total_ttc", "paye", "status",
        ],
        "standard": [
            "id", "ref", "ref_ext", "socid", "date", "date_lim_reglement",
            "total_ht", "total_tva", "total_ttc", "paye", "status",
            "fk_project", "note_public", "lines",
            "date_creation", "date_modification",
        ],
        "full": None,
    },
    "order": {
        "summary": [
            "id", "ref", "socid", "date", "total_ht", "total_ttc", "status",
        ],
        "standard": [
            "id", "ref", "ref_ext", "socid", "date", "total_ht", "total_tva",
            "total_ttc", "status", "fk_project", "lines",
            "date_creation", "date_modification",
        ],
        "full": None,
    },
    "customer": {
        "summary": [
            "id", "nom", "name_alias", "email", "phone", "status", "client",
            "fournisseur", "town", "zip", "country_code", "code_client",
        ],
        "standard": [
            "id", "nom", "name_alias", "email", "phone", "address", "town",
            "zip", "country_id", "country_code", "status", "client",
            "fournisseur", "code_client", "code_fournisseur",
            "date_creation", "date_modification",
        ],
        "full": None,
    },
    "user": {
        "summary": [
            "id", "login", "lastname", "firstname", "email", "statut", "admin",
        ],
        "standard": [
            "id", "login", "lastname", "firstname", "email", "statut",
            "admin", "entity", "datec", "datem",
        ],
        "full": None,
    },
    "contact": {
        "summary": [
            "id", "firstname", "lastname", "email", "phone_pro", "socid",
            "statut",
        ],
        "standard": [
            "id", "firstname", "lastname", "email", "phone_pro",
            "phone_perso", "phone_mobile", "socid", "poste", "statut",
            "datec", "datem",
        ],
        "full": None,
    },
    "project": {
        "summary": [
            "id", "ref", "title", "socid", "status", "date_start",
            "date_end", "budget_amount",
        ],
        "standard": [
            "id", "ref", "title", "description", "socid", "status",
            "date_start", "date_end", "budget_amount", "opp_amount",
            "opp_percent", "date_creation", "date_modification",
        ],
        "full": None,
    },
    "category": {
        "summary": [
            "id", "label", "type", "fk_parent",
        ],
        "standard": [
            "id", "label", "description", "type", "fk_parent",
            "date_creation", "date_modification",
        ],
        "full": None,
    },
}


# ---------------------------------------------------------------------------
# Invoice / order line summary fields
# ---------------------------------------------------------------------------
# The Dolibarr ?properties= param does NOT filter sub-objects (lines).
# We filter them client-side for summary/standard modes.

INVOICE_LINE_SUMMARY: List[str] = [
    "id", "fk_product", "product_ref", "product_label", "qty",
    "subprice", "total_ht", "total_ttc", "tva_tx", "product_type",
    "description",
]

ORDER_LINE_SUMMARY: List[str] = [
    "id", "fk_product", "product_ref", "product_label", "qty",
    "subprice", "total_ht", "total_ttc", "tva_tx", "product_type",
    "description",
]


# ---------------------------------------------------------------------------
# Tool response configuration
# ---------------------------------------------------------------------------
# Maps tool names to their default response shaping behaviour.

TOOL_RESPONSE_CONFIG: Dict[str, Dict[str, Any]] = {
    # List tools → summary, compact
    "get_users":     {"entity_type": "user",     "field_set": "summary", "is_list": True},
    "get_customers": {"entity_type": "customer", "field_set": "summary", "is_list": True},
    "get_products":  {"entity_type": "product",  "field_set": "summary", "is_list": True},
    "get_invoices":  {"entity_type": "invoice",  "field_set": "summary", "is_list": True},
    "get_orders":    {"entity_type": "order",    "field_set": "summary", "is_list": True},
    "get_contacts":  {"entity_type": "contact",  "field_set": "summary", "is_list": True},
    "get_projects":  {"entity_type": "project",  "field_set": "summary", "is_list": True},

    # Search tools → standard, compact
    "search_products_by_ref":   {"entity_type": "product",  "field_set": "standard", "is_list": True},
    "search_products_by_label": {"entity_type": "product",  "field_set": "standard", "is_list": True},
    "search_customers":         {"entity_type": "customer", "field_set": "standard", "is_list": True},
    "search_projects":          {"entity_type": "project",  "field_set": "standard", "is_list": True},

    # Category tools
    "get_categories":         {"entity_type": "category", "field_set": "summary", "is_list": True},
    "search_categories":      {"entity_type": "category", "field_set": "standard", "is_list": True},
    "get_products_by_category": {"entity_type": "product", "field_set": "summary", "is_list": True},
    "get_product_categories": {"entity_type": "category", "field_set": "summary", "is_list": True},

    # Detail tools → full
    "get_user_by_id":     {"entity_type": "user",     "field_set": "full", "is_list": False},
    "get_customer_by_id": {"entity_type": "customer", "field_set": "full", "is_list": False},
    "get_product_by_id":  {"entity_type": "product",  "field_set": "full", "is_list": False},
    "get_invoice_by_id":  {"entity_type": "invoice",  "field_set": "full", "is_list": False},
    "get_order_by_id":    {"entity_type": "order",    "field_set": "full", "is_list": False},
    "get_contact_by_id":  {"entity_type": "contact",  "field_set": "full", "is_list": False},
    "get_project_by_id":  {"entity_type": "project",  "field_set": "full", "is_list": False},
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_field_list(
    entity_type: Optional[str],
    field_set: str = "summary",
    custom_fields: Optional[List[str]] = None,
) -> Optional[List[str]]:
    """Resolve the list of fields to use.

    Returns *None* when no filtering should be applied (full mode or
    unknown entity type).
    """
    if custom_fields:
        return custom_fields

    if not entity_type:
        return None

    type_sets = ENTITY_FIELD_SETS.get(entity_type, {})
    return type_sets.get(field_set)


def get_properties_param(
    entity_type: Optional[str],
    field_set: str = "summary",
    custom_fields: Optional[List[str]] = None,
) -> Optional[str]:
    """Build the ``properties`` query-string value for the Dolibarr API.

    Returns *None* when the full response should be returned.
    """
    fields = get_field_list(entity_type, field_set, custom_fields)
    if fields is None:
        return None
    # Exclude sub-object keys that aren't real Dolibarr columns
    excluded = {"lines"}
    api_fields = [f for f in fields if f not in excluded]
    return ",".join(api_fields) if api_fields else None


def filter_fields(entity: Dict[str, Any], fields: Optional[List[str]]) -> Dict[str, Any]:
    """Keep only *fields* keys in *entity*.  Pass-through when *fields* is None."""
    if fields is None:
        return entity
    return {k: v for k, v in entity.items() if k in fields}


def filter_lines(
    lines: List[Dict[str, Any]],
    line_fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Filter sub-object lines (invoice/order) to keep only useful fields."""
    if line_fields is None:
        return lines
    return [filter_fields(line, line_fields) for line in lines]


def _line_fields_for(entity_type: Optional[str], field_set: str) -> Optional[List[str]]:
    """Return the line-level field list or None (no filtering)."""
    if field_set == "full":
        return None
    if entity_type == "invoice":
        return INVOICE_LINE_SUMMARY
    if entity_type == "order":
        return ORDER_LINE_SUMMARY
    return None


def _shape_entity(
    entity: Dict[str, Any],
    entity_type: Optional[str],
    field_set: str,
    custom_fields: Optional[List[str]],
) -> Dict[str, Any]:
    """Apply field + line filtering to a single entity dict."""
    fields = get_field_list(entity_type, field_set, custom_fields)
    shaped = filter_fields(entity, fields)

    # Filter nested lines when present
    if "lines" in shaped and isinstance(shaped["lines"], list):
        lf = _line_fields_for(entity_type, field_set) if not custom_fields else None
        shaped["lines"] = filter_lines(shaped["lines"], lf)

    return shaped


# ---------------------------------------------------------------------------
# Response formatting
# ---------------------------------------------------------------------------

def format_response(
    result: Any,
    *,
    tool_name: str,
    arguments: Dict[str, Any],
    max_response_chars: int = DEFAULT_MAX_RESPONSE_CHARS,
) -> List[TextContent]:
    """Format a tool result into MCP ``TextContent``.

    - Looks up *tool_name* in ``TOOL_RESPONSE_CONFIG`` for defaults.
    - Applies field filtering (server-side via ``properties`` already done,
      this handles line filtering and any remaining shaping).
    - Wraps lists in ``{"count": N, "page": P, "items": [...]}``.
    - Uses compact JSON (no indent) for lists.
    - Truncates when the serialised response exceeds *max_response_chars*.
    """
    config = TOOL_RESPONSE_CONFIG.get(tool_name, {})
    entity_type = config.get("entity_type")
    field_set = config.get("field_set", "full")
    is_list = config.get("is_list", False)

    # Allow caller to override field set
    custom_fields: Optional[List[str]] = None
    raw_fields = arguments.get("fields")
    if raw_fields:
        custom_fields = [f.strip() for f in raw_fields.split(",") if f.strip()]

    # ----- List responses -----
    if is_list and isinstance(result, list):
        items = [_shape_entity(e, entity_type, field_set, custom_fields) for e in result]
        page = arguments.get("page", 1)
        envelope: Dict[str, Any] = {
            "count": len(items),
            "page": page,
            "items": items,
        }

        text = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False)

        # Truncate if too large
        if len(text) > max_response_chars:
            # Binary search for how many items fit
            lo, hi = 0, len(items)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                trial = json.dumps(
                    {"count": len(items), "page": page, "showing": mid,
                     "truncated": True, "items": items[:mid]},
                    separators=(",", ":"), ensure_ascii=False,
                )
                if len(trial) <= max_response_chars:
                    lo = mid
                else:
                    hi = mid - 1

            envelope = {
                "count": len(items),
                "page": page,
                "showing": lo,
                "truncated": True,
                "message": f"Response truncated: {len(items)} items available, {lo} shown. Use a smaller limit or add fields filter.",
                "items": items[:lo],
            }
            text = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False)

        return [TextContent(type="text", text=text)]

    # ----- Single entity responses -----
    if isinstance(result, dict):
        shaped = _shape_entity(result, entity_type, field_set, custom_fields)
        text = json.dumps(shaped, separators=(",", ":"), ensure_ascii=False)

        if len(text) > max_response_chars:
            # For single entities, try standard then summary
            for fallback in ("standard", "summary"):
                if fallback == field_set:
                    continue
                shaped_fb = _shape_entity(result, entity_type, fallback, None)
                text_fb = json.dumps(shaped_fb, separators=(",", ":"), ensure_ascii=False)
                if len(text_fb) <= max_response_chars:
                    shaped_fb["_note"] = f"Response reduced to '{fallback}' fields due to size."
                    return [TextContent(type="text", text=json.dumps(
                        shaped_fb, separators=(",", ":"), ensure_ascii=False,
                    ))]

        return [TextContent(type="text", text=text)]

    # ----- Fallback (scalar, unknown structure) -----
    return [TextContent(type="text", text=json.dumps(result, separators=(",", ":"), ensure_ascii=False))]
