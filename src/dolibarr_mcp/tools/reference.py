"""Reference / dictionary lookups (tax rates, ...)."""

from __future__ import annotations

from mcp.types import Tool

from .base import ToolContext

TOOLS: list[Tool] = [
    Tool(
        name="get_vat_rates",
        description=(
            "List the valid tax rates (VAT, or TGC in New Caledonia) from Dolibarr's tax "
            "dictionary. Defaults to the company's own country, so these are the rates that "
            "apply to your invoices and orders. Call this before setting a line's tva_tx to "
            "use a rate that actually exists in the dictionary instead of guessing."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "country_id": {
                    "type": "integer",
                    "description": "Dolibarr country id to scope the rates to. Defaults to the company's country.",
                },
                "active": {
                    "type": "integer",
                    "description": "1 for active rates only (default), 0 to include inactive ones.",
                    "default": 1,
                },
            },
            "additionalProperties": False,
        },
    ),
]


async def get_vat_rates(ctx: ToolContext):
    return await ctx.client.get_vat_rates(
        country_id=ctx.arguments.get("country_id"),
        active=ctx.arguments.get("active", 1),
    )


HANDLERS = {
    "get_vat_rates": get_vat_rates,
}
