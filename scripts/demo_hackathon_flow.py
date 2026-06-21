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


async def _create_customer(client: AsyncClient, headers: dict[str, str], business_id: int) -> dict:
    response = await client.post(
        "/api/v1/customers",
        headers=headers,
        params={"business_id": business_id},
        json={
            "business_id": business_id,
            "name": "Aina Bakery Buyer",
            "phone": "60123456789",
            "email": "aina@example.com",
        },
    )
    response.raise_for_status()
    return response.json()


async def _create_invoice(
    client: AsyncClient,
    headers: dict[str, str],
    business_id: int,
    customer_id: int,
    invoice_number: str,
    total: float,
) -> dict:
    response = await client.post(
        "/api/v1/invoices",
        headers=headers,
        params={"business_id": business_id},
        json={
            "business_id": business_id,
            "customer_id": customer_id,
            "invoice_number": invoice_number,
            "items": [{"name": "Chocolate Cake", "quantity": 1, "unit_price": total}],
            "subtotal": total,
            "tax": 0.0,
            "total": total,
            "payment_method": "pending",
            "payment_status": "pending",
            "due_date": "2026-06-30",
        },
    )
    response.raise_for_status()
    return response.json()


async def _readiness(client: AsyncClient, headers: dict[str, str], business_id: int) -> dict:
    response = await client.get(
        "/api/v1/month-end/readiness",
        headers=headers,
        params={"business_id": business_id, "month": "2026-06", "as_of_date": "2026-06-30"},
    )
    response.raise_for_status()
    return response.json()


async def main() -> None:
    reset_db()
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, business_id = await _signup(client, "demo-hackathon@example.com", "Warung Demo")
        headers = _auth_headers(token)

        print("[1] Shop profile")
        profile = await client.get(
            "/api/v1/business/profile",
            headers=headers,
            params={"business_id": business_id},
        )
        profile.raise_for_status()
        print("loaded:", json.dumps(profile.json()))

        updated_profile = await client.patch(
            "/api/v1/business/profile",
            headers=headers,
            params={"business_id": business_id},
            json={
                "name": "Warung Seri Pagi",
                "tagline": "reviewable evidence for Malaysian micro-sellers",
                "theme_color": "#D4A853",
                "owner_whatsapp": "60123456789",
                "industry": "bakery",
            },
        )
        updated_profile.raise_for_status()
        print("updated:", json.dumps(updated_profile.json()))

        print("\n[2] Invoice + customer")
        customer = await _create_customer(client, headers, business_id)
        invoice_primary = await _create_invoice(client, headers, business_id, customer["id"], "INV-HACK-001", 45.0)
        invoice_secondary = await _create_invoice(client, headers, business_id, customer["id"], "INV-HACK-002", 60.0)
        print("customer:", json.dumps({"id": customer["id"], "name": customer["name"], "phone": customer["phone"]}))
        print(
            "invoices:",
            json.dumps(
                [
                    {"id": invoice_primary["id"], "invoice_number": invoice_primary["invoice_number"], "status": invoice_primary["payment_status"]},
                    {"id": invoice_secondary["id"], "invoice_number": invoice_secondary["invoice_number"], "status": invoice_secondary["payment_status"]},
                ]
            ),
        )

        print("\n[3] WhatsApp evidence")
        evidence_response = await client.post(
            "/api/v1/evidence/whatsapp",
            headers=headers,
            params={"business_id": business_id},
            json={
                "business_id": business_id,
                "from_phone": customer["phone"],
                "message": None,
                "transcript": "Hey, I just paid RM45 for INV-HACK-001 via QR",
                "media_type": "voice_note",
                "media_metadata": {"filename": "voice-note.ogg", "mime_type": "audio/ogg"},
            },
        )
        evidence_response.raise_for_status()
        evidence = evidence_response.json()
        print(
            "payment proof created:",
            json.dumps(
                {
                    "intent": evidence["intent"],
                    "proof_id": evidence["payment_proof"]["id"],
                    "review_state": evidence["payment_proof"]["review_state"],
                    "invoice_id": evidence["payment_proof"]["invoice_id"],
                }
            ),
        )

        invoice_pending = await client.get(
            f"/api/v1/invoices/{invoice_primary['id']}",
            headers=headers,
            params={"business_id": business_id},
        )
        invoice_pending.raise_for_status()
        print("invoice before approval:", json.dumps({"invoice_number": invoice_primary["invoice_number"], "status": invoice_pending.json()["payment_status"]}))

        print("\n[4] Approval gate")
        approved = await client.post(
            f"/api/v1/payment-proofs/{evidence['payment_proof']['id']}/approve",
            headers=headers,
            params={"business_id": business_id},
            json={
                "invoice_id": invoice_primary["id"],
                "amount": 45.0,
                "reference": "HACK-DEMO-APPROVED-001",
                "method": "qr",
                "decision_reason": "hackathon_demo_approval",
            },
        )
        approved.raise_for_status()
        print(
            "proof approved:",
            json.dumps(
                {
                    "proof_id": approved.json()["id"],
                    "review_state": approved.json()["review_state"],
                    "approved_payment_id": approved.json()["approved_payment_id"],
                }
            ),
        )

        invoice_paid = await client.get(
            f"/api/v1/invoices/{invoice_primary['id']}",
            headers=headers,
            params={"business_id": business_id},
        )
        invoice_paid.raise_for_status()
        readiness_after_approval = await _readiness(client, headers, business_id)
        print(
            "invoice after approval:",
            json.dumps({"invoice_number": invoice_primary["invoice_number"], "status": invoice_paid.json()["payment_status"]}),
        )
        print(
            "readiness after approval:",
            json.dumps(
                {
                    "status": readiness_after_approval["readiness_status"],
                    "score": readiness_after_approval["readiness_score"],
                    "pending_proof_count": readiness_after_approval["summary"]["pending_proof_count"],
                }
            ),
        )

        print("\n[5] Ingredient notes + supplier summary")
        for payload in [
            {
                "name": "Flour",
                "unit": "kg",
                "current_stock": 2,
                "reorder_point": 5,
                "supplier": "Sime Darby",
                "notes": "Call Sime Darby every Friday",
            },
            {
                "name": "Sugar",
                "unit": "kg",
                "current_stock": 8,
                "reorder_point": 5,
                "supplier": "Sime Darby",
                "notes": "Bulk order before weekend promo",
            },
            {
                "name": "Eggs",
                "unit": "pcs",
                "current_stock": 20,
                "reorder_point": 30,
                "supplier": "Farm Fresh",
                "notes": "Morning delivery only",
            },
        ]:
            ingredient_response = await client.post(
                "/api/v1/inventory/ingredients",
                headers=headers,
                params={"business_id": business_id},
                json=payload,
            )
            ingredient_response.raise_for_status()

        supplier_summary = await client.get(
            "/api/v1/inventory/suppliers",
            headers=headers,
            params={"business_id": business_id},
        )
        supplier_summary.raise_for_status()
        print("supplier summary:", json.dumps(supplier_summary.json()))

        print("\n[6] Evidence import")
        whatsapp_import = await client.post(
            "/api/v1/evidence/import",
            headers=headers,
            params={"business_id": business_id},
            json={
                "source_type": "whatsapp_export",
                "raw_text": "[6/19/26, 8:15:17 PM] Aina: Paid RM60 for INV-HACK-002 via transfer",
            },
        )
        whatsapp_import.raise_for_status()
        print("whatsapp export import:", json.dumps(whatsapp_import.json()))

        csv_import = await client.post(
            "/api/v1/evidence/import",
            headers=headers,
            params={"business_id": business_id},
            json={
                "source_type": "csv_export",
                "filename": "june-evidence.csv",
                "mime_type": "text/csv",
                "raw_text": "\n".join(
                    [
                        "invoice_number,amount,payment_method,paid_at,notes",
                        "INV-UNKNOWN-003,35,transfer,2026-06-19,Paid via transfer",
                    ]
                ),
            },
        )
        csv_import.raise_for_status()
        print("csv import:", json.dumps(csv_import.json()))

        print("\n[7] Month-end readiness")
        readiness_after_import = await _readiness(client, headers, business_id)
        print(
            "readiness after imports:",
            json.dumps(
                {
                    "status": readiness_after_import["readiness_status"],
                    "score": readiness_after_import["readiness_score"],
                    "pending_proof_count": readiness_after_import["summary"]["pending_proof_count"],
                    "blockers": [blocker["type"] for blocker in readiness_after_import["blockers"]],
                }
            ),
        )

        print("\n[8] Accountant export")
        accountant_export = await client.get(
            "/api/v1/exports/accountant",
            headers=headers,
            params={"business_id": business_id, "month": "2026-06"},
        )
        accountant_export.raise_for_status()
        export_payload = accountant_export.json()
        print(
            "export summary:",
            json.dumps(
                {
                    "invoice_count": export_payload["summary"]["invoice_count"],
                    "paid_total": export_payload["summary"]["paid_total"],
                    "proof_needs_review_count": export_payload["summary"]["proof_needs_review_count"],
                    "risk_flags": [flag["type"] for flag in export_payload["risk_flags"]],
                }
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
