from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone

from app.services.customers import create_customer, get_customer_by_name, get_customer_by_phone
from app.services.evidence import ingest_whatsapp_evidence
from app.services.invoices import create_invoice, get_invoice_by_number
from app.services.parser import AMOUNT_PATTERN, parse_order
from app.services.payment_proofs import PaymentProofConflictError, create_text_payment_proof
from app.services.whatsapp import detect_payment


WHATSAPP_EXPORT_LINE_PATTERN = re.compile(r"^\[(?P<timestamp>[^\]]+)\]\s+(?P<sender>[^:]+):\s*(?P<message>.+)$")
PAYMENT_COLUMNS = {"invoice_number", "reference", "amount", "paid_amount", "payment_method", "paid_at"}
ORDER_COLUMNS = {"item", "qty", "quantity", "total", "customer", "phone", "message", "notes"}
SUPPORTED_SOURCE_TYPES = {
    "whatsapp_export",
    "csv_export",
    "google_drive_file",
    "local_file",
    "unknown",
}


def ingest_evidence_import(
    *,
    business_id: int,
    source_type: str,
    raw_text: str | None = None,
    file_content: bytes | None = None,
    filename: str | None = None,
    mime_type: str | None = None,
    drive_url: str | None = None,
    media_metadata: dict | None = None,
) -> dict:
    normalized_source_type = _normalize_source_type(source_type)
    metadata = dict(media_metadata or {})
    if drive_url:
        metadata["drive_url"] = drive_url
    if filename:
        metadata["filename"] = filename
    if mime_type:
        metadata["mime_type"] = mime_type

    result = {
        "business_id": business_id,
        "source_type": normalized_source_type,
        "imported_count": 0,
        "payment_proofs_created": 0,
        "invoices_created": 0,
        "needs_review_count": 0,
        "failed_count": 0,
        "failures": [],
    }

    if normalized_source_type == "whatsapp_export":
        if not raw_text:
            raise ValueError("raw_text is required for whatsapp_export")
        for row_number, entry in enumerate(_parse_whatsapp_export(raw_text), start=1):
            _handle_import_action(
                result,
                row_number=row_number,
                action=lambda: ingest_whatsapp_evidence(
                    business_id=business_id,
                    from_phone=entry["from_phone"],
                    message=entry["message"],
                    transcript=None,
                    media_type="text",
                    media_metadata={
                        **metadata,
                        "source_type": normalized_source_type,
                        "sender": entry["sender"],
                        "timestamp": entry["timestamp"],
                    },
                    source_channel="import",
                ),
            )
        return result

    if _is_csv_source(normalized_source_type, filename, mime_type, raw_text, file_content):
        rows = _parse_csv_content(raw_text=raw_text, file_content=file_content)
        for row_number, row in enumerate(rows, start=1):
            classification = _classify_import_row(row)
            _handle_import_action(
                result,
                row_number=row_number,
                action=lambda row=row, classification=classification: _ingest_csv_row(
                    business_id=business_id,
                    row=row,
                    classification=classification,
                    source_type=normalized_source_type,
                    base_metadata=metadata,
                ),
            )
        return result

    if normalized_source_type in {"google_drive_file", "local_file", "unknown"}:
        proof = _create_import_review_payload(
            business_id=business_id,
            text=raw_text or json.dumps({"source_type": normalized_source_type, **metadata}, sort_keys=True),
            metadata={**metadata, "source_type": normalized_source_type},
            invoice_number=_extract_reference_from_metadata(metadata),
            amount=None,
            method=None,
        )
        result["imported_count"] = 1
        result["payment_proofs_created"] = 1
        result["needs_review_count"] = 1
        return result

    raise ValueError("Unsupported source_type")


def _parse_whatsapp_export(raw_text: str) -> list[dict]:
    entries: list[dict] = []
    for line in raw_text.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        match = WHATSAPP_EXPORT_LINE_PATTERN.match(normalized)
        if not match:
            entries.append(
                {
                    "timestamp": None,
                    "sender": "unknown",
                    "from_phone": "imported-whatsapp",
                    "message": normalized,
                }
            )
            continue
        sender = match.group("sender").strip()
        entries.append(
            {
                "timestamp": match.group("timestamp").strip(),
                "sender": sender,
                "from_phone": _sender_to_phone(sender),
                "message": match.group("message").strip(),
            }
        )
    return entries


def _parse_csv_content(*, raw_text: str | None, file_content: bytes | None) -> list[dict]:
    if file_content is not None:
        text = file_content.decode("utf-8-sig")
    elif raw_text is not None:
        text = raw_text
    else:
        raise ValueError("CSV import requires raw_text or file_content")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    for row in reader:
        rows.append({str(key or "").strip().lower(): (value or "").strip() for key, value in row.items()})
    return rows


def _classify_import_row(row: dict) -> str:
    if _extract_reference(row) and _extract_amount(row) is not None:
        return "payment"
    if any(row.get(column) for column in ORDER_COLUMNS):
        text = _row_to_order_text(row)
        if text and _looks_like_import_order(text):
            return "order"
    return "unknown"


def _ingest_csv_row(
    *,
    business_id: int,
    row: dict,
    classification: str,
    source_type: str,
    base_metadata: dict,
) -> dict:
    if classification == "payment":
        reference = _extract_reference(row)
        amount = _extract_amount(row)
        invoice = get_invoice_by_number(reference, business_id) if reference else None
        method = row.get("payment_method") or detect_payment(_row_to_payment_text(row)).method or "transfer"
        return _create_import_review_payload(
            business_id=business_id,
            text=_row_to_payment_text(row),
            metadata={**base_metadata, "source_type": source_type, "row": row},
            invoice_number=reference,
            amount=amount,
            method=method,
            invoice_id=invoice["id"] if invoice else None,
            extracted_paid_at=row.get("paid_at") or None,
        )

    if classification == "order":
        text = _row_to_order_text(row)
        parsed = parse_order(text, business_id)
        customer = _resolve_customer_for_import(
            business_id=business_id,
            phone=row.get("phone"),
            customer_name=row.get("customer"),
        )
        invoice_number = row.get("invoice_number") or _generate_invoice_number(business_id)
        return create_invoice(
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

    return _create_import_review_payload(
        business_id=business_id,
        text=json.dumps(row, sort_keys=True),
        metadata={**base_metadata, "source_type": source_type, "row": row},
        invoice_number=_extract_reference(row),
        amount=_extract_amount(row),
        method=row.get("payment_method") or None,
    )


def _create_import_review_payload(
    *,
    business_id: int,
    text: str,
    metadata: dict,
    invoice_number: str | None,
    amount: float | None,
    method: str | None,
    invoice_id: int | None = None,
    extracted_paid_at: str | None = None,
) -> dict:
    try:
        return create_text_payment_proof(
            business_id=business_id,
            uploaded_by_user_id=None,
            text=text,
            source_channel="import",
            invoice_id=invoice_id,
            extracted_amount=amount,
            extracted_reference=invoice_number,
            extracted_paid_at=extracted_paid_at,
            extracted_method=method,
            extra_payload=metadata,
            decision_reason="needs_manual_review",
        )
    except PaymentProofConflictError as exc:
        raise ValueError(str(exc)) from exc


def _handle_import_action(result: dict, *, row_number: int | None, action) -> None:
    try:
        payload = action()
    except Exception as exc:
        result["failed_count"] += 1
        result["failures"].append({"row_number": row_number, "message": str(exc)})
        return

    result["imported_count"] += 1
    if payload.get("intent"):
        if payload["intent"] == "invoice_created":
            result["invoices_created"] += 1
            return
        if payload["intent"] in {"payment_proof", "needs_review"}:
            result["payment_proofs_created"] += 1
            result["needs_review_count"] += 1
            return
    if payload.get("id") and "approved_payment_id" in payload:
        result["payment_proofs_created"] += 1
        if payload.get("review_state") == "needs_review":
            result["needs_review_count"] += 1
        return
    if payload.get("id") and payload.get("invoice_number"):
        result["invoices_created"] += 1
        return
    result["needs_review_count"] += 1


def _is_csv_source(
    source_type: str,
    filename: str | None,
    mime_type: str | None,
    raw_text: str | None,
    file_content: bytes | None,
) -> bool:
    if source_type == "csv_export":
        return True
    lowered_name = (filename or "").lower()
    lowered_mime = (mime_type or "").lower()
    if lowered_name.endswith(".csv") or lowered_mime == "text/csv":
        return True
    if file_content and source_type in {"google_drive_file", "local_file"}:
        return True
    if raw_text and "," in raw_text and "\n" in raw_text:
        return True
    return False


def _normalize_source_type(value: str) -> str:
    normalized = (value or "unknown").strip().lower()
    if normalized not in SUPPORTED_SOURCE_TYPES:
        return "unknown"
    return normalized


def _sender_to_phone(sender: str) -> str:
    digits = "".join(ch for ch in sender if ch.isdigit())
    return digits or sender


def _extract_reference(row: dict) -> str | None:
    for key in ("invoice_number", "reference"):
        value = row.get(key)
        if value:
            return value.strip().upper()
    return None


def _extract_amount(row: dict) -> float | None:
    for key in ("amount", "paid_amount", "total"):
        value = row.get(key)
        if not value:
            continue
        try:
            return float(str(value).replace("RM", "").replace("rm", "").strip())
        except ValueError:
            continue
    return None


def _row_to_payment_text(row: dict) -> str:
    parts = []
    if row.get("message"):
        parts.append(row["message"])
    if row.get("notes"):
        parts.append(row["notes"])
    reference = _extract_reference(row)
    amount = _extract_amount(row)
    if amount is not None and reference:
        parts.append(f"Paid RM{amount:.2f} for {reference}")
    if row.get("payment_method"):
        parts.append(f"via {row['payment_method']}")
    return " ".join(part for part in parts if part).strip() or json.dumps(row, sort_keys=True)


def _row_to_order_text(row: dict) -> str:
    if row.get("message"):
        return row["message"]
    qty = row.get("qty") or row.get("quantity") or "1"
    item = row.get("item") or row.get("notes") or "Item"
    total = row.get("total") or row.get("amount") or ""
    parts = [f"{item} x{qty}"]
    if total:
        parts.append(f"RM{total}")
    return " ".join(parts).strip()


def _looks_like_import_order(text: str) -> bool:
    if detect_payment(text).detected:
        return False
    lowered = text.lower()
    has_keyword = any(term in lowered for term in ["want", "order", "cake", "nasi", "mee", "brownie", "beli", "buy"])
    has_quantity = " x" in lowered or "x" in lowered
    has_amount = bool(AMOUNT_PATTERN.search(text))
    return bool(has_amount and (has_keyword or has_quantity))


def _resolve_customer_for_import(*, business_id: int, phone: str | None, customer_name: str | None) -> dict:
    normalized_phone = (phone or "").strip() or None
    normalized_name = (customer_name or "").strip() or None
    if normalized_phone:
        customer = get_customer_by_phone(business_id, normalized_phone)
        if customer:
            return customer
    if normalized_name:
        customer = get_customer_by_name(business_id, normalized_name)
        if customer:
            return customer
    return create_customer(
        {
            "business_id": business_id,
            "name": normalized_name or normalized_phone or "Imported Customer",
            "phone": normalized_phone,
        }
    )


def _generate_invoice_number(business_id: int) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"INV-{business_id}-{timestamp}"


def _extract_reference_from_metadata(metadata: dict) -> str | None:
    for key in ("invoice_number", "reference"):
        value = metadata.get(key)
        if value:
            return str(value).strip().upper()
    return None
