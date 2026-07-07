"""Analytics tools must be advertised as unavailable when SQL is not configured."""

import pytest

import dolibarr_mcp.dolibarr_mcp_server as server
from dolibarr_mcp.analytics import ANALYTICS_TOOLS, analytics_available
from dolibarr_mcp.capabilities import Capabilities


@pytest.fixture
def admin_caps(monkeypatch):
    """Admin rights so permission is never the reason a tool is unavailable."""
    monkeypatch.setattr(server, "CAPABILITIES", Capabilities(admin=True, rights={}))


async def _tool_map():
    return {t.name: t for t in await server.handle_list_tools()}


@pytest.mark.asyncio
async def test_analytics_flagged_unavailable_when_db_absent(admin_caps, monkeypatch):
    monkeypatch.setattr(server, "ANALYTICS_AVAILABLE", False)
    tools = await _tool_map()
    for name in ANALYTICS_TOOLS:
        assert "[UNAVAILABLE" in tools[name].description
        assert "DB_HOST" in tools[name].description


@pytest.mark.asyncio
async def test_analytics_not_flagged_when_db_available(admin_caps, monkeypatch):
    monkeypatch.setattr(server, "ANALYTICS_AVAILABLE", True)
    tools = await _tool_map()
    for name in ANALYTICS_TOOLS:
        assert "[UNAVAILABLE" not in tools[name].description


@pytest.mark.asyncio
async def test_non_analytics_tool_unaffected_by_db(admin_caps, monkeypatch):
    monkeypatch.setattr(server, "ANALYTICS_AVAILABLE", False)
    tools = await _tool_map()
    assert "[UNAVAILABLE" not in tools["get_invoices"].description


def test_analytics_available_helper():
    class _Cfg:
        db_available = True

    class _CfgNo:
        db_available = False

    # Depends on aiomysql being importable; assert it tracks db_available given the
    # driver state rather than hardcoding an environment assumption.
    from dolibarr_mcp.analytics import HAS_AIOMYSQL

    assert analytics_available(_Cfg()) is (HAS_AIOMYSQL and True)
    assert analytics_available(_CfgNo()) is False
