from app.db.store import get_db, utc_now


def create_daily_close(payload: dict) -> dict:
    if payload.get("business_id") is None:
        raise ValueError("business_id is required")
    business_id = int(payload["business_id"])
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO daily_ops (
                business_id,
                date,
                total_cash,
                total_qr,
                total_transfer,
                total_orders,
                total_revenue,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                business_id,
                payload["date"],
                payload.get("total_cash", 0),
                payload.get("total_qr", 0),
                payload.get("total_transfer", 0),
                payload.get("total_orders", 0),
                payload.get("total_revenue", 0),
                utc_now(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM daily_ops WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)


def list_daily_close(business_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM daily_ops
            WHERE business_id = ?
            ORDER BY date DESC, id DESC
            """,
            (business_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_daily_close(date: str, business_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM daily_ops
            WHERE date = ? AND business_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (date, business_id),
        ).fetchone()
    return dict(row) if row else None
