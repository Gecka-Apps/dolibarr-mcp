"""Analytics queries using direct database access.

These queries provide aggregated data (top sellers, sales summaries,
low stock alerts) that cannot be efficiently obtained through the
Dolibarr REST API.

Requires the ``aiomysql`` package and database credentials in config.
"""

import logging
from typing import Any, Dict, List, Optional

from .config import Config

logger = logging.getLogger(__name__)

try:
    import aiomysql
    HAS_AIOMYSQL = True
except ImportError:
    HAS_AIOMYSQL = False


class AnalyticsUnavailableError(Exception):
    """Raised when analytics features are not configured."""


async def _get_connection(config: Config):
    """Create a single async MySQL connection."""
    if not HAS_AIOMYSQL:
        raise AnalyticsUnavailableError(
            "Analytics requires the 'aiomysql' package. "
            "Install with: pip install dolibarr-mcp[analytics]"
        )
    if not config.db_available:
        raise AnalyticsUnavailableError(
            "Database not configured. Set DB_HOST, DB_NAME, DB_USER, "
            "DB_PASSWORD in your .env file to enable analytics."
        )
    return await aiomysql.connect(
        host=config.db_host,
        port=config.db_port,
        db=config.db_name,
        user=config.db_user,
        password=config.db_password,
        charset="utf8mb4",
        autocommit=True,
    )


async def _fetch_all(config: Config, query: str, args: tuple = ()) -> List[Dict[str, Any]]:
    """Execute a read-only query and return rows as dicts."""
    conn = await _get_connection(config)
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(query, args)
            rows = await cur.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()


async def get_top_selling_products(
    config: Config,
    *,
    period_months: int = 12,
    limit: int = 20,
    category_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Get top selling products by quantity sold in invoices.

    Args:
        period_months: How many months back to look (default: 12).
        limit: Number of products to return (default: 20).
        category_id: Optional category ID to filter products.
    """
    pfx = config.db_prefix

    category_join = ""
    category_where = ""
    if category_id is not None:
        category_join = (
            f"JOIN {pfx}categorie_product cp ON cp.fk_product = p.rowid"
        )
        category_where = "AND cp.fk_categorie = %s"

    query = f"""
        SELECT
            p.rowid AS id,
            p.ref,
            p.label,
            CAST(SUM(fd.qty) AS SIGNED) AS total_qty_sold,
            COUNT(DISTINCT f.rowid) AS nb_invoices,
            ROUND(SUM(fd.total_ht), 2) AS total_revenue_ht,
            ROUND(SUM(fd.total_ttc), 2) AS total_revenue_ttc
        FROM {pfx}facturedet fd
        JOIN {pfx}facture f ON fd.fk_facture = f.rowid
        JOIN {pfx}product p ON fd.fk_product = p.rowid
        {category_join}
        WHERE f.fk_statut > 0
          AND f.datef >= DATE_SUB(NOW(), INTERVAL %s MONTH)
          {category_where}
        GROUP BY p.rowid
        ORDER BY total_qty_sold DESC
        LIMIT %s
    """

    args = (period_months,)
    if category_id is not None:
        args = (period_months, category_id)
    args = args + (limit,)

    rows = await _fetch_all(config, query, args)

    return {
        "period_months": period_months,
        "category_id": category_id,
        "count": len(rows),
        "items": rows,
    }


async def get_sales_summary(
    config: Config,
    *,
    period_months: int = 12,
    group_by: str = "month",
) -> Dict[str, Any]:
    """Get sales summary grouped by month or year.

    Args:
        period_months: How many months back to look (default: 12).
        group_by: Grouping period - 'month' or 'year' (default: month).
    """
    pfx = config.db_prefix

    if group_by == "year":
        date_format = "%Y"
        group_label = "year"
    else:
        date_format = "%Y-%m"
        group_label = "month"

    query = f"""
        SELECT
            DATE_FORMAT(f.datef, %s) AS period,
            COUNT(*) AS nb_invoices,
            COUNT(DISTINCT f.fk_soc) AS nb_customers,
            ROUND(SUM(f.total_ht), 2) AS total_ht,
            ROUND(SUM(f.total_tva), 2) AS total_tva,
            ROUND(SUM(f.total_ttc), 2) AS total_ttc
        FROM {pfx}facture f
        WHERE f.fk_statut > 0
          AND f.datef >= DATE_SUB(NOW(), INTERVAL %s MONTH)
        GROUP BY DATE_FORMAT(f.datef, %s)
        ORDER BY period DESC
    """

    rows = await _fetch_all(config, query, (date_format, period_months, date_format))

    return {
        "period_months": period_months,
        "group_by": group_label,
        "count": len(rows),
        "items": rows,
    }


async def get_low_stock_products(
    config: Config,
    *,
    limit: int = 20,
    include_zero_stock: bool = True,
) -> Dict[str, Any]:
    """Get products with stock at or below their alert threshold.

    Args:
        limit: Number of products to return (default: 20).
        include_zero_stock: Include products with zero/null stock (default: True).
    """
    pfx = config.db_prefix

    stock_condition = "p.stock <= p.seuil_stock_alerte"
    if include_zero_stock:
        stock_condition = (
            "(p.stock <= p.seuil_stock_alerte OR p.stock IS NULL OR p.stock = 0)"
        )

    query = f"""
        SELECT
            p.rowid AS id,
            p.ref,
            p.label,
            COALESCE(p.stock, 0) AS stock_reel,
            COALESCE(p.seuil_stock_alerte, 0) AS seuil_stock_alerte,
            COALESCE(p.desiredstock, 0) AS desiredstock
        FROM {pfx}product p
        WHERE p.tosell = 1
          AND p.fk_product_type = 0
          AND p.seuil_stock_alerte IS NOT NULL
          AND p.seuil_stock_alerte > 0
          AND {stock_condition}
        ORDER BY (COALESCE(p.stock, 0) - p.seuil_stock_alerte) ASC
        LIMIT %s
    """

    rows = await _fetch_all(config, query, (limit,))

    return {
        "count": len(rows),
        "items": rows,
    }
