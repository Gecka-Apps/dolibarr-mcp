"""Per-domain tool registry.

Each domain module exports ``TOOLS`` (definitions) and ``HANDLERS`` (name ->
async handler). This package aggregates them into ``ALL_TOOLS`` / ``ALL_HANDLERS``
that the central server advertises and dispatches, while keeping the cross-cutting
concerns (capability gating, response shaping, analytics availability) central.

To add or move a tool, edit the relevant domain module and, if new, add its
module to ``_MODULES`` below. Nothing else in the server needs to change.
"""

from __future__ import annotations

from mcp.types import Tool

from . import (
    analytics,
    categories,
    contacts,
    customers,
    invoices,
    orders,
    products,
    projects,
    system,
    users,
)

_MODULES = [
    system,
    customers,
    products,
    invoices,
    orders,
    contacts,
    projects,
    categories,
    users,
    analytics,
]

ALL_TOOLS: list[Tool] = [tool for module in _MODULES for tool in module.TOOLS]
ALL_HANDLERS = {
    name: handler
    for module in _MODULES
    for name, handler in module.HANDLERS.items()
}
