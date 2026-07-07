"""Tests for the capability gating layer."""

import pytest

from dolibarr_mcp.capabilities import (
    ADMIN_ONLY,
    Capabilities,
    MissingUserInfoPermission,
    TOOL_PERMISSIONS,
)
from dolibarr_mcp.dolibarr_client import DolibarrAPIError
from dolibarr_mcp.permissions_catalog import permission_exists


# ---------------------------------------------------------------------------
# Fixtures — rights trees mirroring real /users/info responses
# ---------------------------------------------------------------------------

# The restricted "mcp" user: invoices read+write (no delete), read-only third
# parties and contacts, plus the mandatory self.creer. Values are strings, as
# Dolibarr serializes them ("0" is a *false* string).
MCP_RIGHTS = {
    "facture": {"lire": "1", "creer": "1", "supprimer": "0"},
    "propal": {"lire": "1", "creer": "1"},
    "societe": {"lire": "1", "contact": {"lire": "1", "creer": "0"}},
    "produit": {"lire": "0"},
    "user": {"self": {"creer": "1"}},
}


def mcp_caps():
    return Capabilities(admin=False, rights=MCP_RIGHTS)


def admin_caps():
    return Capabilities(admin=True, rights={})


# ---------------------------------------------------------------------------
# Mapping integrity
# ---------------------------------------------------------------------------

def test_every_mapped_permission_exists_in_catalog():
    for tool, required in TOOL_PERMISSIONS.items():
        for path in required:
            if path == ADMIN_ONLY:
                continue
            assert permission_exists(path), f"{tool} references unknown permission {path!r}"


def test_registered_tools_are_all_mapped():
    """Guards against adding a tool without gating it (fail-open safety net)."""
    from dolibarr_mcp.tools import ALL_TOOLS

    registered = {tool.name for tool in ALL_TOOLS}
    assert registered, "could not find any registered tools"
    assert registered == set(TOOL_PERMISSIONS), (
        f"unmapped: {registered - set(TOOL_PERMISSIONS)}, "
        f"stale: {set(TOOL_PERMISSIONS) - registered}"
    )


# ---------------------------------------------------------------------------
# Admin bypass
# ---------------------------------------------------------------------------

def test_admin_is_allowed_everything():
    caps = admin_caps()
    assert all(caps.is_allowed(tool) for tool in TOOL_PERMISSIONS)
    assert caps.has("facture.supprimer")
    assert caps.is_allowed("dolibarr_raw_api")


# ---------------------------------------------------------------------------
# Restricted user gating
# ---------------------------------------------------------------------------

def test_string_zero_is_not_granted():
    caps = mcp_caps()
    assert caps.has("facture.creer") is True
    assert caps.has("facture.supprimer") is False  # "0" must read as denied
    assert caps.has("produit.lire") is False


def test_read_and_write_are_gated_independently():
    caps = mcp_caps()
    assert caps.is_allowed("get_invoices")       # facture.lire
    assert caps.is_allowed("create_invoice")     # facture.creer
    assert not caps.is_allowed("delete_invoice")  # facture.supprimer missing


def test_missing_module_hides_all_its_tools():
    caps = mcp_caps()
    for tool in ("get_products", "create_product", "delete_product",
                 "get_orders", "get_projects", "get_categories"):
        assert not caps.is_allowed(tool)


def test_nested_contact_permissions():
    caps = mcp_caps()
    assert caps.is_allowed("get_contacts")         # societe.contact.lire
    assert not caps.is_allowed("create_contact")   # societe.contact.creer = "0"


def test_system_tools_always_available():
    caps = Capabilities(admin=False, rights={})
    assert caps.is_allowed("test_connection")
    assert caps.is_allowed("get_status")


def test_raw_api_requires_admin():
    assert not mcp_caps().is_allowed("dolibarr_raw_api")
    assert admin_caps().is_allowed("dolibarr_raw_api")


def test_expected_visible_tool_count_for_mcp_user():
    caps = mcp_caps()
    visible = {tool for tool in TOOL_PERMISSIONS if caps.is_allowed(tool)}
    assert "set_invoice_project" in visible      # facture.creer
    assert "get_sales_summary" in visible         # analytics gated on facture.lire
    assert "get_low_stock_products" not in visible  # needs produit.lire
    assert "dolibarr_raw_api" not in visible


# ---------------------------------------------------------------------------
# Denial messages
# ---------------------------------------------------------------------------

def test_denial_message_names_missing_permission():
    msg = mcp_caps().denial_message("create_product")
    assert "create_product" in msg
    assert "produit.creer" in msg
    assert "Create/modify products" in msg  # label from the catalog


def test_denial_message_for_admin_only_tool():
    msg = mcp_caps().denial_message("dolibarr_raw_api")
    assert "administrator" in msg.lower()


def test_missing_returns_only_unsatisfied_paths():
    caps = mcp_caps()
    assert caps.missing("get_invoices") == []
    assert caps.missing("delete_invoice") == ["facture.supprimer"]


# ---------------------------------------------------------------------------
# fetch() error handling
# ---------------------------------------------------------------------------

class _FakeClient:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error

    async def request(self, method, endpoint, params=None):
        if self._error:
            raise self._error
        return self._response


@pytest.mark.asyncio
async def test_fetch_raises_prerequisite_error_on_403():
    client = _FakeClient(error=DolibarrAPIError("Forbidden", status_code=403))
    with pytest.raises(MissingUserInfoPermission):
        await Capabilities.fetch(client)


@pytest.mark.asyncio
async def test_fetch_reraises_other_errors():
    client = _FakeClient(error=DolibarrAPIError("Boom", status_code=500))
    with pytest.raises(DolibarrAPIError):
        await Capabilities.fetch(client)


@pytest.mark.asyncio
async def test_fetch_parses_admin_and_rights():
    client = _FakeClient(response={"admin": "1", "rights": {"facture": {"lire": "1"}}})
    caps = await Capabilities.fetch(client)
    assert caps.admin is True
    assert caps.has("facture.lire")
