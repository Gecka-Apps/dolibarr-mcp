"""Tests for the tax-rate (VAT/TGC) lookup and the invoice line tva_tx fix."""

from unittest.mock import AsyncMock

import pytest

from dolibarr_mcp.config import Config
from dolibarr_mcp.dolibarr_client import DolibarrClient
from dolibarr_mcp.tools.invoices import TOOLS as INVOICE_TOOLS


def _client():
    return DolibarrClient(Config(
        dolibarr_url="https://test.dolibarr.com/api/index.php",
        api_key="test_key",
    ))


_VAT_ROWS = [
    {"taux": "0", "code": "", "note": "TGC 0", "localtax1": "0", "localtax2": "0"},
    {"taux": "11", "code": "", "note": "TGC 11", "localtax1": "0", "localtax2": "0"},
]


@pytest.mark.asyncio
async def test_get_vat_rates_resolves_company_country_and_trims():
    client = _client()
    client.request = AsyncMock(side_effect=[{"country_id": 165}, _VAT_ROWS])

    rates = await client.get_vat_rates()

    # First call resolves the company country, second is the dictionary lookup.
    vat_call = client.request.call_args_list[1]
    assert vat_call.args[:2] == ("GET", "setup/dictionary/vat")
    assert vat_call.kwargs["params"]["fk_country"] == 165
    assert rates == [
        {"rate": 0.0, "code": None, "note": "TGC 0"},
        {"rate": 11.0, "code": None, "note": "TGC 11"},
    ]


@pytest.mark.asyncio
async def test_get_vat_rates_explicit_country_skips_company_lookup():
    client = _client()
    client.request = AsyncMock(return_value=_VAT_ROWS)

    await client.get_vat_rates(country_id=165)

    # Only the dictionary call, no setup/company resolution.
    assert client.request.call_count == 1
    assert client.request.call_args.kwargs["params"]["fk_country"] == 165


@pytest.mark.asyncio
async def test_get_vat_rates_surfaces_local_taxes_when_set():
    client = _client()
    client.request = AsyncMock(return_value=[
        {"taux": "5", "code": "X", "note": "n", "localtax1": "2", "localtax2": "0"},
    ])

    rates = await client.get_vat_rates(country_id=1)

    assert rates[0]["localtax1"] == "2"
    assert "localtax2" not in rates[0]  # zero local taxes are omitted


def test_invoice_line_schema_uses_tva_tx_not_vat():
    """Regression for the P0-5 bug: Dolibarr expects tva_tx, not vat."""
    for name in ("add_invoice_line", "update_invoice_line"):
        schema = next(t.inputSchema for t in INVOICE_TOOLS if t.name == name)
        assert "tva_tx" in schema["properties"], f"{name} missing tva_tx"
        assert "vat" not in schema["properties"], f"{name} still exposes the ignored 'vat'"
