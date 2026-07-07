"""Tests for search_invoices, set_invoice_to_draft and add_payment_to_invoice."""

from unittest.mock import AsyncMock

import pytest

from dolibarr_mcp.config import Config
from dolibarr_mcp.dolibarr_client import DolibarrClient, DolibarrAPIError


def _client():
    return DolibarrClient(Config(
        dolibarr_url="https://test.dolibarr.com/api/index.php",
        api_key="test_key",
    ))


@pytest.mark.asyncio
async def test_search_invoices_builds_sqlfilters():
    client = _client()
    client.request = AsyncMock(return_value=[])

    await client.search_invoices(customer_id=8, status=1, limit=5)

    params = client.request.call_args.kwargs["params"]
    assert params["sqlfilters"] == "(t.fk_soc:=:8) and (t.fk_statut:=:1)"
    assert params["limit"] == 5
    assert params["sortorder"] == "DESC"


@pytest.mark.asyncio
async def test_search_invoices_no_filters_omits_sqlfilters():
    client = _client()
    client.request = AsyncMock(return_value=[])

    await client.search_invoices()

    assert "sqlfilters" not in client.request.call_args.kwargs["params"]


@pytest.mark.asyncio
async def test_set_invoice_to_draft_posts_settodraft():
    client = _client()
    client.request = AsyncMock(return_value={"id": 1})

    await client.set_invoice_to_draft(1)

    method, endpoint = client.request.call_args.args[:2]
    assert (method, endpoint) == ("POST", "invoices/1/settodraft")
    assert client.request.call_args.kwargs["data"] == {"idwarehouse": -1}


@pytest.mark.asyncio
async def test_add_payment_resolves_single_account_and_vir_mode():
    client = _client()
    client.get_bank_accounts = AsyncMock(return_value=[{"id": "4", "label": "Main"}])
    client.get_payment_modes = AsyncMock(return_value=[
        {"id": "1", "code": "CB"}, {"id": "2", "code": "VIR"},
    ])
    client.request = AsyncMock(return_value=99)

    await client.add_payment_to_invoice(10, date="2026-07-07")

    sent = client.request.call_args.kwargs["data"]
    assert sent["accountid"] == "4"          # single account auto-picked
    assert sent["paymentid"] == "2"          # VIR chosen
    assert sent["closepaidinvoices"] == "yes"
    assert client.request.call_args.args[1] == "invoices/10/payments"


@pytest.mark.asyncio
async def test_add_payment_errors_on_multiple_accounts():
    client = _client()
    client.get_bank_accounts = AsyncMock(return_value=[{"id": "1"}, {"id": "2"}])

    with pytest.raises(DolibarrAPIError, match="Multiple bank accounts"):
        await client.add_payment_to_invoice(10, date="2026-07-07")
