"""Capability gating for the Dolibarr MCP server.

The server exposes read *and* write tools, but a given Dolibarr API token only
carries the rights granted to its user. This module discovers those rights from
``GET /users/info?includepermissions=1`` and maps every MCP tool to the Dolibarr
permission(s) it needs, so unauthorized calls are refused with an explicit
message instead of an opaque Dolibarr 403.

Discovering the rights tree itself requires the API user to hold at least
``user.self.creer`` ("Create/modify its own user info") - otherwise
``/users/info`` returns 403. That permission is therefore mandatory for any MCP
user and is documented as an install prerequisite.
"""

from __future__ import annotations

from typing import Any, Optional

from .dolibarr_client import DolibarrClient, DolibarrAPIError
from .permissions_catalog import CORE_PERMISSIONS

# Sentinel: the tool is reserved to Dolibarr administrators (no single permission
# path gates it - e.g. the arbitrary raw API passthrough).
ADMIN_ONLY = "__admin__"

# Tool name -> list of required Dolibarr permission paths (AND semantics).
# An empty list means the tool is always available (system/bootstrap tools).
# Paths follow the catalog in permissions_catalog.py: <rights_class>.<perms>[.<subperms>].
#
# Each tool maps to the permission its underlying REST endpoint actually enforces
# (the minimal right), so we never refuse a call Dolibarr would have accepted.
TOOL_PERMISSIONS: dict[str, list[str]] = {
    # System & bootstrap - always available.
    "test_connection": [],
    "get_status": [],
    # Public tax dictionary lookup - no special right required.
    "get_vat_rates": [],
    # Search / resolve (read).
    "search_products_by_ref": ["produit.lire"],
    "search_products_by_label": ["produit.lire"],
    "resolve_product_ref": ["produit.lire"],
    "search_customers": ["societe.lire"],
    "search_suppliers": ["societe.lire"],
    "get_product_purchase_prices": ["produit.lire"],
    "add_product_purchase_price": ["produit.creer"],
    "delete_product_purchase_price": ["produit.creer"],
    # Users.
    "get_users": ["user.user.lire"],
    "get_user_by_id": ["user.user.lire"],
    "create_user": ["user.user.creer"],
    "update_user": ["user.user.creer"],
    "delete_user": ["user.user.supprimer"],
    # Customers / third parties.
    "get_customers": ["societe.lire"],
    "get_customer_by_id": ["societe.lire"],
    "create_customer": ["societe.creer"],
    "update_customer": ["societe.creer"],
    "delete_customer": ["societe.supprimer"],
    # Products.
    "get_products": ["produit.lire"],
    "get_product_by_id": ["produit.lire"],
    "create_product": ["produit.creer"],
    "update_product": ["produit.creer"],
    "delete_product": ["produit.supprimer"],
    # Invoices.
    "get_invoices": ["facture.lire"],
    "get_invoice_by_id": ["facture.lire"],
    "create_invoice": ["facture.creer"],
    "create_invoice_draft": ["facture.creer"],
    "update_invoice": ["facture.creer"],
    "delete_invoice": ["facture.supprimer"],
    "add_invoice_line": ["facture.creer"],
    "update_invoice_line": ["facture.creer"],
    # Deleting a line is a modification of the invoice, not deletion of it.
    "delete_invoice_line": ["facture.creer"],
    "set_invoice_project": ["facture.creer"],
    "validate_invoice": ["facture.creer"],
    "search_invoices": ["facture.lire"],
    "set_invoice_to_draft": ["facture.creer"],
    "add_payment_to_invoice": ["facture.paiement"],
    # Proposals (quotes / devis). rights_class is `propale` in the catalogue.
    "get_proposals": ["propale.lire"],
    "get_proposal_by_id": ["propale.lire"],
    "create_proposal": ["propale.creer"],
    "update_proposal": ["propale.creer"],
    "delete_proposal": ["propale.supprimer"],
    "add_proposal_line": ["propale.creer"],
    "update_proposal_line": ["propale.creer"],
    "delete_proposal_line": ["propale.creer"],
    "validate_proposal": ["propale.creer"],
    "sign_proposal": ["propale.creer"],
    "convert_proposal_to_order": ["propale.creer"],
    "build_proposal_document": ["propale.lire"],
    # Supplier (purchase) orders. rights_class is `fournisseur`, sub `commande`.
    "get_supplier_orders": ["fournisseur.commande.lire"],
    "get_supplier_order_by_id": ["fournisseur.commande.lire"],
    "create_supplier_order": ["fournisseur.commande.creer"],
    "update_supplier_order": ["fournisseur.commande.creer"],
    "delete_supplier_order": ["fournisseur.commande.supprimer"],
    # Orders.
    "get_orders": ["commande.lire"],
    "get_order_by_id": ["commande.lire"],
    "create_order": ["commande.creer"],
    "update_order": ["commande.creer"],
    "delete_order": ["commande.supprimer"],
    # Line edits modify the order, gated like order creation (as invoice lines are).
    "add_order_line": ["commande.creer"],
    "update_order_line": ["commande.creer"],
    "delete_order_line": ["commande.creer"],
    # Contacts (nested under the societe module).
    "get_contacts": ["societe.contact.lire"],
    "get_contact_by_id": ["societe.contact.lire"],
    "create_contact": ["societe.contact.creer"],
    "update_contact": ["societe.contact.creer"],
    "delete_contact": ["societe.contact.supprimer"],
    # Projects.
    "get_projects": ["projet.lire"],
    "get_project_by_id": ["projet.lire"],
    "search_projects": ["projet.lire"],
    "create_project": ["projet.creer"],
    "update_project": ["projet.creer"],
    "delete_project": ["projet.supprimer"],
    "get_project_contacts": ["projet.lire"],
    "add_project_contact": ["projet.creer"],
    "remove_project_contact": ["projet.creer"],
    # Categories.
    "get_categories": ["categorie.lire"],
    "search_categories": ["categorie.lire"],
    "link_category": ["categorie.creer"],
    "unlink_category": ["categorie.creer"],
    "get_products_by_category": ["categorie.lire"],
    "get_product_categories": ["produit.lire"],
    # Analytics run over a direct read-only SQL connection, so Dolibarr rights do
    # not constrain them technically; we still gate them by policy on the matching
    # read permission of the API user.
    "get_top_selling_products": ["facture.lire"],
    "get_sales_summary": ["facture.lire"],
    "get_low_stock_products": ["produit.lire"],
    # Arbitrary passthrough - administrators only.
    "dolibarr_raw_api": [ADMIN_ONLY],
}


class MissingUserInfoPermission(Exception):
    """Raised when ``/users/info`` is forbidden for the configured API user.

    This means the user lacks ``user.self.creer`` (and is not an admin), so the
    server cannot discover its capabilities and must refuse to start.
    """


def _is_granted(value: Any) -> bool:
    """Interpret a Dolibarr rights leaf; note ``"0"`` is a *false* string."""
    return value in (1, "1", True)


class Capabilities:
    """Resolved rights of the Dolibarr user behind the configured API token."""

    def __init__(self, admin: bool, rights: dict[str, Any]):
        self.admin = admin
        self.rights = rights or {}

    def has(self, permission_path: str) -> bool:
        """Return True if the user holds *permission_path* (admins hold everything)."""
        if self.admin:
            return True
        node: Any = self.rights
        for segment in permission_path.split("."):
            if not isinstance(node, dict) or segment not in node:
                return False
            node = node[segment]
        return _is_granted(node)

    def missing(self, tool: str) -> list[str]:
        """Return the required permissions the user is missing for *tool*."""
        required = TOOL_PERMISSIONS.get(tool)
        if not required:
            return []
        if ADMIN_ONLY in required:
            return [] if self.admin else [ADMIN_ONLY]
        return [path for path in required if not self.has(path)]

    def is_allowed(self, tool: str) -> bool:
        """Return True if the user can run *tool*.

        Unknown tools fail open (allowed): the consistency test guarantees every
        registered tool is mapped, so an unmapped name is not a silent gate.
        """
        if tool not in TOOL_PERMISSIONS:
            return True
        return not self.missing(tool)

    def denial_message(self, tool: str) -> str:
        """Human-readable reason why *tool* is refused, naming the missing rights."""
        missing = self.missing(tool)
        if not missing:
            return f"Tool '{tool}' is allowed for the current Dolibarr user."
        if missing == [ADMIN_ONLY]:
            return (
                f"Tool '{tool}' is reserved to Dolibarr administrators, and the "
                f"connected API user is not an administrator."
            )
        described = ", ".join(f"{path} ({_label_for(path)})" for path in missing)
        return (
            f"The connected Dolibarr user is not allowed to run '{tool}'. "
            f"Missing permission(s): {described}."
        )

    @classmethod
    async def fetch(cls, client: DolibarrClient) -> "Capabilities":
        """Discover the API user's rights via ``/users/info?includepermissions=1``."""
        try:
            info = await client.request(
                "GET", "users/info", params={"includepermissions": 1}
            )
        except DolibarrAPIError as exc:
            if exc.status_code == 403:
                raise MissingUserInfoPermission(
                    "GET /users/info returned 403: the MCP API user must have the "
                    "'Create/modify its own user info' permission (user.self.creer)."
                ) from exc
            raise
        return cls(admin=_is_granted(info.get("admin")), rights=info.get("rights") or {})


def _label_for(permission_path: str) -> str:
    """Return the catalog label for a permission path, or the path itself."""
    module = permission_path.split(".", 1)[0]
    entry = CORE_PERMISSIONS.get(module)
    if entry:
        return entry["permissions"].get(permission_path, permission_path)
    return permission_path
