from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

from app.services.customers import create_customer, get_customer_by_name, get_customer_by_phone
from app.services.invoices import create_invoice, find_latest_open_invoice_for_phone, get_invoice_by_number
from app.services.parser import AMOUNT_PATTERN, QUANTITY_TOKEN_PATTERN, parse_order
from app.services.payment_proofs import create_text_payment_proof, get_payment_proof_by_hash
from app.services.whatsapp import detect_payment


ORDER_KEYWORD_PATTERN = re.compile(
    r"\b(want|wants|nak|beli|buy|please send|brownie|cake|cakes|nasi|mee|roti|teh|kopi)\b",
    re.IGNORECASE,
)
INVOICE_REFERENCE_PATTERN = re.compile(r"INV-[A-Z0-9-]+", re.IGNORECASE)
SUPPORTED_MEDIA_TYPES = {
    "text",
    "voice_note",
    "receipt_image",
    "invoice_image",
    "document",
    "unknown",
}


def ingest_whatsapp_evidence(
    *,
    business_id: int,
    from_phone: str,
    message: str | None,
    transcript: str | None,
    media_type: str,
    media_metadata: dict | None = None,
    source_channel: str = "whatsapp",
) -> dict:
    normalized_media_type = (media_type or "text").strip().lower()
    if normalized_media_type not in SUPPORTED_MEDIA_TYPES:
        normalized_media_type = "unknown"

    normalized_text = _normalize_text(transcript or message)
    metadata = {**(media_metadata or {}), "from_phone": from_phone}
    if not normalized_text and not metadata:
        raise ValueError("message, transcript, or media_metadata is required")

    if _should_create_payment_proof(normalized_text, normalized_media_type):
        invoice_num = _extract_invoice_number(normalized_text)
        invoice = get_invoice_by_number(invoice_num, business_id) if invoice_num else find_latest_open_invoice_for_phone(business_id, from_phone)
        payment_info = detect_payment(normalized_text)
        auto_approve = bool(payment_info.amount and invoice and normalized_media_type == "receipt_image")

        proof = _create_whatsapp_proof(
            business_id=business_id,
            text=normalized_text or _serialize_metadata(metadata, normalized_media_type),
            media_type=normalized_media_type,
            media_metadata=metadata,
            invoice_number=invoice_num,
            source_channel=source_channel,
            decision_reason="needs_manual_review",
            auto_approve=auto_approve,
        )
        return {
            "business_id": business_id,
            "intent": "payment_proof",
            "from_phone": from_phone,
            "media_type": normalized_media_type,
            "normalized_text": normalized_text or None,
            "payment_proof": proof,
            "invoice": None,
            "parsed": _build_payment_parsed(normalized_text, proof),
            "message": "Payment proof received for review. Invoice status will update after approval.",
        }

    parsed_order = parse_order(normalized_text, business_id) if normalized_text else None
    if normalized_text and parsed_order and _looks_like_order(normalized_text, parsed_order):
        parsed = parsed_order
        customer = _resolve_customer(business_id, from_phone, parsed.get("customer_name"))
        invoice_number = _generate_invoice_number(business_id)
        invoice = create_invoice(
            {
                "business_id": business_id,
                "customer_id": customer["id"],
                "invoice_number": invoice_number,
                "items": parsed["items"],
                "subtotal": parsed["total"],
                "tax": 0.0,
                "total": parsed["total"],
                "payment_method": parsed["payment_method"],
                "payment_status": "pending",
            }
        )
        return {
            "business_id": business_id,
            "intent": "invoice_created",
            "from_phone": from_phone,
            "media_type": normalized_media_type,
            "normalized_text": normalized_text,
            "payment_proof": None,
            "invoice": invoice,
            "parsed": parsed,
            "message": f"Order captured. Invoice {invoice['invoice_number']} is pending seller confirmation.",
        }

    proof = _create_whatsapp_proof(
        business_id=business_id,
        text=normalized_text or _serialize_metadata(metadata, normalized_media_type),
        media_type=normalized_media_type,
        media_metadata=metadata,
        invoice_number=_extract_invoice_number(normalized_text),
        source_channel=source_channel,
        decision_reason="needs_manual_review",
    )
    return {
        "business_id": business_id,
        "intent": "needs_review",
        "from_phone": from_phone,
        "media_type": normalized_media_type,
        "normalized_text": normalized_text or None,
        "payment_proof": proof,
        "invoice": None,
        "parsed": {
            "classification": "unknown",
            "invoice_number": _extract_invoice_number(normalized_text),
        },
        "message": "Evidence received for review. Seller approval is required before anything updates.",
    }


def _resolve_customer(business_id: int, phone: str, customer_name: str | None) -> dict:
    customer = get_customer_by_phone(business_id, phone)
    if not customer and customer_name:
        customer = get_customer_by_name(business_id, customer_name)
    if customer:
        return customer
    return create_customer(
        {
            "business_id": business_id,
            "name": customer_name or phone,
            "phone": phone,
        }
    )


def _should_create_payment_proof(text: str, media_type: str) -> bool:
    if media_type == "receipt_image":
        return True
    if not text:
        return media_type in {"invoice_image", "document", "unknown"}
    if detect_payment(text).detected:
        return True
    return bool(re.search(r"\b(dah bayar|dh bayar|dh byr|bayar dah|paid|payment done|done pay|transfer dah)\b", text, re.IGNORECASE))


def _looks_like_order(text: str, parsed: dict | None = None) -> bool:
    if detect_payment(text).detected:
        return False
    if parsed and parsed.get("total", 0) and any(float(item.get("unit_price") or 0.0) > 0 for item in parsed.get("items") or []):
        return True
    if QUANTITY_TOKEN_PATTERN.search(text):
        return True
    if ORDER_KEYWORD_PATTERN.search(text) and AMOUNT_PATTERN.search(text):
        return True
    if AMOUNT_PATTERN.search(text) and any(token in text for token in ["+", ",", " x", "x", "total"]):
        return True
    return False


def _create_whatsapp_proof(
    *,
    business_id: int,
    text: str,
    media_type: str,
    media_metadata: dict,
    invoice_number: str | None,
    source_channel: str,
    decision_reason: str | None = None,
    auto_approve: bool = False,
) -> dict:
    payment_info = detect_payment(text)
    invoice = get_invoice_by_number(invoice_number, business_id) if invoice_number else None
    if invoice is None and media_type == "text" and detect_payment(text).detected:
        invoice = find_latest_open_invoice_for_phone(business_id, str((media_metadata or {}).get("from_phone") or ""))
    dedupe_key = _resolve_whatsapp_dedupe_key(text, media_type, media_metadata)
    text_bytes = (dedupe_key or text.strip()).encode("utf-8")
    file_hash = hashlib.sha256(text_bytes).hexdigest()
    existing = get_payment_proof_by_hash(business_id, file_hash)
    if existing:
        return existing
    
    # Auto-approve if receipt image with valid amount + matching invoice
    extracted_amount = payment_info.amount if payment_info.amount is not None else (float(invoice["total"]) if invoice else None)
    extracted_reference = invoice_number or (invoice.get("invoice_number") if invoice else None)

    if auto_approve and extracted_amount is not None and invoice:
        proof = create_text_payment_proof(
            business_id=business_id,
            uploaded_by_user_id=None,
            text=text,
            source_channel=source_channel,
            dedupe_key=dedupe_key,
            invoice_id=invoice["id"],
            extracted_amount=extracted_amount,
            extracted_reference=extracted_reference,
            extracted_method=payment_info.method,
            extra_payload={
                "media_type": media_type,
                "media_metadata": media_metadata,
            },
            decision_reason="auto_approved_receipt",
            auto_approve=True,
        )
        return proof

    return create_text_payment_proof(
        business_id=business_id,
        uploaded_by_user_id=None,
        text=text,
        source_channel=source_channel,
        dedupe_key=dedupe_key,
        invoice_id=invoice["id"] if invoice else None,
        extracted_amount=extracted_amount,
        extracted_reference=extracted_reference,
        extracted_method=payment_info.method,
        extra_payload={
            "media_type": media_type,
            "media_metadata": media_metadata,
        },
        decision_reason=decision_reason,
        auto_approve=False,
    )


def _build_payment_parsed(text: str, proof: dict) -> dict:
    payment_info = detect_payment(text) if text else None
    return {
        "classification": "payment",
        "detected_amount": payment_info.amount if payment_info else proof.get("extracted_amount"),
        "invoice_number": payment_info.invoice_number if payment_info else proof.get("extracted_reference"),
        "method": payment_info.method if payment_info else None,
    }


def _extract_invoice_number(text: str) -> str | None:
    if not text:
        return None
    match = INVOICE_REFERENCE_PATTERN.search(text)
    return match.group(0).upper() if match else None


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().split())


def _serialize_metadata(media_metadata: dict, media_type: str) -> str:
    payload = {"media_type": media_type, "media_metadata": media_metadata}
    return json.dumps(payload, sort_keys=True)


def _resolve_whatsapp_dedupe_key(text: str, media_type: str, media_metadata: dict) -> str | None:
    if media_type in {"document", "receipt_image", "invoice_image", "voice_note", "unknown"}:
        event_id = str(media_metadata.get("event_id") or "").strip()
        message_id = str(media_metadata.get("message_id") or "").strip()
        if event_id or message_id:
            return "|".join(part for part in [event_id, message_id] if part)
        # Demo-safe fallback: if WAHA does not expose stable ids for forwarded media,
        # force a fresh proof instead of collapsing distinct receipts into one row.
        return f"media-{uuid.uuid4()}"
    normalized = text.strip()
    return normalized or None


def _generate_invoice_number(business_id: int) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"INV-{business_id}-{timestamp}"
