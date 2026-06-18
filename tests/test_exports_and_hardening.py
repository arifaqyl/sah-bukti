import asyncio

from httpx import ASGITransport, AsyncClient

from app.db.store import get_db, reset_db
from app.main import create_app
from app.services.customers import create_customer
from app.services.daily_close import create_daily_close
from app.services.invoices import create_invoice, record_invoice_payment
from app.services.inventory import create_ingredient


def _seed_customer_and_invoice() -> tuple[dict, dict]:
    customer = create_customer(
        {
            "business_id": 1,
            "name": "Export Customer",
            "phone": "60111111111",
        }
    )
    invoice = create_invoice(
        {
            "business_id": 1,
            "customer_id": customer["id"],
            "invoice_number": "EXP-INV-001",
            "items": [{"name": "Brownies", "quantity": 2, "unit_price": 25.0}],
            "subtotal": 50.0,
            "tax": 0.0,
            "total": 50.0,
            "payment_method": "pending",
            "payment_status": "pending",
            "due_date": "2026-06-30",
        }
    )
    return customer, invoice


def test_export_endpoints_return_csv_and_json():
    async def run() -> None:
        reset_db()
        _customer, invoice = _seed_customer_and_invoice()
        create_ingredient(
            {
                "business_id": 1,
                "name": "Flour",
                "unit": "kg",
                "current_stock": 2,
                "reorder_point": 5,
                "supplier": "Mill Supplier",
            }
        )
        create_daily_close(
            {
                "business_id": 1,
                "date": "2026-06-18",
                "total_cash": 10.0,
                "total_qr": 20.0,
                "total_transfer": 0.0,
                "total_orders": 1,
                "total_revenue": 30.0,
            }
        )

        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            invoice_csv = await client.get("/api/v1/invoices/export", params={"business_id": 1, "format": "csv"})
            assert invoice_csv.status_code == 200
            assert "text/csv" in invoice_csv.headers["content-type"]
            assert invoice["invoice_number"] in invoice_csv.text

            daily_json = await client.get("/api/v1/daily-ops/export", params={"business_id": 1, "format": "json"})
            assert daily_json.status_code == 200
            assert daily_json.json()[0]["date"] == "2026-06-18"

            inventory_csv = await client.get("/api/v1/inventory/export", params={"business_id": 1, "format": "csv"})
            assert inventory_csv.status_code == 200
            assert "Flour" in inventory_csv.text

    asyncio.run(run())


def test_duplicate_payment_reference_is_idempotent():
    reset_db()
    _customer, invoice = _seed_customer_and_invoice()

    first = record_invoice_payment(
        invoice["id"],
        {"amount": 50.0, "method": "qr", "reference": "REF-DUPE", "confirmed": True},
    )
    second = record_invoice_payment(
        invoice["id"],
        {"amount": 50.0, "method": "qr", "reference": "REF-DUPE", "confirmed": True},
    )

    assert first is not None
    assert second is not None
    assert second["payment_status"] == "paid"

    with get_db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS count FROM payments WHERE invoice_id = ? AND reference = ?",
            (invoice["id"], "REF-DUPE"),
        ).fetchone()["count"]
    assert count == 1


def test_whatsapp_webhook_secret_is_enforced(monkeypatch):
    async def run() -> None:
        reset_db()
        import app.api.routes.whatsapp as whatsapp_route

        monkeypatch.setattr(whatsapp_route, "KEDAIOPS_WEBHOOK_SECRET", "test-secret")
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            denied = await client.post(
                "/api/v1/webhook/whatsapp",
                json={"message": "nasi lemak x2 RM45", "from": "60123456789", "business_id": 1},
            )
            assert denied.status_code == 401

            allowed = await client.post(
                "/api/v1/webhook/whatsapp",
                headers={"x-kede-webhook-secret": "test-secret"},
                json={"message": "nasi lemak x2 RM45", "from": "60123456789", "business_id": 1},
            )
            assert allowed.status_code == 201

    asyncio.run(run())
