import secrets
from urllib.parse import quote

import httpx

from app.config import (
    APP_BASE_URL,
    BILLPLZ_API_KEY,
    BILLPLZ_BASE_URL,
    BILLPLZ_CALLBACK_PATH,
    BILLPLZ_COLLECTION_ID,
    BILLPLZ_REDIRECT_PATH,
    KEDAIOPS_BRAND_NAME,
    MOCK_PAYMENT_BASE_URL,
    MOCK_PAYMENT_PREFIX,
    PAYMENT_PROVIDER,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from app.db.store import utc_now
from app.services.invoices import get_invoice, mark_invoice_paid_from_provider, update_invoice_payment_link


def create_payment_link(invoice_id: int) -> dict:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise ValueError("Invoice not found")

    provider = "billplz" if PAYMENT_PROVIDER == "billplz" and BILLPLZ_API_KEY and BILLPLZ_COLLECTION_ID else "mock"

    if provider == "billplz":
        payment = _create_billplz_bill(invoice)
    else:
        payment = _create_mock_payment(invoice)

    updated = update_invoice_payment_link(
        invoice_id=invoice_id,
        provider=payment["provider"],
        payment_link_url=payment["payment_link_url"],
        provider_bill_id=payment["provider_bill_id"],
    )
    if not updated:
        raise ValueError("Invoice disappeared during payment-link creation")
    return {
        "invoice_id": updated["id"],
        "provider": payment["provider"],
        "payment_link_url": payment["payment_link_url"],
        "provider_bill_id": payment["provider_bill_id"],
        "whatsapp_text": _build_whatsapp_text(updated, payment["payment_link_url"]),
    }


def _create_mock_payment(invoice: dict) -> dict:
    provider_bill_id = f"mock-{invoice['id']}-{secrets.token_hex(4)}"
    payment_link_url = f"{MOCK_PAYMENT_BASE_URL.rstrip('/')}{MOCK_PAYMENT_PREFIX}{invoice['id']}"
    return {
        "provider": "mock",
        "provider_bill_id": provider_bill_id,
        "payment_link_url": payment_link_url,
    }


def _create_billplz_bill(invoice: dict) -> dict:
    callback_url = f"{APP_BASE_URL}{BILLPLZ_CALLBACK_PATH}"
    redirect_url = f"{APP_BASE_URL}{BILLPLZ_REDIRECT_PATH}?id={invoice['id']}"
    payload = {
        "collection_id": BILLPLZ_COLLECTION_ID,
        "email": f"buyer+invoice-{invoice['id']}@kedaiops.local",
        "name": invoice["customer_name"],
        "amount": str(int(round(float(invoice["amount"]) * 100))),
        "callback_url": callback_url,
        "redirect_url": redirect_url,
        "description": f"{invoice['invoice_number']} - {invoice['item_description']}",
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
        "provider_bill_id": data["id"],
        "payment_link_url": data["url"],
    }


def handle_billplz_webhook(payload: dict) -> dict:
    bill_id = payload.get("id") or payload.get("billplz", {}).get("id")
    paid = payload.get("paid")
    if isinstance(paid, str):
        paid = paid.lower() == "true"
    if not bill_id:
        return {"ok": False, "invoice_id": None, "status": "missing_bill_id"}
    if not paid:
        return {"ok": True, "invoice_id": None, "status": "ignored_unpaid_event"}

    paid_at = payload.get("paid_at") or utc_now()
    reference = payload.get("transaction_id") or payload.get("txn_id") or payload.get("id")
    amount_value = payload.get("amount")
    amount = None
    if amount_value is not None:
        try:
            amount = float(amount_value) / 100 if float(amount_value) > 1000 else float(amount_value)
        except (TypeError, ValueError):
            amount = None

    invoice = mark_invoice_paid_from_provider(
        provider_bill_id=bill_id,
        amount=amount,
        reference=reference,
        paid_at=paid_at,
    )
    if not invoice:
        return {"ok": False, "invoice_id": None, "status": "invoice_not_found"}

    _send_telegram_alert(invoice)
    return {"ok": True, "invoice_id": invoice["id"], "status": "paid"}


def _send_telegram_alert(invoice: dict) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    message = (
        f"{KEDAIOPS_BRAND_NAME} payment received\n"
        f"Invoice: {invoice['invoice_number']}\n"
        f"Customer: {invoice['customer_name']}\n"
        f"Amount: RM{float(invoice['amount']):.2f}"
    )
    with httpx.Client(timeout=10.0) as client:
        client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
        )


def _build_whatsapp_text(invoice: dict, payment_link_url: str) -> str:
    customer_name = invoice.get("customer_name") or "there"
    amount = float(invoice["amount"])
    item = invoice["item_description"]
    return (
        f"Hi {customer_name},\n\n"
        f"Here is your payment link for {item} ({invoice['invoice_number']}) "
        f"for RM{amount:.2f}:\n{payment_link_url}\n\n"
        f"Pay here and I will get payment confirmation automatically."
    )
