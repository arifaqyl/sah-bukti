from app.db.store import get_db, get_default_business_id, utc_now


def create_daily_close(payload: dict) -> dict:
    business_id = int(payload.get("business_id") or get_default_business_id())
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


def list_daily_close() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM daily_ops
            ORDER BY date DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_daily_close(date: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM daily_ops
            WHERE date = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (date,),
        ).fetchone()
    return dict(row) if row else None
