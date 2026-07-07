"""Tests for customer order line tools."""

from unittest.mock import AsyncMock

import pytest

from dolibarr_mcp.config import Config
from dolibarr_mcp.dolibarr_client import DolibarrClient


def _client():
    return DolibarrClient(Config(
        dolibarr_url="https://test.dolibarr.com/api/index.php",
        api_key="test_key",
    ))


@pytest.mark.asyncio
async def test_add_order_line_maps_product_id():
    client = _client()
    client.request = AsyncMock(return_value=7)

    await client.add_order_line(1, desc="Service", qty=2, subprice=100, product_id=42)

    method, endpoint = client.request.call_args.args[:2]
    sent = client.request.call_args.kwargs["data"]
    assert (method, endpoint) == ("POST", "orders/1/lines")
    assert sent["fk_product"] == 42
    assert "product_id" not in sent


@pytest.mark.asyncio
async def test_update_order_line_preserves_unprovided_fields():
    client = _client()
    client.get_order_by_id = AsyncMock(return_value={
        "lines": [{
            "id": "5", "desc": "Old", "subprice": "100.00",
            "qty": "2", "tva_tx": "20.0", "product_type": "1",
        }],
    })
    client.request = AsyncMock(return_value=5)

    await client.update_order_line(1, 5, qty=3)

    sent = client.request.call_args.kwargs["data"]
    assert sent["qty"] == 3            # overridden
    assert sent["desc"] == "Old"       # preserved
    assert sent["subprice"] == "100.00"
    assert sent["tva_tx"] == "20.0"
    assert sent["product_type"] == "1"


@pytest.mark.asyncio
async def test_delete_order_line():
    client = _client()
    client.request = AsyncMock(return_value={"success": True})

    await client.delete_order_line(1, 5)

    method, endpoint = client.request.call_args.args[:2]
    assert (method, endpoint) == ("DELETE", "orders/1/lines/5")
