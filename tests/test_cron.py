import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.store import get_db, reset_db
from app.main import create_app
from app.services.auth import list_memberships
from app.services.cron import run_daily_close, run_monthly_provision
from app.services.customers import create_customer
from app.services.inventory import create_ingredient
from app.services.invoices import create_invoice


def _signup_owner(client: AsyncClient) -> str:
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "owner@example.com", "password": "password123", "business_name": "Owner Bakery"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


async def _signup_owner_async(client: AsyncClient) -> tuple[str, int]:
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": "owner@example.com", "password": "password123", "business_name": "Owner Bakery"},
    )
    assert response.status_code == 201
    payload = response.json()
    memberships = list_memberships(payload["user"]["id"])
    return payload["access_token"], memberships[0]["business_id"]


def _auth_headers(token: str) -> dict:
    return {"authorization": f"Bearer {token}"}


def _seed_paid_invoice(
    business_id: int,
    invoice_number: str,
    total: float,
    payment_method: str,
    created_at: str,
    paid_at: str | None = None,
    payment_status: str = "paid",
    due_date: str = "2026-06-18",
) -> dict:
    customer = create_customer(
        {
            "business_id": business_id,
            "name": f"Customer {invoice_number}",
            "phone": f"60{invoice_number[-6:]:0>6}",
        }
    )
    invoice = create_invoice(
        {
            "business_id": business_id,
            "customer_id": customer["id"],
            "invoice_number": invoice_number,
            "items": [{"name": invoice_number, "quantity": 1, "unit_price": total}],
            "subtotal": total,
            "tax": 0.0,
            "total": total,
            "payment_method": payment_method,
            "payment_status": payment_status,
            "due_date": due_date,
        }
    )
    with get_db() as conn:
        conn.execute(
            """
            UPDATE invoices
            SET created_at = ?, paid_at = ?, updated_at = ?, payment_status = ?, payment_method = ?
            WHERE id = ?
            """,
            (
                created_at,
                paid_at,
                paid_at or created_at,
                payment_status,
                payment_method,
                invoice["id"],
            ),
        )
    return invoice


def test_run_daily_close_creates_summary_and_reorder_alerts():
    reset_db()
    _seed_paid_invoice(1, "INV-CASH-1", 20.0, "cash", "2026-06-18T01:00:00+00:00", "2026-06-18T01:30:00+00:00")
    _seed_paid_invoice(1, "INV-QR-1", 30.0, "duitnow qr", "2026-06-18T02:00:00+00:00", "2026-06-18T02:15:00+00:00")
    _seed_paid_invoice(1, "INV-TRF-1", 50.0, "bank transfer", "2026-06-18T03:00:00+00:00", "2026-06-18T03:20:00+00:00")
    _seed_paid_invoice(1, "INV-PEND-1", 99.0, "pending", "2026-06-18T04:00:00+00:00", None, payment_status="pending")
    create_ingredient(
        {
            "business_id": 1,
            "name": "Eggs",
            "unit": "tray",
            "current_stock": 1,
            "reorder_point": 2,
            "supplier": "Kampung Farm",
        }
    )

    result = run_daily_close(business_id=1, close_date="2026-06-18")

    assert result["status"] == "ok"
    assert result["daily_close"]["total_cash"] == 20.0
    assert result["daily_close"]["total_qr"] == 30.0
    assert result["daily_close"]["total_transfer"] == 50.0
    assert result["daily_close"]["total_orders"] == 3
    assert result["daily_close"]["total_revenue"] == 100.0
    assert len(result["reorder_alerts"]) == 1
    assert result["reorder_alerts"][0]["name"] == "Eggs"


def test_cron_services_require_explicit_business_id():
    reset_db()

    with pytest.raises(ValueError, match="business_id is required"):
        run_daily_close()

    with pytest.raises(ValueError, match="business_id is required"):
        run_monthly_provision()


def test_run_daily_close_updates_existing_row_instead_of_inserting_duplicate():
    reset_db()
    _seed_paid_invoice(1, "INV-DUP-1", 40.0, "cash", "2026-06-18T05:00:00+00:00", "2026-06-18T05:05:00+00:00")

    first_run = run_daily_close(business_id=1, close_date="2026-06-18")

    _seed_paid_invoice(1, "INV-DUP-2", 60.0, "qr", "2026-06-18T06:00:00+00:00", "2026-06-18T06:10:00+00:00")
    second_run = run_daily_close(business_id=1, close_date="2026-06-18")

    with get_db() as conn:
        count_row = conn.execute(
            "SELECT COUNT(*) AS count FROM daily_ops WHERE business_id = ? AND date = ?",
            (1, "2026-06-18"),
        ).fetchone()

    assert first_run["daily_close"]["id"] == second_run["daily_close"]["id"]
    assert second_run["daily_close"]["total_orders"] == 2
    assert second_run["daily_close"]["total_revenue"] == 100.0
    assert second_run["daily_close"]["total_cash"] == 40.0
    assert second_run["daily_close"]["total_qr"] == 60.0
    assert count_row["count"] == 1


def test_run_monthly_provision_persists_snapshot():
    reset_db()
    customer = create_customer({"business_id": 1, "name": "Provision Customer", "phone": "60110000000"})
    create_invoice(
        {
            "business_id": customer["business_id"],
            "customer_id": customer["id"],
            "invoice_number": "INV-MONTHLY-1",
            "items": [{"name": "Older debt", "quantity": 1, "unit_price": 200.0}],
            "subtotal": 200.0,
            "tax": 0.0,
            "total": 200.0,
            "payment_method": "transfer",
            "payment_status": "pending",
            "due_date": "2026-05-10",
        }
    )

    result = run_monthly_provision(business_id=1, month="2026-06")

    assert result["status"] == "ok"
    assert result["snapshot"] is not None
    assert result["snapshot"]["month"] == "2026-06"
    assert result["snapshot"]["provision_amount"] == 10.0
    assert result["result"]["provision_amount"] == 10.0


def test_admin_daily_close_endpoint_runs_manual_trigger():
    async def run() -> None:
        reset_db()
        _seed_paid_invoice(1, "INV-ENDPOINT-1", 88.0, "cash", "2026-06-18T07:00:00+00:00", "2026-06-18T07:05:00+00:00")
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup_owner_async(client)
            headers = _auth_headers(token)
            response = await client.post(
                "/api/v1/admin/cron/daily-close",
                headers=headers,
                params={"business_id": business_id, "date": "2026-06-18"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["daily_close"]["total_cash"] == 0.0
        assert data["daily_close"]["total_orders"] == 0

    asyncio.run(run())


def test_admin_monthly_provision_endpoint_validates_month():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup_owner_async(client)
            response = await client.post(
                "/api/v1/admin/cron/monthly-provision",
                headers=_auth_headers(token),
                params={"business_id": business_id, "month": "2026/06"},
            )
        assert response.status_code == 422
        assert response.json()["detail"] == "Invalid month format. Expected YYYY-MM"

    asyncio.run(run())
