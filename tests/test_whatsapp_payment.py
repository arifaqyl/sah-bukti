from app.api.routes.whatsapp import whatsapp_webhook_route
from app.db.store import get_db, reset_db
from app.schemas.whatsapp import WhatsAppWebhookRequest
from app.services.customers import create_customer
from app.services.invoices import create_invoice, get_invoice_by_number
from app.services.whatsapp import detect_payment


def _seed_invoice(
    invoice_number: str = "INV-P1",
    total: float = 200.0,
    customer_name: str = "Aina",
    phone: str = "60123456789",
) -> dict:
    customer = create_customer(
        {
            "business_id": 1,
            "name": customer_name,
            "phone": phone,
        }
    )
    return create_invoice(
        {
            "business_id": 1,
            "customer_id": customer["id"],
            "invoice_number": invoice_number,
            "items": [{"name": "nasi lemak", "quantity": 1, "unit_price": total}],
            "subtotal": total,
            "tax": 0,
            "total": total,
            "payment_method": "pending",
            "payment_status": "pending",
        }
    )


def _payload(message: str, phone: str = "60123456789", business_id: int = 1) -> WhatsAppWebhookRequest:
    return WhatsAppWebhookRequest.model_validate({"message": message, "from": phone, "business_id": business_id})


def test_detect_qr_payment():
    result = detect_payment("Paid RM200 for INV-P1 via QR")
    assert result.detected is True
    assert result.amount == 200.0
    assert result.invoice_number == "INV-P1"
    assert result.method == "qr"


def test_detect_transfer_payment():
    result = detect_payment("Payment RM150 via transfer for INV-O3")
    assert result.detected is True
    assert result.amount == 150.0
    assert result.invoice_number == "INV-O3"
    assert result.method == "transfer"


def test_detect_cash_payment():
    result = detect_payment("Cash paid 50 for INV-D1")
    assert result.detected is True
    assert result.amount == 50.0
    assert result.invoice_number == "INV-D1"
    assert result.method == "cash"


def test_detect_no_payment():
    result = detect_payment("Nasi lemak x2 RM9")
    assert result.detected is False


def test_detect_amount_without_rm():
    result = detect_payment("paid 300 for INV-P2")
    assert result.detected is True
    assert result.amount == 300.0


def test_whatsapp_webhook_records_payment():
    reset_db()
    created = _seed_invoice()

    response = whatsapp_webhook_route(_payload("Paid RM200 for INV-P1 via QR"))

    assert response == {
        "invoice_number": created["invoice_number"],
        "total": created["total"],
        "customer_name": "Aina",
    }

    invoice = get_invoice_by_number(created["invoice_number"])
    assert invoice is not None
    assert invoice["payment_status"] == "paid"
    assert invoice["payment_method"] == "qr"

    with get_db() as conn:
        payment_row = conn.execute(
            "SELECT amount, method, reference FROM payments WHERE invoice_id = ?",
            (created["id"],),
        ).fetchone()
    assert payment_row is not None
    assert float(payment_row["amount"]) == 200.0
    assert payment_row["method"] == "qr"
    assert str(payment_row["reference"]).startswith("WhatsApp-")


def test_whatsapp_webhook_partial_payment_marks_partial():
    reset_db()
    created = _seed_invoice(invoice_number="INV-PART", total=200.0)

    response = whatsapp_webhook_route(_payload("Paid RM50 for INV-PART via cash"))

    assert response["invoice_number"] == created["invoice_number"]

    invoice = get_invoice_by_number(created["invoice_number"])
    assert invoice is not None
    assert invoice["payment_status"] == "partial"
    assert invoice["payment_method"] == "cash"


def test_whatsapp_webhook_unknown_invoice_does_not_create_new_invoice():
    reset_db()

    response = whatsapp_webhook_route(_payload("Paid RM12 for INV-UNKNOWN via bank", phone="60125550000"))

    assert response == {
        "invoice_number": "INV-UNKNOWN",
        "total": 12.0,
        "customer_name": "60125550000",
    }

    with get_db() as conn:
        invoice_count = conn.execute("SELECT COUNT(*) AS count FROM invoices").fetchone()["count"]
        payment_count = conn.execute("SELECT COUNT(*) AS count FROM payments").fetchone()["count"]
    assert invoice_count == 0
    assert payment_count == 0
