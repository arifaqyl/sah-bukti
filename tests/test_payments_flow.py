import asyncio

from httpx import ASGITransport, AsyncClient

from app.db.store import get_db, reset_db
from app.main import create_app
from app.services.auth import list_memberships
from app.services.customers import create_customer
from app.services.invoices import create_invoice, get_invoice
import app.services.payments as payments_service


def _seed_invoice(business_id: int) -> dict:
    customer = create_customer(
        {
            "business_id": business_id,
            "name": "Payment Customer",
            "phone": "60129990000",
        }
    )
    return create_invoice(
        {
            "business_id": business_id,
            "customer_id": customer["id"],
            "invoice_number": "PAY-INV-001",
            "items": [{"name": "Nasi Lemak", "quantity": 2, "unit_price": 15.0}],
            "subtotal": 30.0,
            "tax": 0.0,
            "total": 30.0,
            "payment_method": "pending",
            "payment_status": "pending",
            "due_date": "2026-06-30",
        }
    )


async def _signup(client: AsyncClient) -> tuple[str, int]:
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": "pay-owner@example.com", "password": "password123", "business_name": "Pay Biz"},
    )
    assert response.status_code == 201
    payload = response.json()
    memberships = list_memberships(payload["user"]["id"])
    return payload["access_token"], memberships[0]["business_id"]


def _auth_headers(token: str) -> dict:
    return {"authorization": f"Bearer {token}"}


def test_create_payment_link_and_page_route():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client)
            invoice = _seed_invoice(business_id)
            link_response = await client.post(
                f"/api/v1/payments/invoices/{invoice['id']}/payment-link",
                headers=_auth_headers(token),
                params={"business_id": business_id},
            )
            assert link_response.status_code == 200
            payload = link_response.json()
            assert payload["provider"] == "mock"
            assert payload["payment_link_url"].endswith(f"/pay.html?id={invoice['id']}")
            assert invoice["invoice_number"] in payload["whatsapp_text"]

            page_response = await client.get("/pay.html", params={"id": invoice["id"]})
            assert page_response.status_code == 200
            assert "Sah.Bukti Payment" in page_response.text

    asyncio.run(run())


def test_manual_qr_provider_is_selectable_and_non_mutating():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client)
            invoice = _seed_invoice(business_id)

            link_response = await client.post(
                f"/api/v1/payments/invoices/{invoice['id']}/payment-link",
                headers=_auth_headers(token),
                params={"business_id": business_id, "provider": "manual_qr"},
            )
            assert link_response.status_code == 200
            payload = link_response.json()
            assert payload["provider"] == "manual_qr"
            assert payload["payment_link_url"] is None
            assert payload["instructions"] is not None
            assert "payment proof" in payload["instructions"].lower()
            assert invoice["invoice_number"] in payload["whatsapp_text"]

        updated_invoice = get_invoice(invoice["id"], business_id)
        assert updated_invoice is not None
        assert updated_invoice["payment_status"] == "pending"

        with get_db() as conn:
            payment_count = conn.execute(
                "SELECT COUNT(*) AS count FROM payments WHERE invoice_id = ?",
                (invoice["id"],),
            ).fetchone()["count"]
        assert payment_count == 0

    asyncio.run(run())


def test_invalid_provider_is_rejected():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client)
            invoice = _seed_invoice(business_id)

            response = await client.post(
                f"/api/v1/payments/invoices/{invoice['id']}/payment-link",
                headers=_auth_headers(token),
                params={"business_id": business_id, "provider": "not_real"},
            )

        assert response.status_code == 400
        assert "Unsupported payment provider" in response.json()["detail"]

    asyncio.run(run())


def test_explicit_billplz_requires_configuration(monkeypatch):
    async def run() -> None:
        reset_db()
        monkeypatch.setattr(payments_service, "BILLPLZ_API_KEY", "")
        monkeypatch.setattr(payments_service, "BILLPLZ_COLLECTION_ID", "")
        app = create_app()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client)
            invoice = _seed_invoice(business_id)

            response = await client.post(
                f"/api/v1/payments/invoices/{invoice['id']}/payment-link",
                headers=_auth_headers(token),
                params={"business_id": business_id, "provider": "billplz"},
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "billplz is not configured"

    asyncio.run(run())


def test_billplz_webhook_route_is_not_mounted():
    async def run() -> None:
        reset_db()
        invoice = _seed_invoice(1)
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/payments/billplz-webhook",
                json={
                    "paid": True,
                    "reference_1": invoice["invoice_number"],
                    "transaction_id": "TXN-PAY-1",
                    "amount": 3000,
                },
            )
            assert response.status_code == 404

        updated_invoice = get_invoice(invoice["id"])
        assert updated_invoice is not None
        assert updated_invoice["payment_status"] == "pending"

        with get_db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) AS count FROM payments WHERE invoice_id = ? AND reference = ?",
                (invoice["id"], "TXN-PAY-1"),
            ).fetchone()["count"]
            proof_count = conn.execute(
                "SELECT COUNT(*) AS count FROM payment_proofs WHERE invoice_id = ? AND extracted_reference = ?",
                (invoice["id"], "TXN-PAY-1"),
            ).fetchone()["count"]
        assert count == 0
        assert proof_count == 0

    asyncio.run(run())
