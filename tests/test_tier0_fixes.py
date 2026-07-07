"""Regression tests for the Tier 0 bug fixes."""

from unittest.mock import AsyncMock

import pytest

from dolibarr_mcp.config import Config
from dolibarr_mcp.dolibarr_client import DolibarrClient
from dolibarr_mcp.tools.products import TOOLS as PRODUCT_TOOLS


def _client():
    config = Config(
        dolibarr_url="https://test.dolibarr.com/api/index.php",
        api_key="test_key",
    )
    return DolibarrClient(config)


def test_create_product_schema_exposes_ref_and_type():
    """The create_product schema must allow the fields the client requires."""
    schema = next(t.inputSchema for t in PRODUCT_TOOLS if t.name == "create_product")
    props = schema["properties"]
    for field in ("ref", "type", "price", "price_ttc", "tva_tx"):
        assert field in props, f"{field} missing from create_product schema"
    assert set(schema["required"]) == {"ref", "label", "type"}


@pytest.mark.asyncio
async def test_update_invoice_line_preserves_unprovided_fields():
    """A partial line update must not blank the fields it does not mention."""
    client = _client()
    client.get_invoice_by_id = AsyncMock(return_value={
        "lines": [{
            "id": "5", "desc": "Old label", "subprice": "10.00",
            "qty": "2", "tva_tx": "20.0", "product_type": "0", "fk_product": "42",
        }],
    })
    client.request = AsyncMock(return_value={"id": 5})

    await client.update_invoice_line(1, 5, qty=3)

    sent = client.request.call_args.kwargs["data"]
    assert sent["qty"] == 3               # overridden
    assert sent["desc"] == "Old label"    # preserved
    assert sent["subprice"] == "10.00"    # preserved
    assert sent["tva_tx"] == "20.0"       # preserved
    assert sent["fk_product"] == "42"     # preserved


@pytest.mark.asyncio
async def test_create_customer_defaults_accounting_codes():
    """A customer/supplier gets the '-1' sentinel so Dolibarr auto-numbers it."""
    client = _client()
    client.request = AsyncMock(return_value={"id": 9})

    await client.create_customer({"name": "ACME", "type": 3})  # 3 = customer + supplier

    sent = client.request.call_args.kwargs["data"]
    assert sent["code_client"] == "-1"
    assert sent["code_fournisseur"] == "-1"
