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
        token, business_id = await _signup(client, "demo-import@example.com", "Demo Import Biz")
        headers = _auth_headers(token)

        customer = await client.post(
            "/api/v1/customers",
            headers=headers,
            params={"business_id": business_id},
            json={"business_id": business_id, "name": "Aina", "phone": "60124440000"},
        )
        customer.raise_for_status()
        customer_payload = customer.json()

        invoice = await client.post(
            "/api/v1/invoices",
            headers=headers,
            params={"business_id": business_id},
            json={
                "business_id": business_id,
                "customer_id": customer_payload["id"],
                "invoice_number": "INV-IMPORT-001",
                "items": [{"name": "Chocolate Cake", "quantity": 1, "unit_price": 45.0}],
                "subtotal": 45.0,
                "tax": 0.0,
                "total": 45.0,
                "payment_method": "pending",
                "payment_status": "pending",
                "due_date": "2026-06-30",
            },
        )
        invoice.raise_for_status()
        invoice_payload = invoice.json()
        invoice_id = int(invoice_payload["id"])
        print("1. Seed invoice created:", invoice_payload["invoice_number"])

        whatsapp_import = await client.post(
            "/api/v1/evidence/import",
            headers=headers,
            params={"business_id": business_id},
            json={
                "source_type": "whatsapp_export",
                "raw_text": "[6/19/26, 8:15:17 PM] Aina: Paid RM45 for INV-IMPORT-001 via QR",
            },
        )
        whatsapp_import.raise_for_status()
        print("2. WhatsApp export import:", json.dumps(whatsapp_import.json()))

        invoice_before = await client.get(
            f"/api/v1/invoices/{invoice_id}",
            headers=headers,
            params={"business_id": business_id},
        )
        invoice_before.raise_for_status()
        print("3. Invoice still pending after import:", invoice_before.json()["payment_status"])

        proofs = await client.get(
            "/api/v1/payment-proofs",
            headers=headers,
            params={"business_id": business_id},
        )
        proofs.raise_for_status()
        first_proof = proofs.json()[0]

        approve = await client.post(
            f"/api/v1/payment-proofs/{first_proof['id']}/approve",
            headers=headers,
            params={"business_id": business_id},
            json={"invoice_id": invoice_id, "amount": 45.0, "reference": "IMPORT-DEMO-APPROVED-1", "method": "qr"},
        )
        approve.raise_for_status()
        print("4. Approved imported proof:", approve.json()["approved_payment_id"])

        csv_import = await client.post(
            "/api/v1/evidence/import",
            headers=headers,
            params={"business_id": business_id},
            json={
                "source_type": "csv_export",
                "filename": "june-sales.csv",
                "mime_type": "text/csv",
                "raw_text": "\n".join(
                    [
                        "invoice_number,amount,payment_method,paid_at,notes",
                        "INV-IMPORT-002,60,transfer,2026-06-19,Paid via transfer",
                    ]
                ),
            },
        )
        csv_import.raise_for_status()
        print("5. CSV import:", json.dumps(csv_import.json()))

        readiness = await client.get(
            "/api/v1/month-end/readiness",
            headers=headers,
            params={"business_id": business_id, "month": "2026-06", "as_of_date": "2026-06-30"},
        )
        readiness.raise_for_status()
        readiness_payload = readiness.json()
        print(
            "6. Month-end readiness:",
            json.dumps(
                {
                    "status": readiness_payload["readiness_status"],
                    "score": readiness_payload["readiness_score"],
                    "pending_proof_count": readiness_payload["summary"]["pending_proof_count"],
                }
            ),
        )

        accountant_export = await client.get(
            "/api/v1/exports/accountant",
            headers=headers,
            params={"business_id": business_id, "month": "2026-06", "include_proof_payloads": "true"},
        )
        accountant_export.raise_for_status()
        export_payload = accountant_export.json()
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
