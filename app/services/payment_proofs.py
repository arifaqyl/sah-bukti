import hashlib
import json
import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.config import UPLOADS_DIR
from app.db.store import get_db, utc_now
from app.services.invoices import get_invoice, get_invoice_by_number, record_invoice_payment


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}
AUTO_APPROVE_CONFIDENCE = 0.9


class PaymentProofError(Exception):
    pass


class PaymentProofNotFoundError(PaymentProofError):
    pass


class PaymentProofConflictError(PaymentProofError):
    pass


@dataclass(frozen=True)
class ProofExtractionResult:
    success: bool
    raw_payload: dict | None = None
    amount: float | None = None
    reference: str | None = None
    paid_at: str | None = None
    confidence_score: float | None = None
    error: str | None = None


class ProofExtractor(Protocol):
    def extract(self, file_path: Path) -> ProofExtractionResult:
        ...


class MockProofExtractor:
    def extract(self, file_path: Path) -> ProofExtractionResult:
        try:
            raw_text = file_path.read_text(encoding="utf-8")
            payload = json.loads(raw_text)
        except Exception as exc:
            return ProofExtractionResult(
                success=False,
                raw_payload=None,
                error=f"mock_extractor_unreadable: {exc}",
            )

        if payload.get("fail"):
            return ProofExtractionResult(
                success=False,
                raw_payload=payload,
                error=str(payload.get("error") or "mock_extractor_failed"),
            )

        amount = payload.get("amount")
        confidence_score = payload.get("confidence")
        try:
            amount_value = float(amount) if amount is not None else None
        except (TypeError, ValueError):
            amount_value = None
        try:
            confidence_value = float(confidence_score) if confidence_score is not None else None
        except (TypeError, ValueError):
            confidence_value = None

        reference = payload.get("reference")
        paid_at = payload.get("paid_at")
        return ProofExtractionResult(
            success=True,
            raw_payload=payload,
            amount=amount_value,
            reference=str(reference) if reference is not None else None,
            paid_at=str(paid_at) if paid_at is not None else None,
            confidence_score=confidence_value,
        )


def create_text_payment_proof(
    *,
    business_id: int,
    uploaded_by_user_id: int | None,
    text: str,
    source_channel: str,
    dedupe_key: str | None = None,
    invoice_id: int | None = None,
    extracted_amount: float | None = None,
    extracted_reference: str | None = None,
    extracted_paid_at: str | None = None,
    extracted_method: str | None = None,
    extra_payload: dict | None = None,
    decision_reason: str | None = None,
    auto_approve: bool = False,
) -> dict:
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("text evidence is required")

    invoice = None
    if invoice_id is not None:
        invoice = get_invoice(invoice_id, business_id)
        if not invoice:
            raise PaymentProofNotFoundError("Invoice not found")

    storage_dir = UPLOADS_DIR / "payment_proofs"
    storage_dir.mkdir(parents=True, exist_ok=True)
    saved_name = f"{uuid.uuid4()}.txt"
    file_path = storage_dir / saved_name
    file_bytes = normalized_text.encode("utf-8")
    file_path.write_bytes(file_bytes)
    hash_bytes = dedupe_key.encode("utf-8") if dedupe_key else file_bytes
    file_hash = hashlib.sha256(hash_bytes).hexdigest()

    existing = get_payment_proof_by_hash(business_id, file_hash)
    if existing:
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise PaymentProofConflictError("duplicate_file_hash")

    payload = {
        "raw_text": normalized_text,
        "source_channel": source_channel,
        "method": extracted_method,
        "invoice_number": extracted_reference,
    }
    if extra_payload:
        payload.update(extra_payload)
    media_metadata = (extra_payload or {}).get("media_metadata") or {}
    source_mime_type = str(
        media_metadata.get("mimetype")
        or media_metadata.get("mime_type")
        or "text/plain"
    ).strip() or "text/plain"
    now = utc_now()
    initial_review_state = "auto_approved" if auto_approve else "needs_review"
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO payment_proofs (
                business_id,
                invoice_id,
                uploaded_by_user_id,
                source_channel,
                file_path,
                file_hash,
                mime_type,
                file_size_bytes,
                ocr_status,
                ocr_error,
                ocr_payload,
                extracted_amount,
                extracted_reference,
                extracted_paid_at,
                confidence_score,
                review_state,
                decision_reason,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                business_id,
                invoice["id"] if invoice else None,
                uploaded_by_user_id,
                source_channel,
                str(file_path),
                file_hash,
                source_mime_type,
                len(file_bytes),
                "completed",
                None,
                json.dumps(payload),
                extracted_amount,
                extracted_reference,
                extracted_paid_at,
                None,
                initial_review_state,
                decision_reason or "proof_extracted",
                now,
            ),
        )
        proof_id = int(cursor.lastrowid)

    _append_event(proof_id, uploaded_by_user_id, "uploaded", {"source_channel": source_channel})
    _append_event(
        proof_id,
        uploaded_by_user_id,
        "proof_extracted",
        {
            "amount": extracted_amount,
            "reference": extracted_reference,
            "method": extracted_method,
            "invoice_id": invoice["id"] if invoice else None,
        },
    )

    if extracted_reference and _has_duplicate_reference(business_id, extracted_reference, exclude_proof_id=proof_id):
        _update_proof_fields(
            proof_id,
            business_id,
            {
                "review_state": "needs_review",
                "decision_reason": "duplicate_reference_detected",
            },
        )
        _append_event(
            proof_id,
            uploaded_by_user_id,
            "duplicate_reference_detected",
            {"reference": extracted_reference},
        )
        return get_payment_proof(proof_id, business_id)

    if auto_approve and invoice and extracted_amount:
        proof = approve_payment_proof(
            proof_id=proof_id,
            business_id=business_id,
            reviewer_user_id=uploaded_by_user_id,
            invoice_id=invoice["id"],
            amount=extracted_amount,
            reference=extracted_reference,
            method=extracted_method or "transfer",
            decision_reason="auto_approved",
        )
        return proof

    return get_payment_proof(proof_id, business_id)


def create_payment_proof(
    *,
    business_id: int,
    uploaded_by_user_id: int | None,
    file_bytes: bytes,
    original_filename: str,
    content_type: str | None,
    invoice_id: int | None = None,
    source_channel: str = "dashboard",
    extractor: ProofExtractor | None = None,
) -> dict:
    if not file_bytes:
        raise ValueError("file is required")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError(f"file exceeds max size of {MAX_UPLOAD_BYTES} bytes")

    mime_type = _normalize_mime_type(content_type, original_filename)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError("unsupported file type")

    invoice = None
    if invoice_id is not None:
        invoice = get_invoice(invoice_id, business_id)
        if not invoice:
            raise PaymentProofNotFoundError("Invoice not found")

    storage_dir = UPLOADS_DIR / "payment_proofs"
    storage_dir.mkdir(parents=True, exist_ok=True)
    extension = _resolve_extension(original_filename, mime_type)
    saved_name = f"{uuid.uuid4()}{extension}"
    file_path = storage_dir / saved_name
    file_path.write_bytes(file_bytes)
    file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

    existing = get_payment_proof_by_hash(business_id, file_hash)
    if existing:
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise PaymentProofConflictError("duplicate_file_hash")

    now = utc_now()
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO payment_proofs (
                business_id,
                invoice_id,
                uploaded_by_user_id,
                source_channel,
                file_path,
                file_hash,
                mime_type,
                file_size_bytes,
                ocr_status,
                review_state,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                business_id,
                invoice_id,
                uploaded_by_user_id,
                source_channel,
                str(file_path),
                file_hash,
                mime_type,
                len(file_bytes),
                "pending",
                "needs_review",
                now,
            ),
        )
        proof_id = int(cursor.lastrowid)
    _append_event(proof_id, uploaded_by_user_id, "uploaded", {"source_channel": source_channel})

    active_extractor = extractor or MockProofExtractor()
    result = active_extractor.extract(file_path)
    if not result.success:
        _update_proof_fields(
            proof_id,
            business_id,
            {
                "ocr_status": "failed",
                "ocr_error": result.error,
                "ocr_payload": json.dumps(result.raw_payload) if result.raw_payload is not None else None,
                "review_state": "needs_review",
                "decision_reason": "ocr_failed",
            },
        )
        _append_event(proof_id, uploaded_by_user_id, "ocr_failed", {"error": result.error})
        return get_payment_proof(proof_id, business_id)

    _update_proof_fields(
        proof_id,
        business_id,
        {
            "ocr_status": "completed",
            "ocr_error": None,
            "ocr_payload": json.dumps(result.raw_payload) if result.raw_payload is not None else None,
            "extracted_amount": result.amount,
            "extracted_reference": result.reference,
            "extracted_paid_at": result.paid_at,
            "confidence_score": result.confidence_score,
            "review_state": "needs_review",
            "decision_reason": "ocr_completed",
        },
    )
    _append_event(
        proof_id,
        uploaded_by_user_id,
        "ocr_succeeded",
        {
            "amount": result.amount,
            "reference": result.reference,
            "confidence_score": result.confidence_score,
        },
    )

    if result.reference and _has_duplicate_reference(business_id, result.reference, exclude_proof_id=proof_id):
        _update_proof_fields(
            proof_id,
            business_id,
            {
                "review_state": "needs_review",
                "decision_reason": "duplicate_reference_detected",
            },
        )
        _append_event(proof_id, uploaded_by_user_id, "duplicate_reference_detected", {"reference": result.reference})
        return get_payment_proof(proof_id, business_id)

    if (
        invoice
        and result.amount is not None
        and result.reference
        and (result.confidence_score or 0.0) >= AUTO_APPROVE_CONFIDENCE
        and abs(float(invoice["total"]) - float(result.amount)) < 0.01
    ):
        _update_proof_fields(
            proof_id,
            business_id,
            {"decision_reason": "strong_invoice_match_requires_owner_review"},
        )
        _append_event(
            proof_id,
            uploaded_by_user_id,
            "approval_required",
            {"reason": "strong_invoice_match_requires_owner_review"},
        )
        return get_payment_proof(proof_id, business_id)

    if invoice and result.amount is not None and abs(float(invoice["total"]) - float(result.amount)) >= 0.01:
        _update_proof_fields(
            proof_id,
            business_id,
            {"decision_reason": "amount_mismatch"},
        )
    elif invoice is None:
        _update_proof_fields(
            proof_id,
            business_id,
            {"decision_reason": "invoice_match_required"},
        )

    return get_payment_proof(proof_id, business_id)


def list_payment_proofs(
    business_id: int,
    *,
    review_state: str | None = None,
    invoice_number: str | None = None,
    source_channel: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    where_clauses = ["pp.business_id = ?"]
    params: list[object] = [business_id]
    if review_state:
        where_clauses.append("pp.review_state = ?")
        params.append(review_state)
    if invoice_number:
        where_clauses.append("i.invoice_number = ?")
        params.append(invoice_number)
    if source_channel:
        where_clauses.append("pp.source_channel = ?")
        params.append(source_channel)
    if date_from:
        where_clauses.append("date(pp.created_at) >= date(?)")
        params.append(date_from)
    if date_to:
        where_clauses.append("date(pp.created_at) <= date(?)")
        params.append(date_to)

    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT pp.*, i.invoice_number
            FROM payment_proofs pp
            LEFT JOIN invoices i ON i.id = pp.invoice_id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY pp.id DESC
            """,
            params,
        ).fetchall()
    return [_serialize_proof_row(row) for row in rows]


def get_payment_proof(proof_id: int, business_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT pp.*, i.invoice_number
            FROM payment_proofs pp
            LEFT JOIN invoices i ON i.id = pp.invoice_id
            WHERE pp.id = ? AND pp.business_id = ?
            """,
            (proof_id, business_id),
        ).fetchone()
    return _serialize_proof_row(row) if row else None


def get_payment_proof_by_hash(business_id: int, file_hash: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT pp.*, i.invoice_number
            FROM payment_proofs pp
            LEFT JOIN invoices i ON i.id = pp.invoice_id
            WHERE pp.business_id = ? AND pp.file_hash = ?
            """,
            (business_id, file_hash),
        ).fetchone()
    return _serialize_proof_row(row) if row else None


def list_payment_proof_events(proof_id: int, business_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT ppe.*
            FROM payment_proof_events ppe
            JOIN payment_proofs pp ON pp.id = ppe.payment_proof_id
            WHERE ppe.payment_proof_id = ? AND pp.business_id = ?
            ORDER BY ppe.id ASC
            """,
            (proof_id, business_id),
        ).fetchall()
    return [_serialize_event_row(row) for row in rows]


def approve_payment_proof(
    *,
    proof_id: int,
    business_id: int,
    reviewer_user_id: int | None,
    invoice_id: int | None = None,
    amount: float | None = None,
    reference: str | None = None,
    method: str = "transfer",
    decision_reason: str | None = None,
) -> dict:
    proof = get_payment_proof(proof_id, business_id)
    if not proof:
        raise PaymentProofNotFoundError("Payment proof not found")
    if proof["review_state"] == "rejected":
        return proof
    if proof["approved_payment_id"] is not None and proof["review_state"] in ("auto_approved", "approved"):
        return proof

    resolved_invoice_id = invoice_id or proof["invoice_id"]
    if resolved_invoice_id is None:
        resolved_invoice_id = _infer_invoice_id_for_proof(business_id, proof, amount=amount, reference=reference)
    if resolved_invoice_id is None:
        raise ValueError("invoice_id is required for approval. Edit the proof with invoice reference or amount first.")
    invoice = get_invoice(int(resolved_invoice_id), business_id)
    if not invoice:
        raise PaymentProofNotFoundError("Invoice not found")

    resolved_amount = amount if amount is not None else proof["extracted_amount"]
    if resolved_amount is None:
        raise ValueError("amount is required for approval")
    resolved_reference = reference or proof["extracted_reference"] or f"proof-{proof_id}"

    updated_invoice = record_invoice_payment(
        invoice["id"],
        {
            "amount": float(resolved_amount),
            "method": method,
            "reference": resolved_reference,
            "confirmed": True,
        },
        business_id,
    )
    if not updated_invoice:
        raise PaymentProofNotFoundError("Invoice not found")

    payment_id = _find_payment_id(invoice["id"], resolved_reference)
    now = utc_now()
    _update_proof_fields(
        proof_id,
        business_id,
        {
            "invoice_id": invoice["id"],
            "approved_payment_id": payment_id,
            "review_state": "auto_approved",
            "decision_reason": decision_reason or "manually_approved",
            "reviewed_at": now,
        },
    )
    _append_event(
        proof_id,
        reviewer_user_id,
        "approved",
        {
            "invoice_id": invoice["id"],
            "amount": float(resolved_amount),
            "reference": resolved_reference,
            "payment_id": payment_id,
        },
    )
    return get_payment_proof(proof_id, business_id)


def _infer_invoice_id_for_proof(
    business_id: int,
    proof: dict,
    *,
    amount: float | None = None,
    reference: str | None = None,
) -> int | None:
    candidate_reference = (reference or proof.get("extracted_reference") or proof.get("invoice_number") or "").strip()
    if candidate_reference:
        invoice = get_invoice_by_number(candidate_reference, business_id)
        if invoice:
            return int(invoice["id"])

    candidate_amount = amount if amount is not None else proof.get("extracted_amount")
    try:
        amount_value = float(candidate_amount) if candidate_amount is not None else None
    except (TypeError, ValueError):
        amount_value = None
    if amount_value is None:
        return None

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id
            FROM invoices
            WHERE business_id = ?
              AND ABS(total - ?) < 0.01
              AND payment_status IN ('pending', 'sent', 'partial')
            ORDER BY id DESC
            LIMIT 2
            """,
            (business_id, amount_value),
        ).fetchall()
    if len(rows) == 1:
        return int(rows[0]["id"])
    return None


def edit_payment_proof(
    *,
    proof_id: int,
    business_id: int,
    reviewer_user_id: int | None,
    amount: float | None = None,
    reference: str | None = None,
    method: str | None = None,
    decision_reason: str | None = None,
) -> dict:
    proof = get_payment_proof(proof_id, business_id)
    if not proof:
        raise PaymentProofNotFoundError("Payment proof not found")
    if proof["review_state"] == "auto_approved":
        raise ValueError("Undo approval before editing this proof")
    updates: dict = {}
    payload: dict = {}
    if amount is not None:
        updates["extracted_amount"] = float(amount)
        payload["amount"] = float(amount)
    if reference:
        updates["extracted_reference"] = reference
        payload["reference"] = reference
    if method:
        ocr_payload = proof.get("ocr_payload") or {}
        if isinstance(ocr_payload, dict):
            ocr_payload["method"] = method
            updates["ocr_payload"] = json.dumps(ocr_payload)
        payload["method"] = method
    if decision_reason:
        updates["decision_reason"] = decision_reason
    if not updates:
        return proof
    _update_proof_fields(proof_id, business_id, updates)
    _append_event(proof_id, reviewer_user_id, "edited", payload or {"decision_reason": decision_reason})
    return get_payment_proof(proof_id, business_id)


def undo_payment_proof_approval(
    *,
    proof_id: int,
    business_id: int,
    reviewer_user_id: int | None,
    decision_reason: str | None = None,
) -> dict:
    proof = get_payment_proof(proof_id, business_id)
    if not proof:
        raise PaymentProofNotFoundError("Payment proof not found")
    if proof["review_state"] != "auto_approved" or proof["approved_payment_id"] is None:
        raise ValueError("Proof is not approved")
    invoice_id = proof["invoice_id"]
    if invoice_id is None:
        raise ValueError("Approved proof is missing invoice_id")
    with get_db() as conn:
        conn.execute("DELETE FROM payments WHERE id = ?", (proof["approved_payment_id"],))
        totals = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS confirmed_total
            FROM payments
            WHERE invoice_id = ? AND confirmed = 1
            """,
            (invoice_id,),
        ).fetchone()
        invoice = get_invoice(invoice_id, business_id)
        confirmed_total = float(totals["confirmed_total"]) if totals else 0.0
        if invoice is not None:
            if confirmed_total <= 0.0:
                payment_status = "pending"
                paid_at = None
                payment_method = "pending"
            elif confirmed_total >= float(invoice["total"]):
                payment_status = "paid"
                payment_method = invoice.get("payment_method") or "transfer"
                paid_at = utc_now()
            else:
                payment_status = "partial"
                payment_method = invoice.get("payment_method") or "transfer"
                paid_at = utc_now()
            conn.execute(
                """
                UPDATE invoices
                SET payment_status = ?, payment_method = ?, paid_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (payment_status, payment_method, paid_at, utc_now(), invoice_id),
            )
    _update_proof_fields(
        proof_id,
        business_id,
        {
            "approved_payment_id": None,
            "review_state": "needs_review",
            "decision_reason": decision_reason or "approval_undone",
            "reviewed_at": utc_now(),
        },
    )
    _append_event(
        proof_id,
        reviewer_user_id,
        "approval_undone",
        {"invoice_id": invoice_id, "decision_reason": decision_reason or "approval_undone"},
    )
    return get_payment_proof(proof_id, business_id)


def reject_payment_proof(
    *,
    proof_id: int,
    business_id: int,
    reviewer_user_id: int | None,
    decision_reason: str,
) -> dict:
    proof = get_payment_proof(proof_id, business_id)
    if not proof:
        raise PaymentProofNotFoundError("Payment proof not found")
    if proof["review_state"] == "auto_approved":
        return proof
    if proof["review_state"] == "rejected":
        return proof

    now = utc_now()
    _update_proof_fields(
        proof_id,
        business_id,
        {
            "review_state": "rejected",
            "decision_reason": decision_reason,
            "reviewed_at": now,
        },
    )
    _append_event(proof_id, reviewer_user_id, "rejected", {"decision_reason": decision_reason})
    return get_payment_proof(proof_id, business_id)


def _normalize_mime_type(content_type: str | None, original_filename: str) -> str:
    if content_type:
        return content_type.lower().split(";", 1)[0].strip()
    guessed, _ = mimetypes.guess_type(original_filename)
    return (guessed or "").lower()


def _resolve_extension(original_filename: str, mime_type: str) -> str:
    suffix = Path(original_filename).suffix.lower()
    allowed_suffixes = set(ALLOWED_MIME_TYPES.values())
    if suffix in allowed_suffixes:
        return suffix
    return ALLOWED_MIME_TYPES[mime_type]


def _update_proof_fields(proof_id: int, business_id: int, fields: dict) -> None:
    updates = {key: value for key, value in fields.items() if key in {
        "invoice_id",
        "approved_payment_id",
        "ocr_status",
        "ocr_error",
        "ocr_payload",
        "extracted_amount",
        "extracted_reference",
        "extracted_paid_at",
        "confidence_score",
        "review_state",
        "decision_reason",
        "reviewed_at",
    }}
    if not updates:
        return
    set_clause = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [proof_id, business_id]
    with get_db() as conn:
        conn.execute(
            f"""
            UPDATE payment_proofs
            SET {set_clause}
            WHERE id = ? AND business_id = ?
            """,
            values,
        )


def _append_event(payment_proof_id: int, actor_user_id: int | None, event_type: str, payload: dict | None) -> None:
    with get_db() as conn:
        proof_exists = conn.execute(
            "SELECT 1 FROM payment_proofs WHERE id = ? LIMIT 1",
            (payment_proof_id,),
        ).fetchone()
        if not proof_exists:
            return
        conn.execute(
            """
            INSERT INTO payment_proof_events (payment_proof_id, actor_user_id, event_type, event_payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payment_proof_id,
                actor_user_id,
                event_type,
                json.dumps(payload) if payload is not None else None,
                utc_now(),
            ),
        )


def _find_payment_id(invoice_id: int, reference: str) -> int | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id
            FROM payments
            WHERE invoice_id = ? AND reference = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (invoice_id, reference),
        ).fetchone()
    return int(row["id"]) if row else None


def _has_duplicate_reference(business_id: int, reference: str, exclude_proof_id: int | None = None) -> bool:
    with get_db() as conn:
        payment_row = conn.execute(
            """
            SELECT 1
            FROM payments p
            JOIN invoices i ON i.id = p.invoice_id
            WHERE i.business_id = ? AND p.reference = ?
            LIMIT 1
            """,
            (business_id, reference),
        ).fetchone()
        if payment_row:
            return True
        if exclude_proof_id is None:
            proof_row = conn.execute(
                """
                SELECT 1
                FROM payment_proofs
                WHERE business_id = ? AND extracted_reference = ?
                LIMIT 1
                """,
                (business_id, reference),
            ).fetchone()
        else:
            proof_row = conn.execute(
                """
                SELECT 1
                FROM payment_proofs
                WHERE business_id = ? AND extracted_reference = ? AND id != ?
                LIMIT 1
                """,
                (business_id, reference, exclude_proof_id),
            ).fetchone()
    return bool(proof_row)


def _serialize_proof_row(row) -> dict:
    if row is None:
        return {}
    data = dict(row)
    for key in ("ocr_payload",):
        value = data.get(key)
        if isinstance(value, str):
            try:
                data[key] = json.loads(value)
            except json.JSONDecodeError:
                data[key] = None
    return data


def _serialize_event_row(row) -> dict:
    data = dict(row)
    payload = data.get("event_payload")
    if isinstance(payload, str):
        try:
            data["event_payload"] = json.loads(payload)
        except json.JSONDecodeError:
            data["event_payload"] = None
    return data
