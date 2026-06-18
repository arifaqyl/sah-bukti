import re

from app.db.store import get_db, utc_now


AMOUNT_PATTERN = re.compile(r"(?:rm|RM)\s*([0-9]+(?:\.[0-9]{1,2})?)")
DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _extract_name(text: str) -> str | None:
    for line in text.splitlines():
        lower = line.lower().strip()
        if lower.startswith("name:"):
            return line.split(":", 1)[1].strip() or None
        if lower.startswith("customer:"):
            return line.split(":", 1)[1].strip() or None
    return None


def _extract_item(text: str) -> str | None:
    for line in text.splitlines():
        lower = line.lower().strip()
        if lower.startswith("item:"):
            return line.split(":", 1)[1].strip() or None
        if lower.startswith("service:"):
            return line.split(":", 1)[1].strip() or None
    return None


def ingest_whatsapp(raw_text: str) -> dict:
    amount_match = AMOUNT_PATTERN.search(raw_text)
    date_match = DATE_PATTERN.search(raw_text)
    extracted = {
        "extracted_name": _extract_name(raw_text),
        "extracted_amount": float(amount_match.group(1)) if amount_match else None,
        "extracted_due_date": date_match.group(1) if date_match else None,
        "extracted_item": _extract_item(raw_text),
    }

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO message_ingests (
                source,
                raw_text,
                extracted_name,
                extracted_amount,
                extracted_due_date,
                extracted_item,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "whatsapp",
                raw_text,
                extracted["extracted_name"],
                extracted["extracted_amount"],
                extracted["extracted_due_date"],
                extracted["extracted_item"],
                utc_now(),
            ),
        )

    parts = []
    if extracted["extracted_name"]:
        parts.append(f"name={extracted['extracted_name']}")
    if extracted["extracted_amount"] is not None:
        parts.append(f"amount=RM{extracted['extracted_amount']:.2f}")
    if extracted["extracted_due_date"]:
        parts.append(f"due={extracted['extracted_due_date']}")
    if extracted["extracted_item"]:
        parts.append(f"item={extracted['extracted_item']}")

    extracted["summary"] = ", ".join(parts) if parts else "No structured fields extracted yet."
    return extracted
