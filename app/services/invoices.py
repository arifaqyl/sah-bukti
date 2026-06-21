import json

from app.db.store import get_db, utc_now
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
    if payload.get("business_id") is None:
        raise ValueError("business_id is required")
    business_id = int(payload["business_id"])
    customer = get_customer(int(payload["customer_id"]), business_id)
    if not customer:
        raise ValueError("Customer not found")

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
            SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email, customers.phone AS customer_phone
            FROM invoices
            JOIN customers ON customers.id = invoices.customer_id
            WHERE invoices.id = ?
            """,
            (invoice_id,),
        ).fetchone()
    return _row_to_invoice(row)


def list_invoices(business_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT 
                invoices.id, invoices.business_id, invoices.customer_id, invoices.invoice_number,
                invoices.items, invoices.subtotal, invoices.tax, invoices.total,
                invoices.payment_method, invoices.payment_status, invoices.due_date,
                invoices.paid_at, invoices.created_at, invoices.updated_at,
                customers.name AS customer_name
            FROM invoices
            JOIN customers ON customers.id = invoices.customer_id
            WHERE invoices.business_id = ?
            ORDER BY invoices.id DESC
            LIMIT ? OFFSET ?
            """,
            (business_id, limit, offset),
        ).fetchall()
    return [_row_to_invoice(row) for row in rows]


def get_invoice(invoice_id: int, business_id: int | None = None) -> dict | None:
    with get_db() as conn:
        if business_id is None:
            row = conn.execute(
                """
                SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email, customers.phone AS customer_phone
                FROM invoices
                JOIN customers ON customers.id = invoices.customer_id
                WHERE invoices.id = ?
                """,
                (invoice_id,),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email, customers.phone AS customer_phone
                FROM invoices
                JOIN customers ON customers.id = invoices.customer_id
                WHERE invoices.id = ? AND invoices.business_id = ?
                """,
                (invoice_id, business_id),
            ).fetchone()
    return _row_to_invoice(row) if row else None


def get_invoice_by_number(invoice_number: str, business_id: int | None = None) -> dict | None:
    with get_db() as conn:
        if business_id is None:
            row = conn.execute(
                """
                SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email, customers.phone AS customer_phone
                FROM invoices
                JOIN customers ON customers.id = invoices.customer_id
                WHERE invoices.invoice_number = ?
                """,
                (invoice_number,),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email, customers.phone AS customer_phone
                FROM invoices
                JOIN customers ON customers.id = invoices.customer_id
                WHERE invoices.invoice_number = ? AND invoices.business_id = ?
                """,
                (invoice_number, business_id),
            ).fetchone()
    return _row_to_invoice(row) if row else None


def find_latest_open_invoice_for_phone(business_id: int, phone: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email, customers.phone AS customer_phone
            FROM invoices
            JOIN customers ON customers.id = invoices.customer_id
            WHERE invoices.business_id = ?
              AND customers.phone = ?
              AND invoices.payment_status IN ('pending', 'partial')
            ORDER BY invoices.id DESC
            LIMIT 1
            """,
            (business_id, phone),
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


def update_invoice(invoice_id: int, payload: dict, business_id: int | None = None) -> dict | None:
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
        return get_invoice(invoice_id, business_id)

    if "customer_id" in updates and not get_customer(int(updates["customer_id"]), business_id):
        raise ValueError("Customer not found")

    set_clause = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values())
    values.append(utc_now())

    with get_db() as conn:
        if business_id is None:
            values.append(invoice_id)
            conn.execute(
                f"""
                UPDATE invoices
                SET {set_clause},
                    updated_at = ?
                WHERE id = ?
                """,
                values,
            )
        else:
            values.extend([invoice_id, business_id])
            conn.execute(
                f"""
                UPDATE invoices
                SET {set_clause},
                    updated_at = ?
                WHERE id = ? AND business_id = ?
                """,
                values,
            )
        row = conn.execute(
            """
            SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email, customers.phone AS customer_phone
            FROM invoices
            JOIN customers ON customers.id = invoices.customer_id
            WHERE invoices.id = ?
            """,
            (invoice_id,),
        ).fetchone()
        if row and business_id is not None and int(row["business_id"]) != business_id:
            return None
    return _row_to_invoice(row) if row else None


def record_invoice_payment(invoice_id: int, payload: dict, business_id: int | None = None) -> dict | None:
    invoice = get_invoice(invoice_id, business_id)
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
                    SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email, customers.phone AS customer_phone
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
            SELECT invoices.*, customers.name AS customer_name, customers.email AS customer_email, customers.phone AS customer_phone
            FROM invoices
            JOIN customers ON customers.id = invoices.customer_id
            WHERE invoices.id = ?
            """,
            (invoice_id,),
        ).fetchone()
    return _row_to_invoice(row)


def delete_invoice(invoice_id: int, business_id: int) -> bool:
    with get_db() as conn:
        dependent = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM payments WHERE invoice_id = ?) AS payment_count,
                (SELECT COUNT(*) FROM payment_proofs WHERE invoice_id = ?) AS proof_count,
                (SELECT COUNT(*) FROM reminders WHERE invoice_id = ?) AS reminder_count,
                (SELECT COUNT(*) FROM receipts WHERE invoice_id = ?) AS receipt_count
            """,
            (invoice_id, invoice_id, invoice_id, invoice_id),
        ).fetchone()
        if dependent and any(int(dependent[key]) > 0 for key in dependent.keys()):
            raise ValueError("Invoice has payment or proof history and cannot be removed")
        result = conn.execute(
            "DELETE FROM invoices WHERE id = ? AND business_id = ?",
            (invoice_id, business_id),
        )
    return result.rowcount > 0


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
