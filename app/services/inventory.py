from app.db.store import get_db, utc_now


def create_ingredient(payload: dict) -> dict:
    if payload.get("business_id") is None:
        raise ValueError("business_id is required")
    business_id = int(payload["business_id"])
    now = utc_now()
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO ingredients (business_id, name, unit, current_stock, reorder_point, supplier, notes, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                business_id,
                payload["name"],
                payload.get("unit", "pcs"),
                payload.get("current_stock", 0),
                payload.get("reorder_point", 0),
                payload.get("supplier"),
                payload.get("notes"),
                now,
            ),
        )
        row = conn.execute("SELECT * FROM ingredients WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def list_ingredients(business_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM ingredients WHERE business_id = ? ORDER BY id DESC",
            (business_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_ingredient(ingredient_id: int, payload: dict, business_id: int | None = None) -> dict | None:
    allowed = {
        "name": payload.get("name"),
        "unit": payload.get("unit"),
        "current_stock": payload.get("current_stock"),
        "reorder_point": payload.get("reorder_point"),
        "supplier": payload.get("supplier"),
        "notes": payload.get("notes"),
    }
    updates = {key: value for key, value in allowed.items() if value is not None}
    if not updates:
        return get_ingredient(ingredient_id, business_id)

    set_clause = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values())
    values.append(utc_now())

    with get_db() as conn:
        if business_id is None:
            values.append(ingredient_id)
            conn.execute(
                f"""
                UPDATE ingredients
                SET {set_clause},
                    last_updated = ?
                WHERE id = ?
                """,
                values,
            )
            row = conn.execute("SELECT * FROM ingredients WHERE id = ?", (ingredient_id,)).fetchone()
        else:
            values.extend([ingredient_id, business_id])
            conn.execute(
                f"""
                UPDATE ingredients
                SET {set_clause},
                    last_updated = ?
                WHERE id = ? AND business_id = ?
                """,
                values,
            )
            row = conn.execute(
                "SELECT * FROM ingredients WHERE id = ? AND business_id = ?",
                (ingredient_id, business_id),
            ).fetchone()
    return dict(row) if row else None


def get_ingredient(ingredient_id: int, business_id: int | None = None) -> dict | None:
    with get_db() as conn:
        if business_id is None:
            row = conn.execute("SELECT * FROM ingredients WHERE id = ?", (ingredient_id,)).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM ingredients WHERE id = ? AND business_id = ?",
                (ingredient_id, business_id),
            ).fetchone()
    return dict(row) if row else None


def check_stock(business_id: int, ingredient_id: int) -> float:
    with get_db() as conn:
        row = conn.execute(
            "SELECT current_stock FROM ingredients WHERE business_id = ? AND id = ?",
            (business_id, ingredient_id),
        ).fetchone()
    return float(row["current_stock"]) if row else 0.0


def get_reorder_alerts(business_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM ingredients
            WHERE business_id = ?
              AND current_stock <= reorder_point
            ORDER BY current_stock ASC, id DESC
            """,
            (business_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_suppliers(business_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                name,
                unit,
                current_stock,
                reorder_point,
                supplier,
                notes
            FROM ingredients
            WHERE business_id = ?
            ORDER BY COALESCE(supplier, ''), name ASC, id DESC
            """,
            (business_id,),
        ).fetchall()

    grouped: dict[str, dict] = {}
    for row in rows:
        item = dict(row)
        supplier_name = (item.get("supplier") or "").strip() or "Unassigned supplier"
        if supplier_name not in grouped:
            grouped[supplier_name] = {
                "supplier": supplier_name,
                "ingredient_count": 0,
                "low_stock_count": 0,
                "ingredients": [],
            }
        grouped[supplier_name]["ingredient_count"] += 1
        if float(item["current_stock"]) <= float(item["reorder_point"]):
            grouped[supplier_name]["low_stock_count"] += 1
        grouped[supplier_name]["ingredients"].append(item)
    return list(grouped.values())


def update_stock(ingredient_id: int, quantity: float) -> bool:
    with get_db() as conn:
        result = conn.execute(
            """
            UPDATE ingredients
            SET current_stock = ?, last_updated = ?
            WHERE id = ?
            """,
            (quantity, utc_now(), ingredient_id),
        )
    return result.rowcount > 0


def delete_ingredient(ingredient_id: int, business_id: int) -> bool:
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM ingredients WHERE id = ? AND business_id = ?",
            (ingredient_id, business_id),
        )
    return result.rowcount > 0


def deduct_ingredients(business_id: int, items: list[dict]) -> bool:
    normalized_names = [str(item.get("name", "")).strip().lower() for item in items if item.get("name")]
    if not normalized_names:
        return True

    with get_db() as conn:
        for item in items:
            name = str(item.get("name", "")).strip().lower()
            quantity = float(item.get("quantity") or 0)
            if not name or quantity <= 0:
                continue
            row = conn.execute(
                """
                SELECT id, current_stock
                FROM ingredients
                WHERE business_id = ? AND lower(name) = ?
                LIMIT 1
                """,
                (business_id, name),
            ).fetchone()
            if not row:
                continue
            new_stock = max(0.0, float(row["current_stock"]) - quantity)
            conn.execute(
                """
                UPDATE ingredients
                SET current_stock = ?, last_updated = ?
                WHERE id = ?
                """,
                (new_stock, utc_now(), row["id"]),
            )
    return True
