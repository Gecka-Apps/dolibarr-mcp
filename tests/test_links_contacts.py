"""Tests for category links and project contact client methods."""

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
async def test_link_category_endpoint():
    client = _client()
    client.request = AsyncMock(return_value={"success": True})

    await client.link_category(10, "product", 42)

    assert client.request.call_args.args[:2] == ("POST", "categories/10/objects/product/42")


@pytest.mark.asyncio
async def test_unlink_category_endpoint():
    client = _client()
    client.request = AsyncMock(return_value={"success": True})

    await client.unlink_category(10, "customer", 5)

    assert client.request.call_args.args[:2] == ("DELETE", "categories/10/objects/customer/5")


@pytest.mark.asyncio
async def test_add_project_contact_payload():
    client = _client()
    client.request = AsyncMock(return_value=1)

    await client.add_project_contact(7, 3, "PROJECTLEADER", "internal")

    method, endpoint = client.request.call_args.args[:2]
    sent = client.request.call_args.kwargs["data"]
    assert (method, endpoint) == ("POST", "projects/7/contacts")
    assert sent == {"fk_socpeople": 3, "type_contact": "PROJECTLEADER", "source": "internal"}


@pytest.mark.asyncio
async def test_remove_project_contact_endpoint():
    client = _client()
    client.request = AsyncMock(return_value={"success": True})

    await client.remove_project_contact(7, 3, "PROJECTLEADER")

    assert client.request.call_args.args[:2] == ("DELETE", "projects/7/contact/3/PROJECTLEADER")
