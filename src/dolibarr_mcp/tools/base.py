"""Shared building blocks for the per-domain tool modules.

Each ``tools/<domain>.py`` module exports two things:
  - ``TOOLS``: the list of ``Tool`` definitions for that domain
  - ``HANDLERS``: a ``{tool_name: async handler}`` map

A handler receives a single :class:`ToolContext` and returns the raw result. The
central server applies the cross-cutting concerns (capability gating, response
shaping, error handling) uniformly, so handlers stay small and focused.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..config import Config
from ..dolibarr_client import DolibarrClient


@dataclass
class ToolContext:
    """Everything a tool handler needs, assembled once by the central dispatcher."""

    client: DolibarrClient
    arguments: dict
    config: Config
    # Precomputed Dolibarr ?properties= selector for server-side field trimming.
    properties: Optional[str]


def escape_sqlfilter(value: str) -> str:
    """Escape single quotes for Dolibarr USF SQL filters."""
    return value.replace("'", "''")


def extract_list_kwargs(arguments: dict, config: Config) -> dict:
    """Extract the common list/pagination/sort parameters from tool arguments."""
    kwargs: dict = {"limit": arguments.get("limit", config.default_list_limit)}
    page = arguments.get("page")
    if page is not None:
        kwargs["page"] = page
    sortfield = arguments.get("sortfield")
    if sortfield:
        kwargs["sortfield"] = sortfield
        kwargs["sortorder"] = arguments.get("sortorder", "ASC")
    return kwargs


# Common schema fragments injected into list/search/detail tool schemas.
LIST_PARAMS = {
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

DETAIL_PARAMS = {
    "fields": {
        "type": "string",
        "description": "Comma-separated fields to return. Default: all fields.",
    },
}
