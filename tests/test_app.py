import asyncio

from httpx import ASGITransport, AsyncClient

from app.db.store import reset_db
from app.db.store import get_db
from app.main import create_app
from app.services.auth import list_memberships


def test_healthcheck():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    asyncio.run(run())


async def _signup(client: AsyncClient, email: str = "owner@example.com") -> tuple[str, int]:
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "password123", "business_name": "Owner Bakery"},
    )
    assert response.status_code == 201
    payload = response.json()
    memberships = list_memberships(payload["user"]["id"])
    return payload["access_token"], memberships[0]["business_id"]


def _auth_headers(token: str) -> dict:
    return {"authorization": f"Bearer {token}"}


def test_core_sahbukti_flow():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client)
            headers = _auth_headers(token)
            customer_resp = await client.post(
                "/api/v1/customers",
                headers=headers,
                params={"business_id": business_id},
                json={
                    "name": "Test Customer",
                    "phone": "012345678",
                    "email": "test@example.com",
                },
            )
            assert customer_resp.status_code == 200
            customer = customer_resp.json()

            invoice_resp = await client.post(
                "/api/v1/invoices",
                headers=headers,
                params={"business_id": business_id},
                json={
                    "customer_id": customer["id"],
                    "invoice_number": "KDE-INV-001",
                    "items": [{"name": "Consulting", "qty": 1, "price": 250.0}],
                    "subtotal": 250.0,
                    "tax": 0.0,
                    "total": 250.0,
                    "payment_method": "pending",
                    "payment_status": "pending",
                    "due_date": "2026-06-30",
                },
            )
            assert invoice_resp.status_code == 200
            invoice = invoice_resp.json()
            assert invoice["total"] == 250.0

            list_resp = await client.get("/api/v1/invoices", headers=headers, params={"business_id": business_id})
            assert list_resp.status_code == 200
            assert len(list_resp.json()) == 1

            patch_resp = await client.patch(
                f"/api/v1/invoices/{invoice['id']}",
                headers=headers,
                params={"business_id": business_id},
                json={"payment_method": "qr", "payment_status": "sent"},
            )
            assert patch_resp.status_code == 200
            assert patch_resp.json()["payment_method"] == "qr"

            legacy_payment_resp = await client.post(
                f"/api/v1/invoices/{invoice['id']}/payment",
                headers=headers,
                params={"business_id": business_id},
                json={
                    "amount": 250.0,
                    "method": "qr",
                    "reference": "REF-123",
                    "confirmed": True,
                },
            )
            assert legacy_payment_resp.status_code == 410

            evidence_resp = await client.post(
                "/api/v1/evidence/whatsapp",
                headers=headers,
                params={"business_id": business_id},
                json={
                    "business_id": business_id,
                    "from_phone": "012345678",
                    "message": "Paid RM250 for KDE-INV-001 via QR",
                    "media_type": "text",
                    "media_metadata": {},
                },
            )
            assert evidence_resp.status_code == 200
            proof = evidence_resp.json()["payment_proof"]

            pending_resp = await client.get(
                f"/api/v1/invoices/{invoice['id']}",
                headers=headers,
                params={"business_id": business_id},
            )
            assert pending_resp.status_code == 200
            assert pending_resp.json()["payment_status"] == "sent"

            approve_resp = await client.post(
                f"/api/v1/payment-proofs/{proof['id']}/approve",
                headers=headers,
                params={"business_id": business_id},
                json={
                    "invoice_id": invoice["id"],
                    "amount": 250.0,
                    "method": "qr",
                    "reference": "REF-123",
                    "decision_reason": "core_flow_owner_approval",
                },
            )
            assert approve_resp.status_code == 200

            paid_resp = await client.get(
                f"/api/v1/invoices/{invoice['id']}",
                headers=headers,
                params={"business_id": business_id},
            )
            assert paid_resp.status_code == 200
            paid_invoice = paid_resp.json()
            assert paid_invoice["payment_status"] == "paid"
            assert paid_invoice["paid_at"]

            daily_close_resp = await client.post(
                "/api/v1/daily-close",
                headers=headers,
                params={"business_id": business_id},
                json={
                    "date": "2026-06-18",
                    "total_cash": 100.0,
                    "total_qr": 150.0,
                    "total_transfer": 0.0,
                    "total_orders": 1,
                    "total_revenue": 250.0,
                },
            )
            assert daily_close_resp.status_code == 200
            daily_close = daily_close_resp.json()
            assert daily_close["total_revenue"] == 250.0

            daily_ops_resp = await client.get("/api/v1/daily-ops", headers=headers, params={"business_id": business_id})
            assert daily_ops_resp.status_code == 200
            assert len(daily_ops_resp.json()) == 1

    asyncio.run(run())


def test_parse_order_endpoint():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client)
            response = await client.post(
                "/api/v1/parse-order",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                json={"text": "nasi lemak x2 RM45"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 45.0
            assert data["items"][0]["quantity"] == 2.0
            assert data["items"][0]["name"].lower() == "nasi lemak"

    asyncio.run(run())


def test_inventory_endpoints_and_reorder():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client)
            headers = _auth_headers(token)
            create_resp = await client.post(
                "/api/v1/inventory/ingredients",
                headers=headers,
                params={"business_id": business_id},
                json={
                    "name": "nasi lemak",
                    "unit": "pcs",
                    "current_stock": 2,
                    "reorder_point": 3,
                    "supplier": "Mak Cik Supplier",
                },
            )
            assert create_resp.status_code == 201
            ingredient = create_resp.json()

            list_resp = await client.get("/api/v1/inventory/ingredients", headers=headers, params={"business_id": business_id})
            assert list_resp.status_code == 200
            assert len(list_resp.json()) == 1

            reorder_resp = await client.get("/api/v1/inventory/reorder", headers=headers, params={"business_id": business_id})
            assert reorder_resp.status_code == 200
            assert len(reorder_resp.json()) == 1
            assert reorder_resp.json()[0]["id"] == ingredient["id"]

            patch_resp = await client.patch(
                f"/api/v1/inventory/ingredients/{ingredient['id']}",
                headers=headers,
                params={"business_id": business_id},
                json={"current_stock": 5},
            )
            assert patch_resp.status_code == 200
            assert patch_resp.json()["current_stock"] == 5.0

    asyncio.run(run())


def test_whatsapp_webhook_creates_invoice(monkeypatch):
    async def run() -> None:
        reset_db()
        import app.api.routes.whatsapp as whatsapp_route

        monkeypatch.setattr(whatsapp_route, "SAHBUKTI_WEBHOOK_SECRET", "test-secret")
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client)
            headers = _auth_headers(token)
            ingredient_resp = await client.post(
                "/api/v1/inventory/ingredients",
                headers=headers,
                params={"business_id": business_id},
                json={
                    "name": "nasi lemak",
                    "unit": "pcs",
                    "current_stock": 5,
                    "reorder_point": 1,
                },
            )
            assert ingredient_resp.status_code == 201
            with get_db() as conn:
                conn.execute(
                    "UPDATE businesses SET owner_whatsapp = ? WHERE id = ?",
                    ("60123456789", business_id),
                )

            response = await client.post(
                "/api/v1/webhook/whatsapp",
                headers={"x-sahbukti-webhook-secret": "test-secret"},
                json={
                    "message": "nasi lemak x2 RM45",
                    "from": "60123456789",
                    "business_id": business_id,
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["invoice_number"].startswith(f"INV-{business_id}-")
            assert data["total"] == 45.0
            assert data["customer_name"] == "60123456789"

            invoices_resp = await client.get("/api/v1/invoices", headers=headers, params={"business_id": business_id})
            assert invoices_resp.status_code == 200
            invoices = invoices_resp.json()
            assert len(invoices) == 1
            assert invoices[0]["items"][0]["name"].lower() == "nasi lemak"

            reorder_resp = await client.get("/api/v1/inventory/reorder", headers=headers, params={"business_id": business_id})
            assert reorder_resp.status_code == 200
            assert reorder_resp.json() == []

    asyncio.run(run())
