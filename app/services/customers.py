from app.db.store import get_db, get_default_business_id, utc_now


def create_customer(payload: dict) -> dict:
    business_id = int(payload.get("business_id") or get_default_business_id())
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


def list_customers() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


def get_customer(customer_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
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
