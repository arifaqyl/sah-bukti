import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.store import get_db, reset_db
from app.main import create_app
from app.services.auth import list_memberships
from app.services.customers import create_customer
from app.services.daily_close import create_daily_close
from app.services.inventory import create_ingredient
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


def _seed_invoice(business_id: int, invoice_number: str = "PROOF-INV-001", total: float = 30.0) -> dict:
    customer = create_customer(
        {
            "business_id": business_id,
            "name": "Proof Customer",
            "phone": "60120000000",
        }
    )
    return create_invoice(
        {
            "business_id": business_id,
            "customer_id": customer["id"],
            "invoice_number": invoice_number,
            "items": [{"name": "Cake", "quantity": 1, "unit_price": total}],
            "subtotal": total,
            "tax": 0.0,
            "total": total,
            "payment_method": "pending",
            "payment_status": "pending",
            "due_date": "2026-06-30",
        }
    )


def _proof_bytes(amount: float, reference: str, confidence: float = 0.99, paid_at: str = "2026-06-19T10:00:00+08:00") -> bytes:
    return json.dumps(
        {
            "amount": amount,
            "reference": reference,
            "confidence": confidence,
            "paid_at": paid_at,
        }
    ).encode("utf-8")


def test_phase3_create_helpers_require_business_id():
    reset_db()
    with pytest.raises(ValueError, match="business_id is required"):
        create_customer({"name": "No Biz"})
    with pytest.raises(ValueError, match="business_id is required"):
        create_ingredient({"name": "Flour"})
    with pytest.raises(ValueError, match="business_id is required"):
        create_daily_close({"date": "2026-06-19"})
    customer = create_customer({"business_id": 1, "name": "Has Biz"})
    with pytest.raises(ValueError, match="business_id is required"):
        create_invoice(
            {
                "customer_id": customer["id"],
                "invoice_number": "NO-BIZ-INV",
                "items": [],
                "subtotal": 10.0,
                "tax": 0.0,
                "total": 10.0,
            }
        )


def test_payment_proof_upload_requires_review_for_strong_match():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client, "proof-owner@example.com", "Proof Biz")
            invoice = _seed_invoice(business_id)
            response = await client.post(
                "/api/v1/payment-proofs/upload",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                files={"file": ("proof.png", _proof_bytes(30.0, "PROOF-REF-1"), "image/png")},
                data={"invoice_id": str(invoice["id"]), "source_channel": "dashboard"},
            )
            assert response.status_code == 201
            proof = response.json()
            assert proof["review_state"] == "needs_review"
            assert proof["decision_reason"] == "strong_invoice_match_requires_owner_review"
            assert proof["approved_payment_id"] is None
            assert proof["invoice_id"] == invoice["id"]
            assert proof["ocr_status"] == "completed"

        updated_invoice = get_invoice(invoice["id"], business_id)
        assert updated_invoice is not None
        assert updated_invoice["payment_status"] == "pending"

    asyncio.run(run())


def test_payment_proof_ocr_failure_stays_reviewable():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client, "proof-fail@example.com", "Proof Fail Biz")
            invoice = _seed_invoice(business_id, invoice_number="PROOF-INV-FAIL", total=45.0)
            response = await client.post(
                "/api/v1/payment-proofs/upload",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                files={"file": ("proof.png", json.dumps({"fail": True, "error": "blurred"}).encode("utf-8"), "image/png")},
                data={"invoice_id": str(invoice["id"])},
            )
            assert response.status_code == 201
            proof = response.json()
            assert proof["review_state"] == "needs_review"
            assert proof["ocr_status"] == "failed"
            assert proof["approved_payment_id"] is None

    asyncio.run(run())


def test_payment_proof_duplicate_file_hash_conflicts():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client, "proof-dup@example.com", "Proof Dup Biz")
            invoice = _seed_invoice(business_id, invoice_number="PROOF-INV-DUP", total=30.0)
            file_bytes = _proof_bytes(30.0, "DUP-HASH-1")

            first = await client.post(
                "/api/v1/payment-proofs/upload",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                files={"file": ("proof.png", file_bytes, "image/png")},
                data={"invoice_id": str(invoice["id"])},
            )
            assert first.status_code == 201

            second = await client.post(
                "/api/v1/payment-proofs/upload",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                files={"file": ("proof.png", file_bytes, "image/png")},
                data={"invoice_id": str(invoice["id"])},
            )
            assert second.status_code == 409
            assert second.json()["detail"] == "duplicate_file_hash"

    asyncio.run(run())


def test_payment_proof_duplicate_reference_requires_review():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client, "proof-ref@example.com", "Proof Ref Biz")
            invoice_a = _seed_invoice(business_id, invoice_number="PROOF-REF-A", total=30.0)
            invoice_b = _seed_invoice(business_id, invoice_number="PROOF-REF-B", total=30.0)

            first = await client.post(
                "/api/v1/payment-proofs/upload",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                files={"file": ("proof-a.png", _proof_bytes(30.0, "SAME-REF-1"), "image/png")},
                data={"invoice_id": str(invoice_a["id"])},
            )
            assert first.status_code == 201
            assert first.json()["review_state"] == "needs_review"

            second = await client.post(
                "/api/v1/payment-proofs/upload",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                files={
                    "file": (
                        "proof-b.png",
                        _proof_bytes(30.0, "SAME-REF-1", confidence=0.95, paid_at="2026-06-19T10:05:00+08:00"),
                        "image/png",
                    )
                },
                data={"invoice_id": str(invoice_b["id"])},
            )
            assert second.status_code == 201
            proof = second.json()
            assert proof["review_state"] == "needs_review"
            assert proof["decision_reason"] == "duplicate_reference_detected"
            assert proof["approved_payment_id"] is None

    asyncio.run(run())


def test_payment_proof_manual_approve_and_reject_are_idempotent():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client, "proof-manual@example.com", "Proof Manual Biz")
            invoice = _seed_invoice(business_id, invoice_number="PROOF-MANUAL", total=30.0)

            upload = await client.post(
                "/api/v1/payment-proofs/upload",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                files={"file": ("proof.png", _proof_bytes(15.0, "MANUAL-REF-1", confidence=0.4), "image/png")},
                data={"invoice_id": str(invoice["id"])},
            )
            assert upload.status_code == 201
            proof = upload.json()
            assert proof["review_state"] == "needs_review"

            approve = await client.post(
                f"/api/v1/payment-proofs/{proof['id']}/approve",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                json={"invoice_id": invoice["id"], "amount": 30.0, "reference": "MANUAL-APPROVE-1", "method": "transfer"},
            )
            assert approve.status_code == 200
            approved = approve.json()
            assert approved["review_state"] == "auto_approved"
            approved_payment_id = approved["approved_payment_id"]
            assert approved_payment_id is not None

            approve_again = await client.post(
                f"/api/v1/payment-proofs/{proof['id']}/approve",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                json={"invoice_id": invoice["id"], "amount": 30.0, "reference": "MANUAL-APPROVE-1", "method": "transfer"},
            )
            assert approve_again.status_code == 200
            assert approve_again.json()["approved_payment_id"] == approved_payment_id

            with get_db() as conn:
                payment_count = conn.execute(
                    "SELECT COUNT(*) AS count FROM payments WHERE invoice_id = ? AND reference = ?",
                    (invoice["id"], "MANUAL-APPROVE-1"),
                ).fetchone()["count"]
            assert payment_count == 1

            reject_upload = await client.post(
                "/api/v1/payment-proofs/upload",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                files={"file": ("proof-reject.png", _proof_bytes(9.0, "REJECT-REF-1", confidence=0.2), "image/png")},
                data={"source_channel": "dashboard"},
            )
            assert reject_upload.status_code == 201
            reject_proof = reject_upload.json()

            reject = await client.post(
                f"/api/v1/payment-proofs/{reject_proof['id']}/reject",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                json={"decision_reason": "not_a_valid_receipt"},
            )
            assert reject.status_code == 200
            assert reject.json()["review_state"] == "rejected"

            reject_again = await client.post(
                f"/api/v1/payment-proofs/{reject_proof['id']}/reject",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                json={"decision_reason": "not_a_valid_receipt"},
            )
            assert reject_again.status_code == 200
            assert reject_again.json()["review_state"] == "rejected"

    asyncio.run(run())


def test_payment_proof_cross_tenant_rejection():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_a, business_a = await _signup(client, "proof-a@example.com", "Proof A")
            token_b, business_b = await _signup(client, "proof-b@example.com", "Proof B")
            invoice_b = _seed_invoice(business_b, invoice_number="PROOF-BIZ-B", total=30.0)

            denied_upload = await client.post(
                "/api/v1/payment-proofs/upload",
                headers=_auth_headers(token_a),
                params={"business_id": business_b},
                files={"file": ("proof.png", _proof_bytes(30.0, "CROSS-REF-1"), "image/png")},
                data={"invoice_id": str(invoice_b["id"])},
            )
            assert denied_upload.status_code == 403

            own_upload = await client.post(
                "/api/v1/payment-proofs/upload",
                headers=_auth_headers(token_b),
                params={"business_id": business_b},
                files={"file": ("proof.png", _proof_bytes(30.0, "CROSS-REF-2"), "image/png")},
                data={"invoice_id": str(invoice_b["id"])},
            )
            assert own_upload.status_code == 201
            proof = own_upload.json()

            hidden_detail = await client.get(
                f"/api/v1/payment-proofs/{proof['id']}",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
            )
            assert hidden_detail.status_code == 404

    asyncio.run(run())
