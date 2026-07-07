"""Tests for proposal (quote) client methods, focused on the tricky routes/remaps."""

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
async def test_create_proposal_remaps_ids():
    client = _client()
    client.request = AsyncMock(return_value=5)

    await client.create_proposal(
        customer_id=8, project_id=3, date="2026-07-07",
        lines=[{"desc": "L", "qty": 1, "subprice": 10, "product_id": 42}],
    )

    sent = client.request.call_args.kwargs["data"]
    assert sent["socid"] == 8 and "customer_id" not in sent
    assert sent["fk_projet"] == 3 and "project_id" not in sent
    assert sent["lines"][0]["fk_product"] == 42 and "product_id" not in sent["lines"][0]


@pytest.mark.asyncio
async def test_add_proposal_line_uses_singular_route():
    """The plural /lines route expects an array; a single line must go to /line."""
    client = _client()
    client.request = AsyncMock(return_value=1)

    await client.add_proposal_line(7, desc="L", qty=1, subprice=10, product_id=42)

    method, endpoint = client.request.call_args.args[:2]
    assert (method, endpoint) == ("POST", "proposals/7/line")
    assert client.request.call_args.kwargs["data"]["fk_product"] == 42


@pytest.mark.asyncio
async def test_update_proposal_line_preserves_fields():
    client = _client()
    client.get_proposal_by_id = AsyncMock(return_value={
        "lines": [{"id": "612", "desc": "L", "subprice": "10.00", "qty": "1", "tva_tx": "11.0", "product_type": "1"}],
    })
    client.request = AsyncMock(return_value=612)

    await client.update_proposal_line(7, 612, qty=4)

    sent = client.request.call_args.kwargs["data"]
    assert sent["qty"] == 4 and sent["desc"] == "L" and sent["subprice"] == "10.00"
    assert client.request.call_args.args[1] == "proposals/7/lines/612"


@pytest.mark.asyncio
async def test_sign_proposal_posts_close_with_status():
    client = _client()
    client.request = AsyncMock(return_value={"id": 7})

    await client.sign_proposal(7, note="ok")

    method, endpoint = client.request.call_args.args[:2]
    assert (method, endpoint) == ("POST", "proposals/7/close")
    sent = client.request.call_args.kwargs["data"]
    assert sent["status"] == 2 and sent["note_private"] == "ok"


@pytest.mark.asyncio
async def test_convert_proposal_uses_orders_endpoint():
    client = _client()
    client.request = AsyncMock(return_value=3)

    await client.convert_proposal_to_order(7)

    method, endpoint = client.request.call_args.args[:2]
    assert (method, endpoint) == ("POST", "orders/createfromproposal/7")
