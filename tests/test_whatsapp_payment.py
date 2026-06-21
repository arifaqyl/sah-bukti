from app.api.routes.whatsapp import whatsapp_webhook_route
from app.db.store import get_db, get_default_business_id, reset_db
from app.schemas.whatsapp import WhatsAppWebhookRequest
from app.services.customers import create_customer
from app.services.payment_proofs import approve_payment_proof, list_payment_proof_events
from app.services.invoices import create_invoice, get_invoice_by_number
from app.services.parser import parse_order
from app.services.whatsapp import detect_payment


def _call_whatsapp_webhook(payload: WhatsAppWebhookRequest) -> dict:
    import app.api.routes.whatsapp as whatsapp_route

    previous_secret = whatsapp_route.SAHBUKTI_WEBHOOK_SECRET
    whatsapp_route.SAHBUKTI_WEBHOOK_SECRET = "test-secret"
    previous_client_factory = whatsapp_route.get_whatsapp_client
    whatsapp_route.get_whatsapp_client = lambda: type(
        "StubClient",
        (),
        {
            "download_media": lambda self, media: None,
            "send_message": lambda self, phone, text: type("Result", (), {"ok": True, "provider": "mock", "detail": "sent"})(),
            "send_buttons": lambda self, phone, text, buttons: type("Result", (), {"ok": True, "provider": "mock", "detail": "sent"})(),
        },
    )()
    with get_db() as conn:
        conn.execute(
            "UPDATE businesses SET owner_whatsapp = ? WHERE id = ?",
            (payload.from_phone, payload.business_id),
        )
    try:
        return whatsapp_webhook_route(payload, x_sahbukti_webhook_secret="test-secret")
    finally:
        whatsapp_route.SAHBUKTI_WEBHOOK_SECRET = previous_secret
        whatsapp_route.get_whatsapp_client = previous_client_factory


def _seed_invoice(
    business_id: int = 1,
    invoice_number: str = "INV-P1",
    total: float = 200.0,
    customer_name: str = "Aina",
    phone: str = "60123456789",
) -> dict:
    customer = create_customer(
        {
            "business_id": business_id,
            "name": customer_name,
            "phone": phone,
        }
    )
    return create_invoice(
        {
            "business_id": business_id,
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


def test_parse_order_requires_explicit_business_id():
    try:
        parse_order("nasi lemak x2 RM9")  # type: ignore[call-arg]
    except TypeError:
        return
    raise AssertionError("parse_order should require business_id")


def test_whatsapp_webhook_payment_creates_reviewable_proof_without_mutating_invoice():
    reset_db()
    created = _seed_invoice()

    response = _call_whatsapp_webhook(_payload("Paid RM200 for INV-P1 via QR"))

    assert response == {
        "invoice_number": created["invoice_number"],
        "total": created["total"],
        "customer_name": "60123456789",
    }

    invoice = get_invoice_by_number(created["invoice_number"])
    assert invoice is not None
    assert invoice["payment_status"] == "pending"
    assert invoice["payment_method"] == "pending"

    with get_db() as conn:
        payment_count = conn.execute(
            "SELECT COUNT(*) AS count FROM payments WHERE invoice_id = ?",
            (created["id"],),
        ).fetchone()["count"]
        proof_row = conn.execute(
            """
            SELECT id, invoice_id, source_channel, review_state, approved_payment_id, ocr_status,
                   extracted_amount, extracted_reference, mime_type
            FROM payment_proofs
            WHERE business_id = ? AND invoice_id = ?
            """,
            (1, created["id"]),
        ).fetchone()
    assert payment_count == 0
    assert proof_row is not None
    assert proof_row["source_channel"] == "whatsapp"
    assert proof_row["review_state"] == "needs_review"
    assert proof_row["approved_payment_id"] is None
    assert proof_row["ocr_status"] == "completed"
    assert float(proof_row["extracted_amount"]) == 200.0
    assert proof_row["extracted_reference"] == created["invoice_number"]
    assert proof_row["mime_type"] == "text/plain"


def test_whatsapp_proof_approval_updates_invoice_through_normal_payment_path():
    reset_db()
    created = _seed_invoice(invoice_number="INV-APPROVE", total=200.0)

    response = _call_whatsapp_webhook(_payload("Paid RM200 for INV-APPROVE via cash"))
    assert response["invoice_number"] == created["invoice_number"]

    with get_db() as conn:
        proof_row = conn.execute(
            "SELECT id FROM payment_proofs WHERE business_id = ? AND invoice_id = ?",
            (1, created["id"]),
        ).fetchone()
    assert proof_row is not None

    approved = approve_payment_proof(
        proof_id=int(proof_row["id"]),
        business_id=1,
        reviewer_user_id=None,
        invoice_id=created["id"],
        amount=200.0,
        reference="WA-APPROVED-1",
        method="cash",
        decision_reason="whatsapp_review_approved",
    )
    assert approved["review_state"] == "auto_approved"
    assert approved["approved_payment_id"] is not None

    invoice = get_invoice_by_number(created["invoice_number"])
    assert invoice is not None
    assert invoice["payment_status"] == "paid"
    assert invoice["payment_method"] == "cash"

    events = list_payment_proof_events(int(proof_row["id"]), 1)
    assert [event["event_type"] for event in events] == ["uploaded", "proof_extracted", "approved"]


def test_whatsapp_webhook_unknown_invoice_creates_unmatched_proof_only():
    reset_db()

    response = _call_whatsapp_webhook(_payload("Paid RM12 for INV-UNKNOWN via bank", phone="60125550000"))

    assert response == {
        "invoice_number": "INV-UNKNOWN",
        "total": 12.0,
        "customer_name": "60125550000",
    }

    with get_db() as conn:
        invoice_count = conn.execute("SELECT COUNT(*) AS count FROM invoices").fetchone()["count"]
        payment_count = conn.execute("SELECT COUNT(*) AS count FROM payments").fetchone()["count"]
        proof_row = conn.execute(
            """
            SELECT invoice_id, source_channel, review_state, extracted_amount, extracted_reference
            FROM payment_proofs
            WHERE business_id = ?
            """,
            (1,),
        ).fetchone()
    assert invoice_count == 0
    assert payment_count == 0
    assert proof_row is not None
    assert proof_row["invoice_id"] is None
    assert proof_row["source_channel"] == "whatsapp"
    assert proof_row["review_state"] == "needs_review"
    assert float(proof_row["extracted_amount"]) == 12.0
    assert proof_row["extracted_reference"] == "INV-UNKNOWN"


def test_duplicate_whatsapp_payment_text_does_not_create_payment_or_duplicate_proof():
    reset_db()
    created = _seed_invoice(invoice_number="INV-DUP-WA", total=80.0)

    _call_whatsapp_webhook(_payload("Paid RM80 for INV-DUP-WA via QR"))
    _call_whatsapp_webhook(_payload("Paid RM80 for INV-DUP-WA via QR"))

    with get_db() as conn:
        payment_count = conn.execute(
            "SELECT COUNT(*) AS count FROM payments WHERE invoice_id = ?",
            (created["id"],),
        ).fetchone()["count"]
        proof_count = conn.execute(
            "SELECT COUNT(*) AS count FROM payment_proofs WHERE business_id = ? AND invoice_id = ?",
            (1, created["id"]),
        ).fetchone()["count"]
    assert payment_count == 0
    assert proof_count == 1


def test_whatsapp_event_document_without_caption_creates_reviewable_proof(monkeypatch):
    reset_db()
    business_id = get_default_business_id()
    _seed_invoice(business_id=business_id, invoice_number="INV-PDF-1", total=90.0)
    import app.api.routes.whatsapp as whatsapp_route

    previous_secret = whatsapp_route.SAHBUKTI_WEBHOOK_SECRET
    whatsapp_route.SAHBUKTI_WEBHOOK_SECRET = "test-secret"
    monkeypatch.setattr(
        whatsapp_route,
        "get_whatsapp_client",
        lambda: type(
            "StubClient",
            (),
            {
                "download_media": lambda self, media: None,
                "send_message": lambda self, phone, text: type("Result", (), {"ok": True, "provider": "mock", "detail": "sent"})(),
                "send_buttons": lambda self, phone, text, buttons: type("Result", (), {"ok": True, "provider": "mock", "detail": "sent"})(),
            },
        )(),
    )
    try:
        response = whatsapp_route._handle_whatsapp_webhook_payload(
            raw={
                "event": "message",
                "payload": {
                    "from": "60123456789@c.us",
                    "chatId": "60123456789@c.us",
                    "type": "document",
                    "hasMedia": True,
                    "body": "",
                    "media": {
                        "filename": "receipt.pdf",
                        "mimetype": "application/pdf",
                    },
                },
                "business_id": business_id,
            },
            x_sahbukti_webhook_secret="test-secret",
            token=None,
        )
    finally:
        whatsapp_route.SAHBUKTI_WEBHOOK_SECRET = previous_secret

    assert response["invoice_number"] == "REVIEW-PENDING"
    assert response["total"] == 0.0

    with get_db() as conn:
        proof_row = conn.execute(
            """
            SELECT source_channel, review_state, mime_type, invoice_id
            FROM payment_proofs
            WHERE business_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (business_id,),
        ).fetchone()
    assert proof_row is not None
    assert proof_row["source_channel"] == "whatsapp"
    assert proof_row["review_state"] == "needs_review"
    assert proof_row["mime_type"] == "application/pdf"
    assert proof_row["invoice_id"] is None
