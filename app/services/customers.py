from app.db.store import get_db, utc_now


def create_customer(payload: dict) -> dict:
    if payload.get("business_id") is None:
        raise ValueError("business_id is required")
    business_id = int(payload["business_id"])
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO customers (business_id, name, phone, email, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                business_id,
                payload["name"],
                payload.get("phone"),
                payload.get("email"),
                utc_now(),
            ),
        )
        customer_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
    return dict(row)


def list_customers(business_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM customers WHERE business_id = ? ORDER BY id DESC",
            (business_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_customer(customer_id: int, business_id: int | None = None) -> dict | None:
    with get_db() as conn:
        if business_id is None:
            row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM customers WHERE id = ? AND business_id = ?",
                (customer_id, business_id),
            ).fetchone()
    return dict(row) if row else None


def get_customer_by_phone(business_id: int, phone: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE business_id = ? AND phone = ?",
            (business_id, phone),
        ).fetchone()
    return dict(row) if row else None


def get_customer_by_name(business_id: int, name: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE business_id = ? AND lower(name) = lower(?)",
            (business_id, name),
        ).fetchone()
    return dict(row) if row else None


def update_customer(customer_id: int, payload: dict, business_id: int) -> dict | None:
    allowed = {
        "name": payload.get("name"),
        "phone": payload.get("phone"),
        "email": payload.get("email"),
    }
    updates = {key: value for key, value in allowed.items() if value is not None}
    if not updates:
        return get_customer(customer_id, business_id)

    set_clause = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values())
    values.extend([customer_id, business_id])

    with get_db() as conn:
        conn.execute(
            f"""
            UPDATE customers
            SET {set_clause}
            WHERE id = ? AND business_id = ?
            """,
            values,
        )
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ? AND business_id = ?",
            (customer_id, business_id),
        ).fetchone()
    return dict(row) if row else None


def delete_customer(customer_id: int, business_id: int) -> bool:
    with get_db() as conn:
        invoice_row = conn.execute(
            """
            SELECT id
            FROM invoices
            WHERE customer_id = ? AND business_id = ?
            LIMIT 1
            """,
            (customer_id, business_id),
        ).fetchone()
        if invoice_row:
            raise ValueError("Customer has invoices and cannot be removed")
        result = conn.execute(
            "DELETE FROM customers WHERE id = ? AND business_id = ?",
            (customer_id, business_id),
        )
    return result.rowcount > 0
