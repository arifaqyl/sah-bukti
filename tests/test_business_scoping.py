import asyncio

from httpx import ASGITransport, AsyncClient

from app.db.store import reset_db
from app.main import create_app
from app.services.auth import list_memberships
from app.services.customers import create_customer
from app.services.daily_close import create_daily_close
from app.services.inventory import create_ingredient
from app.services.invoices import create_invoice


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


def test_phase2_business_scoping_routes(monkeypatch):
    async def run() -> None:
        reset_db()
        import app.api.routes.whatsapp as whatsapp_route

        monkeypatch.setattr(whatsapp_route, "SAHBUKTI_WEBHOOK_SECRET", "test-secret")
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_a, business_a = await _signup(client, "owner-a@example.com", "Biz A")
            token_b, business_b = await _signup(client, "owner-b@example.com", "Biz B")

            customer_a = create_customer({"business_id": business_a, "name": "A Customer", "phone": "60110000001"})
            invoice_a = create_invoice(
                {
                    "business_id": business_a,
                    "customer_id": customer_a["id"],
                    "invoice_number": "A-INV-001",
                    "items": [{"name": "Brownie", "quantity": 1, "unit_price": 12.0}],
                    "subtotal": 12.0,
                    "tax": 0.0,
                    "total": 12.0,
                    "payment_method": "pending",
                    "payment_status": "pending",
                }
            )
            customer_b = create_customer({"business_id": business_b, "name": "B Customer", "phone": "60110000002"})
            invoice_b = create_invoice(
                {
                    "business_id": business_b,
                    "customer_id": customer_b["id"],
                    "invoice_number": "B-INV-001",
                    "items": [{"name": "Cookie", "quantity": 1, "unit_price": 15.0}],
                    "subtotal": 15.0,
                    "tax": 0.0,
                    "total": 15.0,
                    "payment_method": "pending",
                    "payment_status": "pending",
                    "due_date": "2026-06-01",
                }
            )
            create_ingredient(
                {
                    "business_id": business_a,
                    "name": "Flour A",
                    "unit": "kg",
                    "current_stock": 1,
                    "reorder_point": 2,
                }
            )
            create_ingredient(
                {
                    "business_id": business_b,
                    "name": "Flour B",
                    "unit": "kg",
                    "current_stock": 1,
                    "reorder_point": 2,
                }
            )
            create_daily_close(
                {
                    "business_id": business_a,
                    "date": "2026-06-18",
                    "total_cash": 10.0,
                    "total_qr": 0.0,
                    "total_transfer": 0.0,
                    "total_orders": 1,
                    "total_revenue": 10.0,
                }
            )

            unauth_customers = await client.get("/api/v1/customers", params={"business_id": business_a})
            assert unauth_customers.status_code == 401

            missing_context = await client.get(
                "/api/v1/customers",
                headers=_auth_headers(token_a),
            )
            assert missing_context.status_code == 400

            own_customers = await client.get(
                "/api/v1/customers",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert own_customers.status_code == 200
            assert len(own_customers.json()) == 1

            cross_customers = await client.get(
                "/api/v1/customers",
                headers=_auth_headers(token_a),
                params={"business_id": business_b},
            )
            assert cross_customers.status_code == 403

            own_invoice = await client.get(
                f"/api/v1/invoices/{invoice_a['id']}",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert own_invoice.status_code == 200

            cross_invoice = await client.get(
                f"/api/v1/invoices/{invoice_b['id']}",
                headers=_auth_headers(token_a),
                params={"business_id": business_b},
            )
            assert cross_invoice.status_code == 403

            wrong_invoice_in_own_ctx = await client.get(
                f"/api/v1/invoices/{invoice_b['id']}",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert wrong_invoice_in_own_ctx.status_code == 404

            payment_link_cross = await client.post(
                f"/api/v1/payments/invoices/{invoice_b['id']}/payment-link",
                headers=_auth_headers(token_a),
                params={"business_id": business_b},
            )
            assert payment_link_cross.status_code == 403

            export_cross = await client.get(
                "/api/v1/invoices/export",
                headers=_auth_headers(token_a),
                params={"business_id": business_b, "format": "csv"},
            )
            assert export_cross.status_code == 403

            inventory_own = await client.get(
                "/api/v1/inventory/ingredients",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert inventory_own.status_code == 200
            assert len(inventory_own.json()) == 1

            inventory_cross = await client.get(
                "/api/v1/inventory/ingredients",
                headers=_auth_headers(token_a),
                params={"business_id": business_b},
            )
            assert inventory_cross.status_code == 403

            daily_ops_own = await client.get(
                "/api/v1/daily-ops",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert daily_ops_own.status_code == 200
            assert len(daily_ops_own.json()) == 1

            provision_cross = await client.get(
                "/api/v1/provision/calculate",
                headers=_auth_headers(token_a),
                params={"business_id": business_b, "month": "2026-06"},
            )
            assert provision_cross.status_code == 403

            invalid_webhook = await client.post(
                "/api/v1/webhook/whatsapp",
                headers={"x-sahbukti-webhook-secret": "test-secret"},
                json={"message": "nasi lemak x2 RM45", "from": "60123456789", "business_id": 99999},
            )
            assert invalid_webhook.status_code == 403

    asyncio.run(run())
