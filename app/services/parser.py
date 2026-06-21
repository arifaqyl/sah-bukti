import json
import re
from typing import Any

import httpx

from app.config import GEMINI_API_KEY, GEMINI_FLASH_MODEL, GEMINI_TIMEOUT_SECONDS
from app.db.store import get_db


AMOUNT_PATTERN = re.compile(r"(?:rm)\s*([0-9]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)
QUANTITY_TOKEN_PATTERN = re.compile(r"(?:x\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:pcs?|pack|unit|units?))", re.IGNORECASE)
PAYMENT_METHOD_PATTERNS = {
    "cash": re.compile(r"\bcash\b", re.IGNORECASE),
    "qr": re.compile(r"\bqr\b|\bduitnow\b", re.IGNORECASE),
    "transfer": re.compile(r"\btransfer\b|\bbank\b", re.IGNORECASE),
}
DEMO_MENU = {
    "nasi lemak": 5.00,
    "nasi goreng": 7.00,
    "roti canai": 3.50,
    "teh tarik": 2.00,
    "mee rebus": 6.00,
}
NUMBER_WORDS = {
    "satu": 1.0,
    "dua": 2.0,
    "tiga": 3.0,
    "empat": 4.0,
    "lima": 5.0,
    "enam": 6.0,
    "tujuh": 7.0,
    "lapan": 8.0,
    "sembilan": 9.0,
    "sepuluh": 10.0,
}


def parse_order(text: str, business_id: int) -> dict:
    regex_first = _parse_with_regex(text, business_id)
    if regex_first["total"] > 0 and regex_first.get("menu_matched"):
        return regex_first

    ai_error: Exception | None = None
    if GEMINI_API_KEY:
        try:
            return _parse_with_gemini(text)
        except Exception as exc:
            ai_error = exc

    parsed = regex_first
    if ai_error is not None:
        parsed["source"] = "regex_fallback"
    return parsed


def _parse_with_gemini(text: str) -> dict:
    prompt = (
        "Extract a WhatsApp order into strict JSON with keys: "
        "customer_name (string or null), items (array of objects with name, quantity, unit_price), "
        "total (number), payment_method (cash|qr|transfer). "
        "If data is missing, infer conservatively. Return JSON only."
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"text": text},
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
        },
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_FLASH_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    with httpx.Client(timeout=GEMINI_TIMEOUT_SECONDS) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(raw_text)
    return _normalize_parsed_order(parsed, source="gemini")


def _parse_with_regex(text: str, business_id: int) -> dict:
    amount_match = AMOUNT_PATTERN.search(text)
    items = _extract_items(text, float(amount_match.group(1)) if amount_match else 0.0)
    inferred_total = round(sum(float(item["quantity"]) * float(item["unit_price"]) for item in items), 2)
    total = float(amount_match.group(1)) if amount_match else inferred_total
    payment_method = _infer_payment_method(text)
    customer_name = _match_customer_name(text, business_id)
    return {
        "customer_name": customer_name,
        "items": items,
        "total": total,
        "payment_method": payment_method,
        "source": "regex",
        "menu_matched": any(float(item.get("unit_price") or 0.0) > 0 for item in items),
    }


def _normalize_parsed_order(parsed: dict[str, Any], source: str) -> dict:
    items = []
    raw_items = parsed.get("items") or []
    for item in raw_items:
        name = str(item.get("name") or "Item").strip()
        quantity = float(item.get("quantity") or 1)
        unit_price = float(item.get("unit_price") or 0)
        items.append({"name": name, "quantity": quantity, "unit_price": unit_price})

    total = float(parsed.get("total") or 0)
    payment_method = str(parsed.get("payment_method") or "cash").lower()
    if payment_method not in {"cash", "qr", "transfer"}:
        payment_method = "cash"

    return {
        "customer_name": parsed.get("customer_name"),
        "items": items or _extract_items("", total),
        "total": total,
        "payment_method": payment_method,
        "source": source,
    }


def _infer_payment_method(text: str) -> str:
    for method, pattern in PAYMENT_METHOD_PATTERNS.items():
        if pattern.search(text):
            return method
    return "cash"


def _match_customer_name(text: str, business_id: int) -> str | None:
    lowered = text.lower()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT name FROM customers WHERE business_id = ?",
            (business_id,),
        ).fetchall()
    for row in rows:
        name = row["name"]
        if name and name.lower() in lowered:
            return name
    return None


def _extract_items(text: str, total: float) -> list[dict]:
    normalized = " ".join(text.strip().split())
    menu_match = _extract_menu_item(normalized)
    if menu_match is not None:
        item_name, quantity, unit_price = menu_match
        if total > 0 and quantity > 0:
            unit_price = round(total / quantity, 2)
        return [{"name": item_name, "quantity": quantity, "unit_price": unit_price}]

    qty_match = QUANTITY_TOKEN_PATTERN.search(normalized)
    quantity = 1.0
    if qty_match:
        quantity = float(qty_match.group(1) or qty_match.group(2))
    else:
        quantity = _extract_word_quantity(normalized)

    item_name = "Item"
    if normalized:
        item_name = _derive_item_name(normalized)
    unit_price = round(total / quantity, 2) if total > 0 and quantity > 0 else 0.0
    return [{"name": item_name, "quantity": quantity, "unit_price": unit_price}]


def _derive_item_name(text: str) -> str:
    trimmed = AMOUNT_PATTERN.sub("", text)
    trimmed = QUANTITY_TOKEN_PATTERN.sub("", trimmed)
    trimmed = re.sub(r"\b(cash|qr|duitnow|transfer|bank)\b", "", trimmed, flags=re.IGNORECASE)
    trimmed = re.sub(r"[^a-zA-Z0-9\s\-]", " ", trimmed)
    trimmed = " ".join(trimmed.split()).strip()
    return trimmed or "Item"


def _extract_menu_item(text: str) -> tuple[str, float, float] | None:
    lowered = text.lower()
    for menu_name, unit_price in DEMO_MENU.items():
        if menu_name in lowered:
            quantity = _extract_quantity_near_phrase(lowered, menu_name)
            return menu_name.title(), quantity, unit_price
    return None


def _extract_quantity_near_phrase(text: str, phrase: str) -> float:
    pattern_x_before = re.search(rf"x\s*(\d+(?:\.\d+)?)\s+{re.escape(phrase)}", text, re.IGNORECASE)
    if pattern_x_before:
        return float(pattern_x_before.group(1))
    pattern_before = re.search(rf"(\d+(?:\.\d+)?)\s+{re.escape(phrase)}", text, re.IGNORECASE)
    if pattern_before:
        return float(pattern_before.group(1))
    pattern_x_after = re.search(rf"{re.escape(phrase)}\s+x\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if pattern_x_after:
        return float(pattern_x_after.group(1))
    pattern_after = re.search(rf"{re.escape(phrase)}\s+(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if pattern_after:
        return float(pattern_after.group(1))
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b\s+{re.escape(phrase)}", text, re.IGNORECASE):
            return value
        if re.search(rf"{re.escape(phrase)}\s+\b{re.escape(word)}\b", text, re.IGNORECASE):
            return value
    return _extract_word_quantity(text)


def _extract_word_quantity(text: str) -> float:
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
            return value
    trailing_number = re.search(r"(\d+(?:\.\d+)?)\s*$", text)
    if trailing_number:
        return float(trailing_number.group(1))
    return 1.0
