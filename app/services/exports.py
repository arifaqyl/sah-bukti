import csv
import io
import json

from app.db.store import get_db


def export_invoices(business_id: int, export_format: str) -> str:
    rows = _fetch_rows(
        """
        SELECT
            i.id,
            i.invoice_number,
            c.name AS customer_name,
            c.phone AS customer_phone,
            i.total,
            i.payment_method,
            i.payment_status,
            i.due_date,
            i.created_at,
            i.paid_at
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE i.business_id = ?
        ORDER BY i.created_at DESC, i.id DESC
        """,
        (business_id,),
    )
    if export_format == "json":
        return json.dumps(rows, indent=2)
    return _rows_to_csv(
        [
            "id",
            "invoice_number",
            "customer_name",
            "customer_phone",
            "total",
            "payment_method",
            "payment_status",
            "due_date",
            "created_at",
            "paid_at",
        ],
        rows,
    )


def export_daily_ops(business_id: int, export_format: str) -> str:
    rows = _fetch_rows(
        """
        SELECT
            id,
            date,
            total_cash,
            total_qr,
            total_transfer,
            total_orders,
            total_revenue,
            created_at
        FROM daily_ops
        WHERE business_id = ?
        ORDER BY date DESC, id DESC
        """,
        (business_id,),
    )
    if export_format == "json":
        return json.dumps(rows, indent=2)
    return _rows_to_csv(
        [
            "id",
            "date",
            "total_cash",
            "total_qr",
            "total_transfer",
            "total_orders",
            "total_revenue",
            "created_at",
        ],
        rows,
    )


def export_inventory(business_id: int, export_format: str) -> str:
    rows = _fetch_rows(
        """
        SELECT
            id,
            name,
            unit,
            current_stock,
            reorder_point,
            supplier,
            last_updated
        FROM ingredients
        WHERE business_id = ?
        ORDER BY name ASC, id DESC
        """,
        (business_id,),
    )
    if export_format == "json":
        return json.dumps(rows, indent=2)
    return _rows_to_csv(
        [
            "id",
            "name",
            "unit",
            "current_stock",
            "reorder_point",
            "supplier",
            "last_updated",
        ],
        rows,
    )


def _fetch_rows(query: str, params: tuple) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _rows_to_csv(fieldnames: list[str], rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in fieldnames})
    return output.getvalue()
