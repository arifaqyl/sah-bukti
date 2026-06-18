import asyncio
import json

from httpx import ASGITransport, AsyncClient

from app.db.store import reset_db
from app.main import create_app
from app.services.aging import AgingService
from app.services.customers import create_customer
from app.services.invoices import create_invoice
from app.services.provision import ProvisionEngine


def _seed_bucket_invoices() -> None:
    customer = create_customer({"name": "Provision Customer", "phone": "60110000000"})
    invoices = [
        ("INV-CUR", 100.0, "2026-06-25"),
        ("INV-3160", 200.0, "2026-05-10"),
        ("INV-6190", 300.0, "2026-04-20"),
        ("INV-91180", 400.0, "2026-02-15"),
        ("INV-180", 500.0, "2025-12-01"),
    ]
    for invoice_number, total, due_date in invoices:
        create_invoice(
            {
                "customer_id": customer["id"],
                "invoice_number": invoice_number,
                "items": [{"name": invoice_number, "quantity": 1, "unit_price": total}],
                "subtotal": total,
                "tax": 0.0,
                "total": total,
                "payment_method": "transfer",
                "payment_status": "pending",
                "due_date": due_date,
            }
        )


def test_calculate_provision_with_default_policy():
    reset_db()
    _seed_bucket_invoices()
    engine = ProvisionEngine()
    result = engine.calculate(1, "2026-06")
    assert result["total_outstanding"] == 1500.0
    assert result["provision_amount"] == 620.0


def test_calculate_provision_with_custom_policy():
    reset_db()
    _seed_bucket_invoices()
    engine = ProvisionEngine()
    result = engine.calculate(1, "2026-06", {"31-60": 0.1, "180+": 0.5})
    assert result["policy_used"]["31-60"] == 0.1
    assert result["policy_used"]["180+"] == 0.5
    assert result["provision_amount"] == 380.0


def test_generate_journal_entry_balanced():
    reset_db()
    engine = ProvisionEngine()
    entry = engine.generate_journal_entry(1650.0, "2026-06")
    assert entry["balanced"] is True
    assert entry["total_debit"] == entry["total_credit"] == 1650.0


def test_generate_journal_entry_amounts():
    reset_db()
    engine = ProvisionEngine()
    entry = engine.generate_journal_entry(500.0, "2026-06")
    assert entry["entries"][0]["debit"] == 500.0
    assert entry["entries"][1]["credit"] == 500.0


def test_export_csv_format():
    reset_db()
    _seed_bucket_invoices()
    engine = ProvisionEngine()
    result = engine.calculate(1, "2026-06")
    csv_text = engine.export_csv(1, result)
    assert "AGING SUMMARY" in csv_text
    assert "JOURNAL ENTRY" in csv_text
    assert "TOTAL,5,1500.00,,620.00" in csv_text


def test_aging_buckets():
    reset_db()
    _seed_bucket_invoices()
    service = AgingService(ProvisionEngine().db)
    invoices = service.get_invoices_for_month(1, "2026-06")
    buckets = service.bucket_invoices(invoices)
    counts = {bucket["bucket"]: bucket["count"] for bucket in buckets}
    assert counts["current"] == 1
    assert counts["31-60"] == 1
    assert counts["61-90"] == 1
    assert counts["91-180"] == 1
    assert counts["180+"] == 1


def test_zero_provision_when_no_overdue():
    reset_db()
    customer = create_customer({"name": "Current Customer", "phone": "60112223333"})
    create_invoice(
        {
            "customer_id": customer["id"],
            "invoice_number": "INV-ZERO",
            "items": [{"name": "Current", "quantity": 1, "unit_price": 250.0}],
            "subtotal": 250.0,
            "tax": 0.0,
            "total": 250.0,
            "payment_method": "cash",
            "payment_status": "pending",
            "due_date": "2026-06-29",
        }
    )
    result = ProvisionEngine().calculate(1, "2026-06")
    assert result["provision_amount"] == 0.0


def test_full_provision_when_180_plus():
    reset_db()
    customer = create_customer({"name": "Old Debt", "phone": "60114445555"})
    create_invoice(
        {
            "customer_id": customer["id"],
            "invoice_number": "INV-OLD",
            "items": [{"name": "Old", "quantity": 1, "unit_price": 500.0}],
            "subtotal": 500.0,
            "tax": 0.0,
            "total": 500.0,
            "payment_method": "transfer",
            "payment_status": "pending",
            "due_date": "2025-01-01",
        }
    )
    result = ProvisionEngine().calculate(1, "2026-06")
    assert result["provision_amount"] == 500.0


def test_provision_api_happy_path():
    async def run() -> None:
        reset_db()
        _seed_bucket_invoices()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            aging_resp = await client.get("/api/v1/provision/aging", params={"business_id": 1, "month": "2026-06"})
            assert aging_resp.status_code == 200
            aging_data = aging_resp.json()
            assert len(aging_data["buckets"]) == 5
            assert aging_data["total_provision"] == 620.0

            calc_resp = await client.get("/api/v1/provision/calculate", params={"business_id": 1, "month": "2026-06"})
            assert calc_resp.status_code == 200
            calc_data = calc_resp.json()
            assert calc_data["journal_entry"]["balanced"] is True
            assert calc_data["provision_amount"] == 620.0

            export_resp = await client.get("/api/v1/provision/export", params={"business_id": 1, "month": "2026-06", "format": "csv"})
            assert export_resp.status_code == 200
            assert "text/csv" in export_resp.headers["content-type"]
            assert "Provision for Doubtful Debts - June 2026" in export_resp.text

    asyncio.run(run())


def test_provision_api_empty_and_policy_override():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            empty_resp = await client.get("/api/v1/provision/aging", params={"business_id": 1, "month": "2026-06"})
            assert empty_resp.status_code == 404
            assert empty_resp.json()["error"]["code"] == "no_data"

            policy_resp = await client.post(
                "/api/v1/provision/policy",
                json={"business_id": 1, "policy": {"31-60": 0.25, "180+": 0.8}},
            )
            assert policy_resp.status_code == 200
            assert policy_resp.json()["policy"]["31-60"] == 0.25

            _seed_bucket_invoices()
            calc_resp = await client.get(
                "/api/v1/provision/calculate",
                params={"business_id": 1, "month": "2026-06", "policy": json.dumps({"31-60": 0.25})},
            )
            assert calc_resp.status_code == 200
            assert calc_resp.json()["policy_used"]["31-60"] == 0.25

    asyncio.run(run())
