"""Tests for the response_shaper module."""

import json
import pytest

from dolibarr_mcp.response_shaper import (
    ENTITY_FIELD_SETS,
    INVOICE_LINE_SUMMARY,
    TOOL_RESPONSE_CONFIG,
    filter_fields,
    filter_lines,
    format_response,
    get_field_list,
    get_properties_param,
)


# ---------------------------------------------------------------------------
# Fixtures — realistic Dolibarr API objects
# ---------------------------------------------------------------------------

def _make_product(**overrides):
    """Build a realistic product dict with 20+ fields."""
    product = {
        "id": "42",
        "ref": "PROD-001",
        "label": "Widget Pro",
        "description": "A professional widget",
        "price": "100.00000000",
        "price_ttc": "122.00000000",
        "price_min": "80.00000000",
        "price_min_ttc": "97.60000000",
        "tva_tx": "22.000",
        "status": "1",
        "type": "0",
        "stock_reel": "15",
        "barcode": "1234567890",
        "weight": "0.5",
        "tosell": "1",
        "tobuy": "1",
        "date_creation": 1650350783,
        "date_modification": 1650350813,
        # Fields that should be stripped in summary/standard
        "entity": "1",
        "module": None,
        "import_key": None,
        "array_options": [],
        "array_languages": None,
        "contacts_ids": None,
        "linkedObjectsIds": None,
        "canvas": "",
        "multicurrency_code": None,
        "multicurrency_total_ht": None,
        "note_private": "",
        "note_public": None,
        "specimen": 0,
        "extraparams": [],
        "fk_user_creat": None,
        "fk_user_modif": None,
    }
    product.update(overrides)
    return product


def _make_invoice(**overrides):
    """Build a realistic invoice dict."""
    invoice = {
        "id": "99",
        "ref": "FA2401-0001",
        "ref_ext": None,
        "socid": "10",
        "date": 1706745600,
        "date_lim_reglement": 1709424000,
        "total_ht": "1000.00000000",
        "total_tva": "220.00000000",
        "total_ttc": "1220.00000000",
        "paye": "0",
        "status": "1",
        "fk_project": "5",
        "note_public": "Test invoice",
        "date_creation": 1706745600,
        "date_modification": 1706745600,
        # Bloat fields
        "entity": "1",
        "module": None,
        "array_options": [],
        "contacts_ids": None,
        "linkedObjectsIds": None,
        "multicurrency_code": None,
        "multicurrency_total_ht": None,
        "multicurrency_total_tva": None,
        "multicurrency_total_ttc": None,
        "note_private": "",
        "specimen": 0,
        "lines": [_make_invoice_line()],
    }
    invoice.update(overrides)
    return invoice


def _make_invoice_line(**overrides):
    """Build a realistic invoice line."""
    line = {
        "id": "200",
        "fk_product": "42",
        "product_ref": "PROD-001",
        "product_label": "Widget Pro",
        "qty": "2",
        "subprice": "500.00000000",
        "total_ht": "1000.00000000",
        "total_ttc": "1220.00000000",
        "tva_tx": "22.000",
        "product_type": "0",
        "description": "2x Widget Pro",
        # Bloat
        "entity": None,
        "module": None,
        "array_options": [],
        "contacts_ids": None,
        "linkedObjectsIds": None,
        "multicurrency_total_ht": "1000.00",
        "multicurrency_total_ttc": "1220.00",
        "fk_accounting_account": None,
        "fk_code_ventilation": "0",
        "fk_parent_line": None,
        "specimen": 0,
    }
    line.update(overrides)
    return line


# ---------------------------------------------------------------------------
# get_field_list
# ---------------------------------------------------------------------------

class TestGetFieldList:
    def test_summary_returns_expected_fields(self):
        fields = get_field_list("product", "summary")
        assert fields is not None
        assert "id" in fields
        assert "ref" in fields
        assert "label" in fields
        assert "price" in fields
        # Should NOT include bloat
        assert "array_options" not in fields

    def test_full_returns_none(self):
        assert get_field_list("product", "full") is None

    def test_unknown_entity_returns_none(self):
        assert get_field_list("unknown_thing", "summary") is None

    def test_custom_fields_override(self):
        fields = get_field_list("product", "summary", custom_fields=["id", "ref"])
        assert fields == ["id", "ref"]

    def test_all_entity_types_have_summary_and_standard(self):
        for entity_type, sets in ENTITY_FIELD_SETS.items():
            assert "summary" in sets, f"{entity_type} missing summary"
            assert "standard" in sets, f"{entity_type} missing standard"
            assert "full" in sets, f"{entity_type} missing full"
            assert sets["full"] is None, f"{entity_type} full should be None"


# ---------------------------------------------------------------------------
# get_properties_param
# ---------------------------------------------------------------------------

class TestGetPropertiesParam:
    def test_summary_returns_csv(self):
        props = get_properties_param("product", "summary")
        assert props is not None
        assert "id" in props
        assert "ref" in props
        assert "," in props

    def test_full_returns_none(self):
        assert get_properties_param("product", "full") is None

    def test_excludes_lines_from_properties(self):
        props = get_properties_param("invoice", "standard")
        assert props is not None
        assert "lines" not in props.split(",")
        assert "id" in props.split(",")

    def test_custom_fields(self):
        props = get_properties_param("product", "summary", custom_fields=["id", "ref", "label"])
        assert props == "id,ref,label"


# ---------------------------------------------------------------------------
# filter_fields
# ---------------------------------------------------------------------------

class TestFilterFields:
    def test_filters_to_specified_fields(self):
        product = _make_product()
        result = filter_fields(product, ["id", "ref", "label"])
        assert set(result.keys()) == {"id", "ref", "label"}

    def test_none_fields_passes_through(self):
        product = _make_product()
        result = filter_fields(product, None)
        assert result is product

    def test_missing_fields_are_ignored(self):
        product = _make_product()
        result = filter_fields(product, ["id", "nonexistent_field"])
        assert "id" in result
        assert "nonexistent_field" not in result


# ---------------------------------------------------------------------------
# filter_lines
# ---------------------------------------------------------------------------

class TestFilterLines:
    def test_filters_line_fields(self):
        lines = [_make_invoice_line()]
        result = filter_lines(lines, INVOICE_LINE_SUMMARY)
        assert len(result) == 1
        # Should keep summary fields
        assert "id" in result[0]
        assert "product_ref" in result[0]
        assert "qty" in result[0]
        # Should strip bloat
        assert "array_options" not in result[0]
        assert "multicurrency_total_ht" not in result[0]

    def test_none_passes_through(self):
        lines = [_make_invoice_line()]
        result = filter_lines(lines, None)
        assert result is lines


# ---------------------------------------------------------------------------
# format_response — list tools
# ---------------------------------------------------------------------------

class TestFormatResponseList:
    def test_list_response_has_envelope(self):
        products = [_make_product() for _ in range(3)]
        result = format_response(
            products, tool_name="get_products", arguments={},
        )
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "count" in data
        assert "page" in data
        assert "items" in data
        assert data["count"] == 3

    def test_list_summary_strips_fields(self):
        products = [_make_product()]
        result = format_response(
            products, tool_name="get_products", arguments={},
        )
        data = json.loads(result[0].text)
        item = data["items"][0]
        # Summary fields present
        assert "id" in item
        assert "ref" in item
        assert "label" in item
        # Bloat fields stripped
        assert "array_options" not in item
        assert "module" not in item
        assert "specimen" not in item

    def test_list_compact_json(self):
        products = [_make_product()]
        result = format_response(
            products, tool_name="get_products", arguments={},
        )
        text = result[0].text
        # Compact JSON should not have indentation
        assert "\n  " not in text

    def test_list_custom_fields(self):
        products = [_make_product()]
        result = format_response(
            products, tool_name="get_products",
            arguments={"fields": "id,ref"},
        )
        data = json.loads(result[0].text)
        item = data["items"][0]
        assert set(item.keys()) == {"id", "ref"}

    def test_list_pagination_info(self):
        products = [_make_product()]
        result = format_response(
            products, tool_name="get_products",
            arguments={"page": 3},
        )
        data = json.loads(result[0].text)
        assert data["page"] == 3

    def test_invoice_lines_filtered_in_summary(self):
        """In summary mode, invoice lines should be excluded (properties won't include them)."""
        invoices = [_make_invoice()]
        result = format_response(
            invoices, tool_name="get_invoices", arguments={},
        )
        data = json.loads(result[0].text)
        item = data["items"][0]
        # Summary does not include lines field (not in summary field set)
        assert "lines" not in item


# ---------------------------------------------------------------------------
# format_response — detail tools
# ---------------------------------------------------------------------------

class TestFormatResponseDetail:
    def test_detail_returns_all_fields(self):
        product = _make_product()
        result = format_response(
            product, tool_name="get_product_by_id", arguments={},
        )
        data = json.loads(result[0].text)
        # Full mode: all original keys present
        assert "array_options" in data
        assert "module" in data

    def test_detail_with_custom_fields(self):
        product = _make_product()
        result = format_response(
            product, tool_name="get_product_by_id",
            arguments={"fields": "id,ref,label"},
        )
        data = json.loads(result[0].text)
        assert set(data.keys()) == {"id", "ref", "label"}

    def test_invoice_detail_keeps_full_lines(self):
        invoice = _make_invoice()
        result = format_response(
            invoice, tool_name="get_invoice_by_id", arguments={},
        )
        data = json.loads(result[0].text)
        assert "lines" in data
        line = data["lines"][0]
        # Full mode: line bloat preserved
        assert "array_options" in line


# ---------------------------------------------------------------------------
# format_response — search tools
# ---------------------------------------------------------------------------

class TestFormatResponseSearch:
    def test_search_uses_standard_fields(self):
        products = [_make_product()]
        result = format_response(
            products, tool_name="search_products_by_label", arguments={},
        )
        data = json.loads(result[0].text)
        item = data["items"][0]
        # Standard includes description
        assert "description" in item
        # But not bloat
        assert "array_options" not in item


# ---------------------------------------------------------------------------
# format_response — truncation
# ---------------------------------------------------------------------------

class TestFormatResponseTruncation:
    def test_truncation_when_too_large(self):
        # Create many products to exceed limit
        products = [_make_product(id=str(i), ref=f"PROD-{i:04d}") for i in range(200)]
        result = format_response(
            products, tool_name="get_products", arguments={},
            max_response_chars=5000,
        )
        data = json.loads(result[0].text)
        assert data["truncated"] is True
        assert data["showing"] < data["count"]
        assert data["count"] == 200
        assert len(data["items"]) == data["showing"]
        assert "message" in data

    def test_no_truncation_when_small(self):
        products = [_make_product()]
        result = format_response(
            products, tool_name="get_products", arguments={},
        )
        data = json.loads(result[0].text)
        assert "truncated" not in data


# ---------------------------------------------------------------------------
# format_response — unknown tools (fallback)
# ---------------------------------------------------------------------------

class TestFormatResponseFallback:
    def test_unknown_tool_passes_through(self):
        result = format_response(
            {"status": "ok"}, tool_name="test_connection", arguments={},
        )
        data = json.loads(result[0].text)
        assert data == {"status": "ok"}

    def test_scalar_result(self):
        result = format_response(42, tool_name="unknown", arguments={})
        assert result[0].text == "42"


# ---------------------------------------------------------------------------
# Size reduction validation
# ---------------------------------------------------------------------------

class TestSizeReduction:
    def test_product_summary_is_much_smaller_than_full(self):
        product = _make_product()
        full_size = len(json.dumps(product))

        result = format_response(
            [product], tool_name="get_products", arguments={},
        )
        summary_size = len(result[0].text)

        # Summary should be significantly smaller (at least 50% reduction)
        assert summary_size < full_size * 0.6, (
            f"Summary ({summary_size}) should be much smaller than full ({full_size})"
        )

    def test_invoice_summary_excludes_lines(self):
        invoice = _make_invoice()
        full_size = len(json.dumps(invoice))

        result = format_response(
            [invoice], tool_name="get_invoices", arguments={},
        )
        summary_size = len(result[0].text)

        assert summary_size < full_size * 0.5, (
            f"Invoice summary ({summary_size}) should be much smaller than full ({full_size})"
        )


# ---------------------------------------------------------------------------
# TOOL_RESPONSE_CONFIG consistency
# ---------------------------------------------------------------------------

class TestToolConfig:
    def test_all_list_tools_have_entity_type(self):
        for tool_name, config in TOOL_RESPONSE_CONFIG.items():
            assert "entity_type" in config, f"{tool_name} missing entity_type"
            assert config["entity_type"] in ENTITY_FIELD_SETS, (
                f"{tool_name} references unknown entity_type: {config['entity_type']}"
            )

    def test_list_tools_are_lists(self):
        list_tools = [k for k, v in TOOL_RESPONSE_CONFIG.items() if v.get("is_list")]
        assert len(list_tools) >= 7  # At least the 7 get_* tools

    def test_detail_tools_use_full(self):
        for tool_name, config in TOOL_RESPONSE_CONFIG.items():
            if not config.get("is_list") and "by_id" in tool_name:
                assert config["field_set"] == "full", (
                    f"{tool_name} detail tool should default to full"
                )
