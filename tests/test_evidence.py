import asyncio

from httpx import ASGITransport, AsyncClient

from app.db.store import get_db, reset_db
from app.main import create_app
from app.services.auth import list_memberships
from app.services.customers import create_customer
from app.services.invoices import create_invoice, get_invoice


def _auth_headers(token: str) -> dict:
    return {"authorization": f"Bearer {token}"}


async def _signup(client: AsyncClient, email: str, business_name: str) -> tuple[str, int]:
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "password123", "business_name": business_name},
    )
    assert response.status_code == 201
    payload = response.json()
    memberships = list_memberships(payload["user"]["id"])
    return payload["access_token"], memberships[0]["business_id"]


def _seed_invoice(business_id: int, invoice_number: str = "INV-EVID-1", total: float = 45.0) -> dict:
    customer = create_customer(
        {
            "business_id": business_id,
            "name": "Evidence Customer",
            "phone": "60124440000",
        }
    )
    return create_invoice(
        {
            "business_id": business_id,
            "customer_id": customer["id"],
            "invoice_number": invoice_number,
            "items": [{"name": "Cake Box", "quantity": 1, "unit_price": total}],
            "subtotal": total,
            "tax": 0.0,
            "total": total,
            "payment_method": "pending",
            "payment_status": "pending",
            "due_date": "2026-06-30",
        }
    )


def test_evidence_whatsapp_route_scope_and_non_mutating_flow():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_a, business_a = await _signup(client, "evidence-a@example.com", "Evidence A")
            token_b, business_b = await _signup(client, "evidence-b@example.com", "Evidence B")
            invoice = _seed_invoice(business_a, invoice_number="INV-EVID-VOICE", total=45.0)

            unauth = await client.post(
                "/api/v1/evidence/whatsapp",
                params={"business_id": business_a},
                json={"from_phone": "60124440000", "transcript": "Paid RM45 for INV-EVID-VOICE", "media_type": "voice_note"},
            )
            assert unauth.status_code == 401

            cross = await client.post(
                "/api/v1/evidence/whatsapp",
                headers=_auth_headers(token_b),
                params={"business_id": business_a},
                json={"from_phone": "60124440000", "transcript": "Paid RM45 for INV-EVID-VOICE", "media_type": "voice_note"},
            )
            assert cross.status_code == 403

            voice = await client.post(
                "/api/v1/evidence/whatsapp",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
                json={
                    "business_id": business_a,
                    "from_phone": "60124440000",
                    "transcript": "Hey, I just paid RM45 for INV-EVID-VOICE via QR",
                    "media_type": "voice_note",
                    "media_metadata": {"filename": "voice-note.ogg"},
                },
            )
            assert voice.status_code == 200
            payload = voice.json()
            assert payload["intent"] == "payment_proof"
            assert payload["payment_proof"]["review_state"] == "needs_review"
            assert payload["payment_proof"]["invoice_id"] == invoice["id"]
            assert payload["invoice"] is None

            unchanged = get_invoice(invoice["id"], business_a)
            assert unchanged is not None
            assert unchanged["payment_status"] == "pending"
            with get_db() as conn:
                payment_count = conn.execute(
                    "SELECT COUNT(*) AS count FROM payments WHERE invoice_id = ?",
                    (invoice["id"],),
                ).fetchone()["count"]
            assert payment_count == 0

            approve = await client.post(
                f"/api/v1/payment-proofs/{payload['payment_proof']['id']}/approve",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
                json={"invoice_id": invoice["id"], "amount": 45.0, "reference": "EVID-VOICE-APPROVED", "method": "qr"},
            )
            assert approve.status_code == 200
            after = get_invoice(invoice["id"], business_a)
            assert after is not None
            assert after["payment_status"] == "paid"

            order = await client.post(
                "/api/v1/evidence/whatsapp",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
                json={
                    "from_phone": "60125550000",
                    "message": "I want 2 chocolate cakes total RM90",
                    "media_type": "text",
                },
            )
            assert order.status_code == 200
            order_payload = order.json()
            assert order_payload["intent"] == "invoice_created"
            assert order_payload["invoice"]["payment_status"] == "pending"
            assert order_payload["payment_proof"] is None

            unknown = await client.post(
                "/api/v1/evidence/whatsapp",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
                json={
                    "from_phone": "60126660000",
                    "message": "can check my order later",
                    "media_type": "text",
                },
            )
            assert unknown.status_code == 200
            unknown_payload = unknown.json()
            assert unknown_payload["intent"] == "needs_review"
            assert unknown_payload["payment_proof"]["review_state"] == "needs_review"
            assert unknown_payload["invoice"] is None

            receipt = await client.post(
                "/api/v1/evidence/whatsapp",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
                json={
                    "from_phone": "60127770000",
                    "media_type": "receipt_image",
                    "media_metadata": {"filename": "receipt.jpg", "mime_type": "image/jpeg"},
                },
            )
            assert receipt.status_code == 200
            receipt_payload = receipt.json()
            assert receipt_payload["intent"] == "payment_proof"
            assert receipt_payload["payment_proof"]["invoice_id"] is None

    asyncio.run(run())
