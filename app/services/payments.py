import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass

import httpx

from app.config import (
    APP_BASE_URL,
    BILLPLZ_API_KEY,
    BILLPLZ_BASE_URL,
    BILLPLZ_CALLBACK_PATH,
    BILLPLZ_COLLECTION_ID,
    BILLPLZ_REDIRECT_PATH,
    BILLPLZ_X_SIGNATURE_KEY,
    SAHBUKTI_BRAND_NAME,
    MANUAL_QR_DESTINATION_TEXT,
    MOCK_PAYMENT_BASE_URL,
    PAYMENT_PROVIDER,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from app.db.store import get_db, utc_now
from app.services.invoices import get_invoice, get_invoice_by_number
from app.services.payment_proofs import PaymentProofConflictError, create_text_payment_proof


SUPPORTED_PAYMENT_PROVIDERS = {"mock", "manual_qr", "billplz"}


@dataclass(frozen=True)
class PaymentProviderResult:
    provider: str
    payment_link_url: str | None
    whatsapp_text: str
    instructions: str | None = None


class BasePaymentProvider:
    name: str

    def create_payment(self, invoice: dict) -> PaymentProviderResult:
        raise NotImplementedError


class MockPaymentProvider(BasePaymentProvider):
    name = "mock"

    def create_payment(self, invoice: dict) -> PaymentProviderResult:
        payment_link_url = f"{MOCK_PAYMENT_BASE_URL.rstrip('/')}/pay.html?id={invoice['id']}"
        return PaymentProviderResult(
            provider=self.name,
            payment_link_url=payment_link_url,
            whatsapp_text=_build_whatsapp_text(invoice, payment_link_url),
            instructions="Demo payment page. Payment proof still requires owner review before the invoice is marked paid.",
        )


class ManualQrPaymentProvider(BasePaymentProvider):
    name = "manual_qr"

    def create_payment(self, invoice: dict) -> PaymentProviderResult:
        instructions = (
            f"{MANUAL_QR_DESTINATION_TEXT}. "
            f"Use reference {invoice['invoice_number']}. "
            "After payment, send payment proof for review before the invoice is marked paid."
        )
        whatsapp_text = (
            f"Hi {invoice.get('customer_name') or 'there'},\n\n"
            f"Invoice {invoice['invoice_number']} for RM{float(invoice['total']):.2f} is ready.\n"
            f"{instructions}"
        )
        return PaymentProviderResult(
            provider=self.name,
            payment_link_url=None,
            whatsapp_text=whatsapp_text,
            instructions=instructions,
        )


class BillplzPaymentProvider(BasePaymentProvider):
    name = "billplz"

    def create_payment(self, invoice: dict) -> PaymentProviderResult:
        if not BILLPLZ_API_KEY or not BILLPLZ_COLLECTION_ID:
            raise ValueError("billplz is not configured")
        payment_link_url = _create_billplz_bill(invoice)["payment_link_url"]
        return PaymentProviderResult(
            provider=self.name,
            payment_link_url=payment_link_url,
            whatsapp_text=_build_whatsapp_text(invoice, payment_link_url),
            instructions="External Billplz checkout. Paid callbacks create reviewable proof; approval is still required before ledger update.",
        )


def create_payment_link(invoice_id: int, business_id: int, provider_name: str | None = None) -> dict:
    invoice = get_invoice(invoice_id, business_id)
    if not invoice:
        raise LookupError("Invoice not found")

    provider = get_payment_provider(provider_name)
    payment = provider.create_payment(invoice)
    return {
        "invoice_id": invoice["id"],
        "provider": payment.provider,
        "payment_link_url": payment.payment_link_url,
        "invoice_number": invoice["invoice_number"],
        "amount": float(invoice["total"]),
        "whatsapp_text": payment.whatsapp_text,
        "instructions": payment.instructions,
    }


def get_payment_provider(provider_name: str | None = None) -> BasePaymentProvider:
    resolved = (provider_name or PAYMENT_PROVIDER or "mock").strip().lower()
    if resolved == "billplz" and (not BILLPLZ_API_KEY or not BILLPLZ_COLLECTION_ID):
        if provider_name is None:
            resolved = "mock"
        else:
            raise ValueError("billplz is not configured")
    if resolved == "mock":
        return MockPaymentProvider()
    if resolved == "manual_qr":
        return ManualQrPaymentProvider()
    if resolved == "billplz":
        return BillplzPaymentProvider()
    raise ValueError(f"Unsupported payment provider: {resolved}")


def _create_billplz_bill(invoice: dict) -> dict:
    callback_url = f"{APP_BASE_URL}{BILLPLZ_CALLBACK_PATH}"
    redirect_url = f"{APP_BASE_URL}{BILLPLZ_REDIRECT_PATH}?id={invoice['id']}"
    payload = {
        "collection_id": BILLPLZ_COLLECTION_ID,
        "email": f"buyer+invoice-{invoice['id']}@sahbukti.local",
        "name": invoice["customer_name"],
        "amount": str(int(round(float(invoice["total"]) * 100))),
        "callback_url": callback_url,
        "redirect_url": redirect_url,
        "description": f"{invoice['invoice_number']} - {_invoice_summary(invoice)}",
        "reference_1_label": "Invoice",
        "reference_1": invoice["invoice_number"],
        "reference_2_label": "Customer",
        "reference_2": invoice["customer_name"],
    }
    with httpx.Client(timeout=30.0, auth=(BILLPLZ_API_KEY, "")) as client:
        response = client.post(f"{BILLPLZ_BASE_URL}/bills", data=payload)
        response.raise_for_status()
        data = response.json()
    return {
        "provider": "billplz",
        "payment_link_url": data["url"],
    }


def handle_billplz_webhook(payload: dict) -> dict:
    invoice_number = (
        payload.get("reference_1")
        or payload.get("billplz", {}).get("reference_1")
        or payload.get("invoice_number")
    )
    transaction_id = payload.get("transaction_id") or payload.get("txn_id")
    event_key = _build_billplz_event_key(payload)

    signature_valid = False
    processing_status = "received"
    if not BILLPLZ_X_SIGNATURE_KEY:
        processing_status = "missing_signature_config"
        _create_provider_callback_event(
            business_id=_resolve_callback_business_id(invoice_number),
            provider="billplz",
            event_key=event_key,
            invoice_number=invoice_number,
            transaction_id=transaction_id,
            payload=payload,
            signature_valid=False,
            processing_status=processing_status,
            processed_invoice_id=None,
        )
        return {"ok": False, "invoice_id": None, "status": processing_status}

    signature = str(payload.get("x_signature") or "")
    if not signature:
        processing_status = "missing_signature"
        _create_provider_callback_event(
            business_id=_resolve_callback_business_id(invoice_number),
            provider="billplz",
            event_key=event_key,
            invoice_number=invoice_number,
            transaction_id=transaction_id,
            payload=payload,
            signature_valid=False,
            processing_status=processing_status,
            processed_invoice_id=None,
        )
        return {"ok": False, "invoice_id": None, "status": processing_status}
    expected_signature = compute_billplz_x_signature(payload, BILLPLZ_X_SIGNATURE_KEY)
    if not hmac.compare_digest(signature.lower(), expected_signature.lower()):
        processing_status = "invalid_signature"
        _create_provider_callback_event(
            business_id=_resolve_callback_business_id(invoice_number),
            provider="billplz",
            event_key=event_key,
            invoice_number=invoice_number,
            transaction_id=transaction_id,
            payload=payload,
            signature_valid=False,
            processing_status=processing_status,
            processed_invoice_id=None,
        )
        return {"ok": False, "invoice_id": None, "status": processing_status}
    signature_valid = True

    existing_event = get_provider_callback_event("billplz", event_key)
    if existing_event:
        return {
            "ok": True,
            "invoice_id": existing_event.get("processed_invoice_id"),
            "status": "duplicate_event",
        }

    paid = payload.get("paid")
    if isinstance(paid, str):
        paid = paid.lower() == "true"
    if not paid:
        processing_status = "ignored_unpaid_event"
        _create_provider_callback_event(
            business_id=_resolve_callback_business_id(invoice_number),
            provider="billplz",
            event_key=event_key,
            invoice_number=invoice_number,
            transaction_id=transaction_id,
            payload=payload,
            signature_valid=signature_valid,
            processing_status=processing_status,
            processed_invoice_id=None,
        )
        return {"ok": True, "invoice_id": None, "status": processing_status}

    if not invoice_number:
        processing_status = "missing_invoice_reference"
        _create_provider_callback_event(
            business_id=None,
            provider="billplz",
            event_key=event_key,
            invoice_number=None,
            transaction_id=transaction_id,
            payload=payload,
            signature_valid=signature_valid,
            processing_status=processing_status,
            processed_invoice_id=None,
        )
        return {"ok": False, "invoice_id": None, "status": processing_status}

    invoice = get_invoice_by_number(invoice_number)
    if not invoice:
        processing_status = "invoice_not_found"
        _create_provider_callback_event(
            business_id=_resolve_callback_business_id(invoice_number),
            provider="billplz",
            event_key=event_key,
            invoice_number=invoice_number,
            transaction_id=transaction_id,
            payload=payload,
            signature_valid=signature_valid,
            processing_status=processing_status,
            processed_invoice_id=None,
        )
        return {"ok": False, "invoice_id": None, "status": processing_status}

    amount_value = payload.get("amount")
    amount = _parse_amount(amount_value, float(invoice["total"]))
    reference = (
        transaction_id
        or payload.get("id")
        or f"billplz-{invoice_number}-{secrets.token_hex(4)}"
    )

    processing_status = "proof_needs_review"
    try:
        create_text_payment_proof(
            business_id=int(invoice["business_id"]),
            uploaded_by_user_id=None,
            text=f"Billplz paid callback for {invoice_number}: RM{amount:.2f} reference {reference}",
            source_channel="billplz",
            invoice_id=int(invoice["id"]),
            extracted_amount=amount,
            extracted_reference=reference,
            extracted_method="transfer",
            extra_payload={"provider": "billplz", "event_key": event_key},
            decision_reason="provider_callback_needs_review",
        )
    except PaymentProofConflictError:
        processing_status = "duplicate_proof"
    _create_provider_callback_event(
        business_id=int(invoice["business_id"]),
        provider="billplz",
        event_key=event_key,
        invoice_number=invoice_number,
        transaction_id=transaction_id,
        payload=payload,
        signature_valid=signature_valid,
        processing_status=processing_status,
        processed_invoice_id=invoice["id"],
    )
    return {"ok": True, "invoice_id": invoice["id"], "status": processing_status}


def compute_billplz_x_signature(payload: dict, x_signature_key: str) -> str:
    source = _build_billplz_x_signature_source(payload)
    return hmac.new(
        x_signature_key.encode("utf-8"),
        source.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _build_billplz_x_signature_source(payload: dict) -> str:
    source_parts: list[str] = []
    for key, value in payload.items():
        if key == "x_signature" or value is None:
            continue
        normalized_key = key.replace("[", "").replace("]", "")
        source_parts.append(f"{normalized_key}{value}")
    source_parts.sort(key=str.lower)
    return "|".join(source_parts)


def _build_billplz_event_key(payload: dict) -> str:
    parts = [
        str(payload.get("transaction_id") or payload.get("txn_id") or ""),
        str(payload.get("id") or ""),
        str(payload.get("reference_1") or payload.get("invoice_number") or ""),
        str(payload.get("paid_at") or ""),
        str(payload.get("paid") or ""),
        str(payload.get("state") or ""),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _payload_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_provider_callback_event(provider: str, event_key: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM provider_callback_events
            WHERE provider = ? AND event_key = ?
            LIMIT 1
            """,
            (provider, event_key),
        ).fetchone()
    return dict(row) if row else None


def list_provider_callback_events(
    business_id: int,
    *,
    status: str | None = None,
    invoice_number: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    where_clauses = ["COALESCE(pce.business_id, processed_invoice.business_id, invoice_lookup.business_id) = ?"]
    params: list[object] = [business_id]
    if status:
        where_clauses.append("pce.processing_status = ?")
        params.append(status)
    if invoice_number:
        where_clauses.append("pce.invoice_number = ?")
        params.append(invoice_number)
    if date_from:
        where_clauses.append("date(pce.created_at) >= date(?)")
        params.append(date_from)
    if date_to:
        where_clauses.append("date(pce.created_at) <= date(?)")
        params.append(date_to)

    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT
                pce.*,
                COALESCE(processed_invoice.invoice_number, invoice_lookup.invoice_number, pce.invoice_number) AS resolved_invoice_number
            FROM provider_callback_events pce
            LEFT JOIN invoices processed_invoice ON processed_invoice.id = pce.processed_invoice_id
            LEFT JOIN invoices invoice_lookup ON invoice_lookup.invoice_number = pce.invoice_number
            WHERE {' AND '.join(where_clauses)}
            ORDER BY pce.id DESC
            """,
            params,
        ).fetchall()
    return [_serialize_provider_callback_event(row) for row in rows]


def _create_provider_callback_event(
    *,
    business_id: int | None,
    provider: str,
    event_key: str,
    invoice_number: str | None,
    transaction_id: str | None,
    payload: dict,
    signature_valid: bool,
    processing_status: str,
    processed_invoice_id: int | None,
) -> None:
    now = utc_now()
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO provider_callback_events (
                business_id,
                provider,
                event_key,
                invoice_number,
                transaction_id,
                transaction_reference,
                payload_json,
                raw_payload,
                payload_hash,
                signature_valid,
                processing_status,
                processed_invoice_id,
                proof_id,
                created_at,
                received_at,
                processed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                business_id,
                provider,
                event_key,
                invoice_number,
                transaction_id,
                transaction_id,
                json.dumps(payload, sort_keys=True),
                json.dumps(payload, sort_keys=True),
                _payload_hash(payload),
                1 if signature_valid else 0,
                processing_status,
                processed_invoice_id,
                None,
                now,
                now,
                now,
            ),
        )


def _serialize_provider_callback_event(row) -> dict:
    data = dict(row)
    payload_json = data.get("payload_json")
    if isinstance(payload_json, str):
        try:
            data["payload_json"] = json.loads(payload_json)
        except json.JSONDecodeError:
            data["payload_json"] = None
    data["invoice_number"] = data.get("resolved_invoice_number") or data.get("invoice_number")
    return data


def _resolve_callback_business_id(invoice_number: str | None) -> int | None:
    if not invoice_number:
        return None
    invoice = get_invoice_by_number(invoice_number)
    if not invoice:
        return None
    return int(invoice["business_id"])


def _parse_amount(amount_value, fallback: float) -> float:
    if amount_value is None:
        return fallback
    try:
        numeric = float(amount_value)
    except (TypeError, ValueError):
        return fallback
    return numeric / 100 if numeric > 1000 else numeric


def _send_telegram_alert(invoice: dict, amount: float) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    message = (
        f"{SAHBUKTI_BRAND_NAME} payment received\n"
        f"Invoice: {invoice['invoice_number']}\n"
        f"Customer: {invoice['customer_name']}\n"
        f"Amount: RM{amount:.2f}\n"
        f"Status: {invoice['payment_status'].upper()}"
    )
    with httpx.Client(timeout=10.0) as client:
        client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
        )


def _build_whatsapp_text(invoice: dict, payment_link_url: str) -> str:
    customer_name = invoice.get("customer_name") or "there"
    amount = float(invoice["total"])
    return (
        f"Hi {customer_name},\n\n"
        f"Invoice {invoice['invoice_number']} for RM{amount:.2f} is ready.\n"
        f"Pay here:\n{payment_link_url}\n\n"
        f"Reply with proof after payment. Sah.Bukti will queue it for owner review before status changes."
    )


def _invoice_summary(invoice: dict) -> str:
    items = invoice.get("items") or []
    if not items:
        return "Order"
    names = [str(item.get("name", "")).strip() for item in items if item.get("name")]
    if not names:
        return "Order"
    summary = ", ".join(names[:2])
    if len(names) > 2:
        summary += f" +{len(names) - 2} more"
    return summary
