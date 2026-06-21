from app.db.store import get_db, utc_now


def get_business_profile(business_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT
                id AS business_id,
                name,
                owner_whatsapp,
                whatsapp_group_chat_id,
                whatsapp_group_name,
                industry,
                tagline,
                theme_color
            FROM businesses
            WHERE id = ?
            """,
            (business_id,),
        ).fetchone()
    return dict(row) if row else None


def update_business_profile(business_id: int, payload: dict) -> dict | None:
    allowed = {
        "name": payload.get("name"),
        "owner_whatsapp": payload.get("owner_whatsapp"),
        "whatsapp_group_chat_id": payload.get("whatsapp_group_chat_id"),
        "whatsapp_group_name": payload.get("whatsapp_group_name"),
        "industry": payload.get("industry"),
        "tagline": payload.get("tagline"),
        "theme_color": payload.get("theme_color"),
    }
    updates = {key: value for key, value in allowed.items() if value is not None}
    if not updates:
        return get_business_profile(business_id)

    set_clause = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [utc_now(), business_id]
    with get_db() as conn:
        conn.execute(
            f"""
            UPDATE businesses
            SET {set_clause},
                updated_at = ?
            WHERE id = ?
            """,
            values,
        )
    return get_business_profile(business_id)


def bind_whatsapp_group(business_id: int, chat_id: str, group_name: str | None = None) -> dict | None:
    with get_db() as conn:
        conn.execute(
            """
            UPDATE businesses
            SET whatsapp_group_chat_id = ?,
                whatsapp_group_name = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (chat_id, group_name, utc_now(), business_id),
        )
    return get_business_profile(business_id)
