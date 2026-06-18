import json

from app.db.store import get_db, get_default_business_id, utc_now
from app.services.customers import get_customer


def _row_to_invoice(row) -> dict:
    data = dict(row)
    items = data.get("items")
    if isinstance(items, str):
        try:
            data["items"] = json.loads(items)
        except json.JSONDecodeError:
            data["items"] = []
    return data


def create_invoice(payload: dict) -> dict:
    business_id = int(payload.get("business_id") or get_default_business_id())
    customer = get_customer(int(payload["customer_id"]))
    if not customer:
        raise ValueError("Customer not found")
    if int(customer["business_id"]) != business_id:
        raise ValueError("Customer does not belong to this business")

    now = utc_now()
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO invoices (
                business_id,
                customer_id,
                invoice_number,
                items,
                subtotal,
                tax,
                total,
                payment_method,
                payment_status,
                due_date,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                business_id,
                customer["id"],
                payload["invoice_number"],
                json.dumps(payload.get("items", [])),
                payload.get("subtotal", 0),
                payload.get("tax", 0),
                payload["total"],
                payload.get("payment_method", "pending"),
                payload.get("payment_status", "pending"),
                payload.get("due_date"),
                now,
                now,
            ),
        )
        invoice_id = cursor.lastrowid
        row = conn.execute(
            """
            SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email
            FROM invoices
            JOIN customers ON customers.id = invoices.customer_id
            WHERE invoices.id = ?
            """,
            (invoice_id,),
        ).fetchone()
    return _row_to_invoice(row)


def list_invoices() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email
            FROM invoices
            JOIN customers ON customers.id = invoices.customer_id
            ORDER BY invoices.id DESC
            """
        ).fetchall()
    return [_row_to_invoice(row) for row in rows]


def get_invoice(invoice_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email
            FROM invoices
            JOIN customers ON customers.id = invoices.customer_id
            WHERE invoices.id = ?
            """,
            (invoice_id,),
        ).fetchone()
    return _row_to_invoice(row) if row else None


def get_invoice_by_number(invoice_number: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email
            FROM invoices
            JOIN customers ON customers.id = invoices.customer_id
            WHERE invoices.invoice_number = ?
            """,
            (invoice_number,),
        ).fetchone()
    return _row_to_invoice(row) if row else None


def record_payment(
    invoice_id: int,
    amount: float,
    method: str,
    reference: str | None = None,
    confirmed: bool = True,
) -> dict | None:
    """Compatibility wrapper for payment recording flows outside the invoice API."""
    return record_invoice_payment(
        invoice_id,
        {
            "amount": amount,
            "method": method,
            "reference": reference,
            "confirmed": confirmed,
        },
    )


def update_invoice(invoice_id: int, payload: dict) -> dict | None:
    allowed_fields = {
        "customer_id": payload.get("customer_id"),
        "invoice_number": payload.get("invoice_number"),
        "items": json.dumps(payload["items"]) if payload.get("items") is not None else None,
        "subtotal": payload.get("subtotal"),
        "tax": payload.get("tax"),
        "total": payload.get("total"),
        "payment_method": payload.get("payment_method"),
        "payment_status": payload.get("payment_status"),
        "due_date": payload.get("due_date"),
    }
    updates = {key: value for key, value in allowed_fields.items() if value is not None}
    if not updates:
        return get_invoice(invoice_id)

    if "customer_id" in updates and not get_customer(int(updates["customer_id"])):
        raise ValueError("Customer not found")

    set_clause = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values())
    values.extend([utc_now(), invoice_id])

    with get_db() as conn:
        conn.execute(
            f"""
            UPDATE invoices
            SET {set_clause},
                updated_at = ?
            WHERE id = ?
            """,
            values,
        )
        row = conn.execute(
            """
            SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email
            FROM invoices
            JOIN customers ON customers.id = invoices.customer_id
            WHERE invoices.id = ?
            """,
            (invoice_id,),
        ).fetchone()
    return _row_to_invoice(row) if row else None


def record_invoice_payment(invoice_id: int, payload: dict) -> dict | None:
    invoice = get_invoice(invoice_id)
    if not invoice:
        return None

    now = utc_now()
    with get_db() as conn:
        reference = payload.get("reference")
        if reference:
            existing_payment = conn.execute(
                """
                SELECT id
                FROM payments
                WHERE invoice_id = ? AND reference = ?
                LIMIT 1
                """,
                (invoice_id, reference),
            ).fetchone()
            if existing_payment:
                row = conn.execute(
                    """
                    SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email
                    FROM invoices
                    JOIN customers ON customers.id = invoices.customer_id
                    WHERE invoices.id = ?
                    """,
                    (invoice_id,),
                ).fetchone()
                return _row_to_invoice(row) if row else None
        conn.execute(
            """
            INSERT INTO payments (invoice_id, amount, method, reference, confirmed, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                payload["amount"],
                payload["method"],
                payload.get("reference"),
                1 if payload.get("confirmed", True) else 0,
                now,
            ),
        )
        if payload.get("confirmed", True):
            totals = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS confirmed_total
                FROM payments
                WHERE invoice_id = ? AND confirmed = 1
                """,
                (invoice_id,),
            ).fetchone()
            confirmed_total = float(totals["confirmed_total"]) if totals else 0.0
            payment_status = "paid" if confirmed_total >= float(invoice["total"]) else "partial"
            conn.execute(
                """
                UPDATE invoices
                SET payment_status = ?,
                    payment_method = ?,
                    paid_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (payment_status, payload["method"], now, now, invoice_id),
            )
        row = conn.execute(
            """
            SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email
            FROM invoices
            JOIN customers ON customers.id = invoices.customer_id
            WHERE invoices.id = ?
            """,
            (invoice_id,),
        ).fetchone()
    return _row_to_invoice(row)


def get_daily_close_history() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM daily_ops
            ORDER BY date DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]
