import asyncio

from httpx import ASGITransport, AsyncClient

from app.db.store import get_db, reset_db, utc_now
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
    due_date: str,
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
    message_text: str,
    generated_for_date: str,
    sent_at: str | None = None,
    last_error: str | None = None,
) -> int:
    with get_db() as conn:
        cursor = conn.execute(
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
                message_text,
                f"{invoice_id}:{policy_id}:{generated_for_date}:{status}",
                generated_for_date,
                f"{generated_for_date}T10:00:00+08:00",
                sent_at,
                last_error,
            ),
        )
        reminder_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO reminder_events (reminder_id, actor_user_id, event_type, event_payload, created_at)
            VALUES (?, NULL, ?, ?, ?)
            """,
            (
                reminder_id,
                "sent" if status == "sent" else "send_failed",
                '{"provider":"mock"}' if status == "sent" else '{"provider":"whatsapp","detail":"missing_phone"}',
                f"{generated_for_date}T11:00:00+08:00",
            ),
        )
    return reminder_id


def _insert_callback_event(
    *,
    invoice_number: str,
    processing_status: str,
    transaction_id: str,
    processed_invoice_id: int | None = None,
) -> None:
    now = "2026-06-19T12:00:00+08:00"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO provider_callback_events (
                provider, event_key, invoice_number, transaction_id, payload_json, payload_hash,
                signature_valid, processing_status, processed_invoice_id, created_at, processed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                processed_invoice_id,
                now,
                now,
            ),
        )


def test_accountant_export_is_tenant_scoped_and_read_only():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_a, business_a = await _signup(client, "acct-a@example.com", "Accountant A")
            token_b, business_b = await _signup(client, "acct-b@example.com", "Accountant B")

            june_pending = _seed_invoice(
                business_id=business_a,
                invoice_number="ACC-JUNE-PENDING",
                customer_name="June Pending",
                customer_phone="60120000001",
                total=100.0,
                due_date="2026-06-10",
            )
            june_paid = _seed_invoice(
                business_id=business_a,
                invoice_number="ACC-JUNE-PAID",
                customer_name="June Paid",
                customer_phone="60120000002",
                total=60.0,
                due_date="2026-06-15",
            )
            may_pending = _seed_invoice(
                business_id=business_a,
                invoice_number="ACC-MAY-PENDING",
                customer_name="May Pending",
                customer_phone="60120000003",
                total=40.0,
                due_date="2026-06-30",
            )
            other_business = _seed_invoice(
                business_id=business_b,
                invoice_number="ACC-OTHER-BIZ",
                customer_name="Other Biz",
                customer_phone="60120000004",
                total=90.0,
                due_date="2026-06-12",
            )

            _set_invoice_created_at(june_pending["invoice"]["id"], "2026-06-05T09:00:00+08:00")
            _set_invoice_created_at(june_paid["invoice"]["id"], "2026-06-08T09:00:00+08:00")
            _set_invoice_created_at(may_pending["invoice"]["id"], "2026-05-28T09:00:00+08:00")
            _set_invoice_created_at(other_business["invoice"]["id"], "2026-06-07T09:00:00+08:00")

            record_invoice_payment(
                june_paid["invoice"]["id"],
                {"amount": 60.0, "method": "transfer", "reference": "ACC-PAY-1", "confirmed": True},
                business_a,
            )
            _set_payment_created_at("ACC-PAY-1", "2026-06-09T10:00:00+08:00")
            _set_invoice_created_at(
                june_paid["invoice"]["id"],
                "2026-06-08T09:00:00+08:00",
                "2026-06-09T10:00:00+08:00",
            )

            proof = create_text_payment_proof(
                business_id=business_a,
                uploaded_by_user_id=None,
                text="Paid RM90 for ACC-JUNE-PENDING via QR",
                source_channel="whatsapp",
                invoice_id=june_pending["invoice"]["id"],
                extracted_amount=90.0,
                extracted_reference="ACC-JUNE-PENDING",
                extracted_method="qr",
            )

            policy = ensure_default_reminder_policy(business_a)
            _insert_reminder(
                business_id=business_a,
                invoice_id=june_pending["invoice"]["id"],
                customer_id=june_pending["customer"]["id"],
                policy_id=policy["id"],
                status="sent",
                message_text="sent reminder",
                generated_for_date="2026-06-18",
                sent_at="2026-06-18T12:00:00+08:00",
            )
            _insert_reminder(
                business_id=business_a,
                invoice_id=may_pending["invoice"]["id"],
                customer_id=may_pending["customer"]["id"],
                policy_id=policy["id"],
                status="failed",
                message_text="failed reminder",
                generated_for_date="2026-06-19",
                last_error="missing_phone",
            )

            create_daily_close(
                {
                    "business_id": business_a,
                    "date": "2026-06-18",
                    "total_cash": 10.0,
                    "total_qr": 20.0,
                    "total_transfer": 60.0,
                    "total_orders": 2,
                    "total_revenue": 90.0,
                }
            )

            _insert_callback_event(
                invoice_number=june_pending["invoice"]["invoice_number"],
                processing_status="invalid_signature",
                transaction_id="CALLBACK-1",
            )
            _insert_callback_event(
                invoice_number=june_pending["invoice"]["invoice_number"],
                processing_status="duplicate_event",
                transaction_id="CALLBACK-2",
            )
            _insert_callback_event(
                invoice_number=other_business["invoice"]["invoice_number"],
                processing_status="invalid_signature",
                transaction_id="CALLBACK-OTHER",
            )

            unauth = await client.get("/api/v1/exports/accountant", params={"business_id": business_a})
            assert unauth.status_code == 401

            cross = await client.get(
                "/api/v1/exports/accountant",
                headers=_auth_headers(token_a),
                params={"business_id": business_b},
            )
            assert cross.status_code == 403

            before_invoice = get_invoice(june_pending["invoice"]["id"], business_a)
            before_proof = get_payment_proof(proof["id"], business_a)

            response = await client.get(
                "/api/v1/exports/accountant",
                headers=_auth_headers(token_a),
                params={"business_id": business_a, "month": "2026-06", "as_of_date": "2026-06-19"},
            )
            assert response.status_code == 200
            payload = response.json()

            invoice_numbers = [row["invoice_number"] for row in payload["invoices"]]
            assert "ACC-JUNE-PENDING" in invoice_numbers
            assert "ACC-JUNE-PAID" in invoice_numbers
            assert "ACC-MAY-PENDING" not in invoice_numbers
            assert "ACC-OTHER-BIZ" not in invoice_numbers

            assert [row["reference"] for row in payload["payments"]] == ["ACC-PAY-1"]
            assert payload["payment_proofs"][0]["invoice_number"] == "ACC-JUNE-PENDING"
            assert payload["payment_proofs"][0]["ocr_payload"] is None
            assert {row["status"] for row in payload["reminders"]} == {"sent", "failed"}
            assert [row["date"] for row in payload["daily_closes"]] == ["2026-06-18"]
            assert {row["processing_status"] for row in payload["provider_callbacks"]} == {"invalid_signature", "duplicate_event"}

            summary = payload["summary"]
            assert summary == {
                "invoice_total": 160.0,
                "paid_total": 60.0,
                "pending_total": 100.0,
                "overdue_total": 100.0,
                "invoice_count": 2,
                "paid_count": 1,
                "pending_count": 1,
                "overdue_count": 1,
                "proof_needs_review_count": 1,
                "reminder_failed_count": 1,
                "callback_issue_count": 2,
            }

            flag_types = {flag["type"] for flag in payload["risk_flags"]}
            assert "pending_payment_proofs" in flag_types
            assert "failed_reminders" in flag_types
            assert "unpaid_overdue_invoices" in flag_types
            assert "invalid_callback_signatures" in flag_types
            assert "duplicate_callback_events" in flag_types
            assert "missing_daily_closes" in flag_types
            assert "proof_payment_amount_mismatches" in flag_types

            assert payload["provision"]["month"] == "2026-06"

            with_payloads = await client.get(
                "/api/v1/exports/accountant",
                headers=_auth_headers(token_a),
                params={
                    "business_id": business_a,
                    "month": "2026-06",
                    "as_of_date": "2026-06-19",
                    "include_proof_payloads": "true",
                },
            )
            assert with_payloads.status_code == 200
            proof_payload = with_payloads.json()["payment_proofs"][0]["ocr_payload"]
            assert proof_payload is not None
            assert proof_payload["raw_text"] == "Paid RM90 for ACC-JUNE-PENDING via QR"

            as_of_response = await client.get(
                "/api/v1/exports/accountant",
                headers=_auth_headers(token_a),
                params={"business_id": business_a, "month": "2026-06", "as_of_date": "2026-06-09"},
            )
            assert as_of_response.status_code == 200
            as_of_summary = as_of_response.json()["summary"]
            assert as_of_summary["overdue_total"] == 0.0
            assert as_of_summary["pending_total"] == 100.0

            after_invoice = get_invoice(june_pending["invoice"]["id"], business_a)
            after_proof = get_payment_proof(proof["id"], business_a)
            assert before_invoice == after_invoice
            assert before_proof == after_proof

    asyncio.run(run())
