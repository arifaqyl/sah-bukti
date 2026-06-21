import asyncio
import json

from httpx import ASGITransport, AsyncClient

from app.db.store import get_db, reset_db, utc_now
from app.main import create_app
from app.services.auth import list_memberships
from app.services.customers import create_customer
from app.services.invoices import create_invoice, get_invoice
import app.services.reminders as reminders_service


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
    total: float,
    due_date: str,
    customer_phone: str = "60123330000",
) -> dict:
    customer = create_customer(
        {
            "business_id": business_id,
            "name": f"Customer {invoice_number}",
            "phone": customer_phone,
        }
    )
    return create_invoice(
        {
            "business_id": business_id,
            "customer_id": customer["id"],
            "invoice_number": invoice_number,
            "items": [{"name": "Kuih", "quantity": 1, "unit_price": total}],
            "subtotal": total,
            "tax": 0.0,
            "total": total,
            "payment_method": "pending",
            "payment_status": "pending",
            "due_date": due_date,
        }
    )


def _proof_bytes(amount: float, reference: str, confidence: float = 0.2) -> bytes:
    return json.dumps(
        {
            "amount": amount,
            "reference": reference,
            "confidence": confidence,
            "paid_at": "2026-06-19T10:00:00+08:00",
        }
    ).encode("utf-8")


def test_review_and_audit_queues_are_scoped_and_non_mutating(monkeypatch):
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_a, business_a = await _signup(client, "queue-a@example.com", "Queue A")
            token_b, business_b = await _signup(client, "queue-b@example.com", "Queue B")

            proof_invoice = _seed_invoice(
                business_id=business_a,
                invoice_number="QUEUE-PROOF-1",
                total=30.0,
                due_date="2026-06-30",
            )
            reminder_invoice_sent = _seed_invoice(
                business_id=business_a,
                invoice_number="QUEUE-REM-SENT",
                total=40.0,
                due_date="2026-06-10",
                customer_phone="60124440000",
            )
            reminder_invoice_failed = _seed_invoice(
                business_id=business_a,
                invoice_number="QUEUE-REM-FAIL",
                total=50.0,
                due_date="2026-06-11",
                customer_phone="60125550000",
            )
            other_business_invoice = _seed_invoice(
                business_id=business_b,
                invoice_number="QUEUE-B-1",
                total=20.0,
                due_date="2026-06-10",
            )

            proof_upload = await client.post(
                "/api/v1/payment-proofs/upload",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
                files={"file": ("proof.png", _proof_bytes(30.0, "QUEUE-PROOF-REF"), "image/png")},
                data={"invoice_id": str(proof_invoice["id"]), "source_channel": "dashboard"},
            )
            assert proof_upload.status_code == 201
            proof = proof_upload.json()
            assert proof["review_state"] == "needs_review"

            unauth = await client.get("/api/v1/review/payment-proofs", params={"business_id": business_a})
            assert unauth.status_code == 401

            cross = await client.get(
                "/api/v1/review/payment-proofs",
                headers=_auth_headers(token_a),
                params={"business_id": business_b},
            )
            assert cross.status_code == 403

            review_proofs = await client.get(
                "/api/v1/review/payment-proofs",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert review_proofs.status_code == 200
            proof_rows = review_proofs.json()
            assert len(proof_rows) == 1
            assert proof_rows[0]["id"] == proof["id"]
            assert proof_rows[0]["review_state"] == "needs_review"

            generated = await client.post(
                "/api/v1/reminders/generate",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
                json={"as_of_date": "2026-06-19"},
            )
            assert generated.status_code == 200
            reminders = {item["invoice_id"]: item for item in generated.json()["reminders"]}
            sent_reminder = reminders[reminder_invoice_sent["id"]]
            failed_reminder = reminders[reminder_invoice_failed["id"]]

            sent = await client.post(
                f"/api/v1/reminders/{sent_reminder['id']}/send",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert sent.status_code == 200
            assert sent.json()["status"] == "sent"

            monkeypatch.setattr(reminders_service, "REMINDER_PROVIDER", "whatsapp")
            with get_db() as conn:
                conn.execute(
                    "UPDATE customers SET phone = NULL WHERE id = ?",
                    (reminder_invoice_failed["customer_id"],),
                )
            failed = await client.post(
                f"/api/v1/reminders/{failed_reminder['id']}/send",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert failed.status_code == 200
            assert failed.json()["status"] == "failed"

            review_reminders = await client.get(
                "/api/v1/review/reminders",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert review_reminders.status_code == 200
            reminder_statuses = {row["invoice_number"]: row["status"] for row in review_reminders.json()}
            assert reminder_statuses["QUEUE-REM-SENT"] == "sent"
            assert reminder_statuses["QUEUE-REM-FAIL"] == "failed"

            sent_only = await client.get(
                "/api/v1/review/reminders",
                headers=_auth_headers(token_a),
                params={"business_id": business_a, "status": "sent"},
            )
            assert sent_only.status_code == 200
            assert [row["invoice_number"] for row in sent_only.json()] == ["QUEUE-REM-SENT"]

            failed_only = await client.get(
                "/api/v1/review/reminders",
                headers=_auth_headers(token_a),
                params={"business_id": business_a, "status": "failed"},
            )
            assert failed_only.status_code == 200
            assert [row["invoice_number"] for row in failed_only.json()] == ["QUEUE-REM-FAIL"]

            proof_audit = await client.get(
                f"/api/v1/audit/payment-proofs/{proof['id']}",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert proof_audit.status_code == 200
            assert any(event["event_type"] == "uploaded" for event in proof_audit.json()["events"])

            reminder_audit = await client.get(
                f"/api/v1/audit/reminders/{sent_reminder['id']}",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert reminder_audit.status_code == 200
            assert any(event["event_type"] == "sent" for event in reminder_audit.json()["events"])

            with get_db() as conn:
                now = utc_now()
                conn.execute(
                    """
                    INSERT INTO provider_callback_events (
                        business_id, provider, event_key, invoice_number, transaction_reference,
                        raw_payload, payload_hash, signature_valid, processing_status,
                        proof_id, received_at, processed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        business_a,
                        "external_callback",
                        "queue-invalid-signature",
                        proof_invoice["invoice_number"],
                        "QUEUE-TXN-1",
                        "{}",
                        "hash-QUEUE-TXN-1",
                        0,
                        "invalid_signature",
                        None,
                        now,
                        now,
                    ),
                )

            callback_queue = await client.get(
                "/api/v1/audit/callbacks",
                headers=_auth_headers(token_a),
                params={"business_id": business_a, "status": "invalid_signature"},
            )
            assert callback_queue.status_code == 200
            callback_rows = callback_queue.json()
            assert len(callback_rows) == 1
            assert callback_rows[0]["invoice_number"] == proof_invoice["invoice_number"]
            assert callback_rows[0]["processing_status"] == "invalid_signature"

            hidden_callbacks = await client.get(
                "/api/v1/audit/callbacks",
                headers=_auth_headers(token_a),
                params={"business_id": business_b},
            )
            assert hidden_callbacks.status_code == 403

            hidden_proof = await client.get(
                f"/api/v1/audit/payment-proofs/{proof['id']}",
                headers=_auth_headers(token_b),
                params={"business_id": business_b},
            )
            assert hidden_proof.status_code == 404

        proof_invoice_after = get_invoice(proof_invoice["id"], business_a)
        sent_invoice_after = get_invoice(reminder_invoice_sent["id"], business_a)
        failed_invoice_after = get_invoice(reminder_invoice_failed["id"], business_a)
        other_invoice_after = get_invoice(other_business_invoice["id"], business_b)
        assert proof_invoice_after is not None
        assert proof_invoice_after["payment_status"] == "pending"
        assert sent_invoice_after is not None
        assert sent_invoice_after["payment_status"] == "pending"
        assert failed_invoice_after is not None
        assert failed_invoice_after["payment_status"] == "pending"
        assert other_invoice_after is not None
        assert other_invoice_after["payment_status"] == "pending"

    asyncio.run(run())
