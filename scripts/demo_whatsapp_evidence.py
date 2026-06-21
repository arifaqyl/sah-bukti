from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.store import reset_db
from app.main import create_app
from app.services.auth import list_memberships


def _auth_headers(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


async def _signup(client: AsyncClient, email: str, business_name: str) -> tuple[str, int]:
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "password123", "business_name": business_name},
    )
    response.raise_for_status()
    payload = response.json()
    memberships = list_memberships(payload["user"]["id"])
    return payload["access_token"], memberships[0]["business_id"]


async def main() -> None:
    reset_db()
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, business_id = await _signup(client, "demo-evidence@example.com", "Demo Evidence Biz")
        headers = _auth_headers(token)

        customer_response = await client.post(
            "/api/v1/customers",
            headers=headers,
            params={"business_id": business_id},
            json={"business_id": business_id, "name": "Aina", "phone": "60123456789"},
        )
        customer_response.raise_for_status()
        customer = customer_response.json()

        invoice_response = await client.post(
            "/api/v1/invoices",
            headers=headers,
            params={"business_id": business_id},
            json={
                "business_id": business_id,
                "customer_id": customer["id"],
                "invoice_number": "INV-DEMO-001",
                "items": [{"name": "Chocolate Cake", "quantity": 1, "unit_price": 45.0}],
                "subtotal": 45.0,
                "tax": 0.0,
                "total": 45.0,
                "payment_method": "pending",
                "payment_status": "pending",
                "due_date": "2026-06-30",
            },
        )
        invoice_response.raise_for_status()
        invoice = invoice_response.json()
        print(f"1. Seed invoice created: {invoice['invoice_number']} status={invoice['payment_status']}")

        evidence_response = await client.post(
            "/api/v1/evidence/whatsapp",
            headers=headers,
            params={"business_id": business_id},
            json={
                "business_id": business_id,
                "from_phone": "60123456789",
                "message": None,
                "transcript": "Hey, I just paid RM45 for INV-DEMO-001 via QR",
                "media_type": "voice_note",
                "media_metadata": {"filename": "voice-note.ogg", "mime_type": "audio/ogg"},
            },
        )
        evidence_response.raise_for_status()
        evidence = evidence_response.json()
        proof = evidence["payment_proof"]
        print(f"2. Voice note created proof: proof_id={proof['id']} state={proof['review_state']}")

        invoice_check = await client.get(
            f"/api/v1/invoices/{invoice['id']}",
            headers=headers,
            params={"business_id": business_id},
        )
        invoice_check.raise_for_status()
        print(f"3. Invoice still unchanged before approval: status={invoice_check.json()['payment_status']}")

        approve_response = await client.post(
            f"/api/v1/payment-proofs/{proof['id']}/approve",
            headers=headers,
            params={"business_id": business_id},
            json={
                "invoice_id": invoice["id"],
                "amount": 45.0,
                "reference": "VOICE-DEMO-APPROVED-1",
                "method": "qr",
                "decision_reason": "demo_voice_note_approved",
            },
        )
        approve_response.raise_for_status()
        approved = approve_response.json()
        print(f"4. Proof approved: state={approved['review_state']} payment_id={approved['approved_payment_id']}")

        invoice_after = await client.get(
            f"/api/v1/invoices/{invoice['id']}",
            headers=headers,
            params={"business_id": business_id},
        )
        invoice_after.raise_for_status()
        print(f"5. Invoice after approval: status={invoice_after.json()['payment_status']}")

        readiness_response = await client.get(
            "/api/v1/month-end/readiness",
            headers=headers,
            params={"business_id": business_id, "month": "2026-06", "as_of_date": "2026-06-30"},
        )
        readiness_response.raise_for_status()
        readiness = readiness_response.json()
        print(
            "6. Month-end readiness:",
            json.dumps(
                {
                    "status": readiness["readiness_status"],
                    "score": readiness["readiness_score"],
                    "pending_proof_count": readiness["summary"]["pending_proof_count"],
                }
            ),
        )

        export_response = await client.get(
            "/api/v1/exports/accountant",
            headers=headers,
            params={"business_id": business_id, "month": "2026-06"},
        )
        export_response.raise_for_status()
        export_payload = export_response.json()
        print(
            "7. Accountant export summary:",
            json.dumps(
                {
                    "invoice_count": export_payload["summary"]["invoice_count"],
                    "paid_total": export_payload["summary"]["paid_total"],
                    "proof_needs_review_count": export_payload["summary"]["proof_needs_review_count"],
                }
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
