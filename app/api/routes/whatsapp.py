from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, status

from app.config import KEDAIOPS_WEBHOOK_SECRET
from app.schemas.whatsapp import WhatsAppWebhookRequest, WhatsAppWebhookResponse
from app.services.customers import create_customer, get_customer_by_name, get_customer_by_phone
from app.services.inventory import deduct_ingredients
from app.services.invoices import create_invoice, get_invoice_by_number as get_invoice_by_number_global, record_payment
from app.services.parser import parse_order
from app.services.whatsapp import detect_payment, get_whatsapp_client


router = APIRouter()


@router.post("/webhook/whatsapp", response_model=WhatsAppWebhookResponse, status_code=status.HTTP_201_CREATED)
def whatsapp_webhook_route(
    payload: WhatsAppWebhookRequest,
    x_kede_webhook_secret: str | None = Header(default=None),
) -> dict:
    if KEDAIOPS_WEBHOOK_SECRET and x_kede_webhook_secret != KEDAIOPS_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    payment_info = detect_payment(payload.message)
    if payment_info.detected and payment_info.invoice_number:
        invoice = get_invoice_by_number(payload.business_id, payment_info.invoice_number)
        if invoice is None:
            invoice = get_invoice_by_number_global(payment_info.invoice_number)
        if invoice:
            recorded_amount = payment_info.amount if payment_info.amount is not None else float(invoice["total"])
            updated_invoice = record_payment(
                invoice_id=invoice["id"],
                amount=recorded_amount,
                method=payment_info.method or "cash",
                reference="WhatsApp-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
            )
            if updated_invoice is not None:
                payment_status = "paid" if recorded_amount >= float(invoice["total"]) else "partial"
                get_whatsapp_client().send_message(
                    payload.from_phone,
                    f"Payment received! RM{recorded_amount:.2f} for {payment_info.invoice_number} "
                    f"via {payment_info.method or 'cash'}. Status: {payment_status.upper()}. Thank you!",
                )
                return _build_webhook_response(updated_invoice)
        return {
            "invoice_number": payment_info.invoice_number,
            "total": payment_info.amount or 0.0,
            "customer_name": payload.from_phone,
        }

    parsed = parse_order(payload.message, payload.business_id)
    customer_name = parsed.get("customer_name") or payload.from_phone
    customer = get_customer_by_phone(payload.business_id, payload.from_phone)
    if not customer and parsed.get("customer_name"):
        customer = get_customer_by_name(payload.business_id, parsed["customer_name"])
    if not customer:
        customer = create_customer(
            {
                "business_id": payload.business_id,
                "name": customer_name,
                "phone": payload.from_phone,
            }
        )

    invoice_number = _generate_invoice_number(payload.business_id)
    invoice = create_invoice(
        {
            "business_id": payload.business_id,
            "customer_id": customer["id"],
            "invoice_number": invoice_number,
            "items": parsed["items"],
            "subtotal": parsed["total"],
            "tax": 0,
            "total": parsed["total"],
            "payment_method": parsed["payment_method"],
            "payment_status": "pending",
        }
    )
    deduct_ingredients(payload.business_id, parsed["items"])

    whatsapp = get_whatsapp_client()
    whatsapp.send_message(
        payload.from_phone,
        f"Order received! Invoice {invoice_number} created. Total: RM{parsed['total']:.2f}. We'll confirm shortly.",
    )

    return {
        "invoice_number": invoice["invoice_number"],
        "total": invoice["total"],
        "customer_name": customer["name"],
    }


def _generate_invoice_number(business_id: int) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"INV-{business_id}-{timestamp}"


def _build_webhook_response(invoice: dict) -> dict:
    return {
        "invoice_number": invoice["invoice_number"],
        "total": invoice["total"],
        "customer_name": invoice["customer_name"],
    }


def get_invoice_by_number(business_id: int, invoice_number: str) -> dict | None:
    """Look up invoice by its number within a business."""
    from app.db.store import get_db

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT i.*, c.name AS customer_name
            FROM invoices i
            LEFT JOIN customers c ON c.id = i.customer_id
            WHERE i.business_id = ? AND i.invoice_number = ?
            """,
            (business_id, invoice_number),
        ).fetchone()
    return dict(row) if row else None
