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


def _seed_invoice(
    *,
    business_id: int,
    invoice_number: str,
    total: float,
    due_date: str,
    payment_status: str = "pending",
) -> dict:
    customer = create_customer(
        {
            "business_id": business_id,
            "name": f"Customer {invoice_number}",
            "phone": f"6012{invoice_number[-4:]}",
        }
    )
    return create_invoice(
        {
            "business_id": business_id,
            "customer_id": customer["id"],
            "invoice_number": invoice_number,
            "items": [{"name": "Brownie", "quantity": 1, "unit_price": total}],
            "subtotal": total,
            "tax": 0.0,
            "total": total,
            "payment_method": "pending",
            "payment_status": payment_status,
            "due_date": due_date,
        }
    )


def test_reminders_workflow_and_scoping():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_a, business_a = await _signup(client, "rem-a@example.com", "Reminders A")
            token_b, business_b = await _signup(client, "rem-b@example.com", "Reminders B")

            overdue_invoice = _seed_invoice(
                business_id=business_a,
                invoice_number="REM-OVERDUE-1",
                total=60.0,
                due_date="2026-06-10",
            )
            paid_invoice = _seed_invoice(
                business_id=business_a,
                invoice_number="REM-PAID-1",
                total=40.0,
                due_date="2026-06-10",
                payment_status="paid",
            )
            business_b_invoice = _seed_invoice(
                business_id=business_b,
                invoice_number="REM-B-1",
                total=25.0,
                due_date="2026-06-10",
            )

            unauth = await client.get("/api/v1/reminders", params={"business_id": business_a})
            assert unauth.status_code == 401

            cross_lookup = await client.get(
                "/api/v1/reminders",
                headers=_auth_headers(token_a),
                params={"business_id": business_b},
            )
            assert cross_lookup.status_code == 403

            policies = await client.get(
                "/api/v1/reminders/policies",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert policies.status_code == 200
            assert len(policies.json()) >= 1

            generated = await client.post(
                "/api/v1/reminders/generate",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
                json={"as_of_date": "2026-06-19"},
            )
            assert generated.status_code == 200
            data = generated.json()
            assert data["generated_count"] == 1
            assert data["suppressed_count"] == 0
            reminder = data["reminders"][0]
            assert reminder["invoice_id"] == overdue_invoice["id"]
            assert reminder["status"] == "draft"
            assert reminder["invoice_number"] == overdue_invoice["invoice_number"]

            duplicate_generated = await client.post(
                "/api/v1/reminders/generate",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
                json={"as_of_date": "2026-06-19"},
            )
            assert duplicate_generated.status_code == 200
            assert duplicate_generated.json()["generated_count"] == 0
            assert duplicate_generated.json()["suppressed_count"] >= 1

            reminders_resp = await client.get(
                "/api/v1/reminders",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert reminders_resp.status_code == 200
            reminders = reminders_resp.json()
            assert len(reminders) == 1
            assert reminders[0]["invoice_id"] == overdue_invoice["id"]
            assert reminders[0]["invoice_id"] != paid_invoice["id"]

            before_send = get_invoice(overdue_invoice["id"], business_a)
            assert before_send is not None
            assert before_send["payment_status"] == "pending"

            sent = await client.post(
                f"/api/v1/reminders/{reminder['id']}/send",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert sent.status_code == 200
            assert sent.json()["status"] == "sent"

            sent_again = await client.post(
                f"/api/v1/reminders/{reminder['id']}/send",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert sent_again.status_code == 200
            assert sent_again.json()["status"] == "sent"

            detail = await client.get(
                f"/api/v1/reminders/{reminder['id']}",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert detail.status_code == 200
            events = detail.json()["events"]
            assert any(event["event_type"] == "generated" for event in events)
            assert any(event["event_type"] == "sent" for event in events)
            sent_event = next(event for event in events if event["event_type"] == "sent")
            assert sent_event["event_payload"]["provider"] == "mock"

            after_send = get_invoice(overdue_invoice["id"], business_a)
            assert after_send is not None
            assert after_send["payment_status"] == "pending"

            cross_detail = await client.get(
                f"/api/v1/reminders/{reminder['id']}",
                headers=_auth_headers(token_a),
                params={"business_id": business_b},
            )
            assert cross_detail.status_code == 403

            hidden_other = await client.get(
                f"/api/v1/reminders/{reminder['id']}",
                headers=_auth_headers(token_b),
                params={"business_id": business_b},
            )
            assert hidden_other.status_code == 404

            business_b_generated = await client.post(
                "/api/v1/reminders/generate",
                headers=_auth_headers(token_b),
                params={"business_id": business_b},
                json={"as_of_date": "2026-06-19"},
            )
            assert business_b_generated.status_code == 200
            assert business_b_generated.json()["generated_count"] == 1
            assert business_b_generated.json()["reminders"][0]["invoice_id"] == business_b_invoice["id"]

            with get_db() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) AS count FROM reminders WHERE business_id = ?",
                    (business_a,),
                ).fetchone()["count"]
            assert count == 1

    asyncio.run(run())
