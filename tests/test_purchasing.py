"""Tests for product purchase-price client methods."""

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
async def test_add_purchase_price_sets_buyprice_and_multicurrency():
    """Multicurrency-enabled instances overwrite buyprice with the multicurrency
    price, so both must carry the value."""
    client = _client()
    client.request = AsyncMock(return_value=1)

    await client.add_product_purchase_price(5, supplier_id=8, price=350, supplier_ref="SKU-9")

    method, endpoint = client.request.call_args.args[:2]
    sent = client.request.call_args.kwargs["data"]
    assert (method, endpoint) == ("POST", "products/5/purchase_prices")
    assert sent["buyprice"] == 350
    assert sent["multicurrency_buyprice"] == 350
    assert sent["fourn_id"] == 8
    assert sent["ref_fourn"] == "SKU-9"


@pytest.mark.asyncio
async def test_get_purchase_prices_endpoint():
    client = _client()
    client.request = AsyncMock(return_value=[])

    await client.get_product_purchase_prices(5)

    assert client.request.call_args.args[:2] == ("GET", "products/5/purchase_prices")


@pytest.mark.asyncio
async def test_delete_purchase_price_endpoint():
    client = _client()
    client.request = AsyncMock(return_value={"success": True})

    await client.delete_product_purchase_price(5, 70)

    assert client.request.call_args.args[:2] == ("DELETE", "products/5/purchase_prices/70")
