"""Tests for supplier orders and proposal document generation."""

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
async def test_create_supplier_order_remaps_ids_and_defaults_line_type():
    client = _client()
    client.request = AsyncMock(return_value=1)

    await client.create_supplier_order(
        supplier_id=8, date="2026-07-07",
        lines=[{"desc": "L", "qty": 1, "subprice": 10, "product_id": 42}],
    )

    method, endpoint = client.request.call_args.args[:2]
    sent = client.request.call_args.kwargs["data"]
    assert (method, endpoint) == ("POST", "supplierorders")
    assert sent["socid"] == 8 and "supplier_id" not in sent
    line = sent["lines"][0]
    assert line["fk_product"] == 42 and "product_id" not in line
    assert line["product_type"] == 0


@pytest.mark.asyncio
async def test_get_supplier_order_by_id_endpoint():
    client = _client()
    client.request = AsyncMock(return_value={})

    await client.get_supplier_order_by_id(3)

    assert client.request.call_args.args[:2] == ("GET", "supplierorders/3")


@pytest.mark.asyncio
async def test_build_proposal_document_strips_base64_content():
    client = _client()
    client.get_proposal_by_id = AsyncMock(return_value={"ref": "PR1", "last_main_doc": "PR1/PR1.pdf"})
    client.request = AsyncMock(return_value={
        "filename": "PR1.pdf", "content-type": "application/pdf",
        "filesize": 90000, "content": "BASE64BLOB", "encoding": "base64",
    })

    result = await client.build_proposal_document(7)

    method, endpoint = client.request.call_args.args[:2]
    assert (method, endpoint) == ("PUT", "documents/builddoc")
    sent = client.request.call_args.kwargs["data"]
    assert sent["modulepart"] == "propal" and sent["original_file"] == "PR1/PR1.pdf"
    assert "content" not in result           # base64 blob dropped
    assert result["filename"] == "PR1.pdf"   # metadata kept


@pytest.mark.asyncio
async def test_build_proposal_document_falls_back_to_ref_path():
    client = _client()
    client.get_proposal_by_id = AsyncMock(return_value={"ref": "PR2", "last_main_doc": ""})
    client.request = AsyncMock(return_value={"filename": "PR2.pdf"})

    await client.build_proposal_document(9)

    assert client.request.call_args.kwargs["data"]["original_file"] == "PR2/PR2.pdf"
