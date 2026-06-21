import asyncio

from httpx import ASGITransport, AsyncClient

from app.db.store import get_db, reset_db
from app.main import create_app
from app.services.auth import list_memberships
from app.services.customers import create_customer
from app.services.daily_close import create_daily_close
from app.services.invoices import create_invoice, get_invoice, record_invoice_payment
from app.services.payment_proofs import create_text_payment_proof, get_payment_proof
from app.services.reminders import ensure_default_reminder_policy


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


def _seed_invoice(
    *,
    business_id: int,
    invoice_number: str,
    customer_name: str,
    customer_phone: str | None,
    total: float,
    due_date: str | None,
) -> dict:
    customer = create_customer(
        {
            "business_id": business_id,
            "name": customer_name,
            "phone": customer_phone,
        }
    )
    invoice = create_invoice(
        {
            "business_id": business_id,
            "customer_id": customer["id"],
            "invoice_number": invoice_number,
            "items": [{"name": "Bake Box", "quantity": 1, "unit_price": total}],
            "subtotal": total,
            "tax": 0.0,
            "total": total,
            "payment_method": "pending",
            "payment_status": "pending",
            "due_date": due_date,
        }
    )
    return {"customer": customer, "invoice": invoice}


def _set_invoice_created_at(invoice_id: int, created_at: str, paid_at: str | None = None) -> None:
    with get_db() as conn:
        conn.execute(
            """
            UPDATE invoices
            SET created_at = ?, updated_at = ?, paid_at = COALESCE(?, paid_at)
            WHERE id = ?
            """,
            (created_at, paid_at or created_at, paid_at, invoice_id),
        )


def _set_payment_created_at(reference: str, created_at: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE payments SET created_at = ? WHERE reference = ?",
            (created_at, reference),
        )


def _insert_reminder(
    *,
    business_id: int,
    invoice_id: int,
    customer_id: int,
    policy_id: int,
    status: str,
    generated_for_date: str,
    last_error: str | None = None,
) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO reminders (
                business_id, invoice_id, customer_id, policy_id, channel, status,
                days_overdue, outstanding_amount, message_text, dedupe_key, generated_for_date, generated_at, sent_at, last_error
            )
            VALUES (?, ?, ?, ?, 'mock', ?, 5, 100.0, ?, ?, ?, ?, ?, ?)
            """,
            (
                business_id,
                invoice_id,
                customer_id,
                policy_id,
                status,
                f"{status} reminder",
                f"{invoice_id}:{policy_id}:{generated_for_date}:{status}",
                generated_for_date,
                f"{generated_for_date}T10:00:00+08:00",
                f"{generated_for_date}T12:00:00+08:00" if status == "sent" else None,
                last_error,
            ),
        )


def _insert_callback_event(
    *,
    invoice_number: str,
    processing_status: str,
    transaction_id: str,
) -> None:
    now = "2026-06-19T12:00:00+08:00"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO provider_callback_events (
                provider, event_key, invoice_number, transaction_id, payload_json, payload_hash,
                signature_valid, processing_status, processed_invoice_id, created_at, processed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                "external_callback",
                f"event-{transaction_id}",
                invoice_number,
                transaction_id,
                "{}",
                f"hash-{transaction_id}",
                0 if processing_status == "invalid_signature" else 1,
                processing_status,
                now,
                now,
            ),
        )


def _seed_full_daily_closes_for_june(business_id: int) -> None:
    for day in range(1, 31):
        create_daily_close(
            {
                "business_id": business_id,
                "date": f"2026-06-{day:02d}",
                "total_cash": 0.0,
                "total_qr": 0.0,
                "total_transfer": 0.0,
                "total_orders": 0,
                "total_revenue": 0.0,
            }
        )


def test_month_end_readiness_auth_and_scope():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_a, business_a = await _signup(client, "me-a@example.com", "Month End A")
            _token_b, business_b = await _signup(client, "me-b@example.com", "Month End B")

            unauth = await client.get("/api/v1/month-end/readiness", params={"business_id": business_a, "month": "2026-06"})
            assert unauth.status_code == 401

            cross = await client.get(
                "/api/v1/month-end/readiness",
                headers=_auth_headers(token_a),
                params={"business_id": business_b, "month": "2026-06"},
            )
            assert cross.status_code == 403

    asyncio.run(run())


def test_month_end_readiness_clean_month_is_ready():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client, "me-clean@example.com", "Month End Clean")
            clean = _seed_invoice(
                business_id=business_id,
                invoice_number="ME-CLEAN-1",
                customer_name="Clean Customer",
                customer_phone="60128880001",
                total=80.0,
                due_date="2026-06-15",
            )
            _set_invoice_created_at(clean["invoice"]["id"], "2026-06-02T09:00:00+08:00")
            record_invoice_payment(
                clean["invoice"]["id"],
                {"amount": 80.0, "method": "transfer", "reference": "ME-CLEAN-PAY", "confirmed": True},
                business_id,
            )
            _set_payment_created_at("ME-CLEAN-PAY", "2026-06-03T10:00:00+08:00")
            _set_invoice_created_at(clean["invoice"]["id"], "2026-06-02T09:00:00+08:00", "2026-06-03T10:00:00+08:00")
            _seed_full_daily_closes_for_june(business_id)

            response = await client.get(
                "/api/v1/month-end/readiness",
                headers=_auth_headers(token),
                params={"business_id": business_id, "month": "2026-06", "as_of_date": "2026-06-30"},
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["readiness_status"] == "ready"
            assert payload["readiness_score"] == 100
            assert payload["blockers"] == []
            assert payload["summary"]["provision_amount"] == 0.0
            assert payload["accountant_export"]["endpoint"] == "/api/v1/exports/accountant"
            assert payload["accountant_export"]["params"] == {"month": "2026-06", "include_proof_payloads": False}

    asyncio.run(run())


def test_month_end_readiness_blocked_month_includes_blockers_actions_and_no_mutation():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client, "me-block@example.com", "Month End Blocked")

            overdue = _seed_invoice(
                business_id=business_id,
                invoice_number="ME-OVERDUE-1",
                customer_name="Overdue Customer",
                customer_phone=None,
                total=100.0,
                due_date="2025-12-10",
            )
            paid = _seed_invoice(
                business_id=business_id,
                invoice_number="ME-PAID-1",
                customer_name="Paid Customer",
                customer_phone="60128880002",
                total=50.0,
                due_date="2026-06-12",
            )
            _set_invoice_created_at(overdue["invoice"]["id"], "2026-06-05T09:00:00+08:00")
            _set_invoice_created_at(paid["invoice"]["id"], "2026-06-08T09:00:00+08:00")

            record_invoice_payment(
                paid["invoice"]["id"],
                {"amount": 50.0, "method": "transfer", "reference": "ME-BLOCK-PAY", "confirmed": True},
                business_id,
            )
            _set_payment_created_at("ME-BLOCK-PAY", "2026-06-09T10:00:00+08:00")
            _set_invoice_created_at(paid["invoice"]["id"], "2026-06-08T09:00:00+08:00", "2026-06-09T10:00:00+08:00")

            proof = create_text_payment_proof(
                business_id=business_id,
                uploaded_by_user_id=None,
                text="Paid RM90 for ME-OVERDUE-1 via QR",
                source_channel="whatsapp",
                invoice_id=overdue["invoice"]["id"],
                extracted_amount=90.0,
                extracted_reference="ME-OVERDUE-1",
                extracted_method="qr",
            )
            policy = ensure_default_reminder_policy(business_id)
            _insert_reminder(
                business_id=business_id,
                invoice_id=overdue["invoice"]["id"],
                customer_id=overdue["customer"]["id"],
                policy_id=policy["id"],
                status="failed",
                generated_for_date="2026-06-19",
                last_error="missing_phone",
            )
            create_daily_close(
                {
                    "business_id": business_id,
                    "date": "2026-06-18",
                    "total_cash": 0.0,
                    "total_qr": 0.0,
                    "total_transfer": 50.0,
                    "total_orders": 1,
                    "total_revenue": 50.0,
                }
            )
            _insert_callback_event(
                invoice_number=overdue["invoice"]["invoice_number"],
                processing_status="invalid_signature",
                transaction_id="ME-CALLBACK-1",
            )

            before_invoice = get_invoice(overdue["invoice"]["id"], business_id)
            before_proof = get_payment_proof(proof["id"], business_id)

            response = await client.get(
                "/api/v1/month-end/readiness",
                headers=_auth_headers(token),
                params={"business_id": business_id, "month": "2026-06", "as_of_date": "2026-06-19"},
            )
            assert response.status_code == 200
            payload = response.json()

            assert payload["readiness_status"] == "blocked"
            assert payload["readiness_score"] < 100
            assert payload["summary"]["pending_proof_count"] == 1
            assert payload["summary"]["failed_reminder_count"] == 1
            assert payload["summary"]["overdue_total"] == 100.0
            assert payload["summary"]["callback_issue_count"] == 1
            assert payload["summary"]["missing_daily_close_count"] > 0
            assert payload["provision"]["provision_amount"] > 0

            blocker_types = {blocker["type"] for blocker in payload["blockers"]}
            assert "pending_payment_proofs" in blocker_types
            assert "failed_reminders" in blocker_types
            assert "unpaid_overdue_invoices" in blocker_types
            assert "invalid_callback_signatures" in blocker_types
            assert "missing_daily_closes" in blocker_types
            assert "proof_payment_amount_mismatches" in blocker_types

            action_endpoints = {action["endpoint"] for action in payload["action_plan"]}
            assert "/api/v1/review/payment-proofs" in action_endpoints
            assert "/api/v1/review/reminders" in action_endpoints
            assert "/api/v1/audit/callbacks" in action_endpoints
            assert "/api/v1/daily-close" in action_endpoints

            data_quality = payload["data_quality"]
            assert data_quality["missing_customer_phone_count"] == 1
            assert data_quality["pending_payment_method_count"] >= 1
            assert data_quality["proof_without_invoice_count"] == 0
            assert data_quality["callback_issue_count"] == 1

            after_invoice = get_invoice(overdue["invoice"]["id"], business_id)
            after_proof = get_payment_proof(proof["id"], business_id)
            assert before_invoice == after_invoice
            assert before_proof == after_proof

    asyncio.run(run())
