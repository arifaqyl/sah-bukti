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


def _seed_invoice(business_id: int, invoice_number: str, total: float) -> dict:
    customer = create_customer(
        {
            "business_id": business_id,
            "name": "Import Customer",
            "phone": "60123334444",
        }
    )
    return create_invoice(
        {
            "business_id": business_id,
            "customer_id": customer["id"],
            "invoice_number": invoice_number,
            "items": [{"name": "Import Box", "quantity": 1, "unit_price": total}],
            "subtotal": total,
            "tax": 0.0,
            "total": total,
            "payment_method": "pending",
            "payment_status": "pending",
            "due_date": "2026-06-30",
        }
    )


def test_evidence_import_auth_scope_and_whatsapp_lines():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_a, business_a = await _signup(client, "import-a@example.com", "Import A")
            token_b, business_b = await _signup(client, "import-b@example.com", "Import B")
            invoice = _seed_invoice(business_a, "INV-IMPORT-001", 45.0)

            raw_text = "\n".join(
                [
                    "[6/19/26, 8:15:17 PM] Aina: Paid RM45 for INV-IMPORT-001 via QR",
                    "[6/19/26, 8:16:00 PM] Siti: I want 2 chocolate cakes total RM90",
                    "[6/19/26, 8:17:00 PM] Lim: can check my order later",
                ]
            )

            unauth = await client.post(
                "/api/v1/evidence/import",
                params={"business_id": business_a},
                json={"source_type": "whatsapp_export", "raw_text": raw_text},
            )
            assert unauth.status_code == 401

            cross = await client.post(
                "/api/v1/evidence/import",
                headers=_auth_headers(token_b),
                params={"business_id": business_a},
                json={"source_type": "whatsapp_export", "raw_text": raw_text},
            )
            assert cross.status_code == 403

            response = await client.post(
                "/api/v1/evidence/import",
                headers=_auth_headers(token_a),
                params={"business_id": business_a},
                json={"business_id": business_a, "source_type": "whatsapp_export", "raw_text": raw_text},
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload == {
                "business_id": business_a,
                "source_type": "whatsapp_export",
                "imported_count": 3,
                "payment_proofs_created": 2,
                "invoices_created": 1,
                "needs_review_count": 2,
                "failed_count": 0,
                "failures": [],
            }

            unchanged = get_invoice(invoice["id"], business_a)
            assert unchanged is not None
            assert unchanged["payment_status"] == "pending"
            with get_db() as conn:
                payment_count = conn.execute(
                    "SELECT COUNT(*) AS count FROM payments WHERE invoice_id = ?",
                    (invoice["id"],),
                ).fetchone()["count"]
                proof_count = conn.execute(
                    "SELECT COUNT(*) AS count FROM payment_proofs WHERE business_id = ?",
                    (business_a,),
                ).fetchone()["count"]
                invoice_count = conn.execute(
                    "SELECT COUNT(*) AS count FROM invoices WHERE business_id = ?",
                    (business_a,),
                ).fetchone()["count"]
            assert payment_count == 0
            assert proof_count == 2
            assert invoice_count == 2

    asyncio.run(run())


def test_evidence_import_csv_drive_approval_readiness_and_export():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client, "import-csv@example.com", "Import CSV")
            invoice = _seed_invoice(business_id, "INV-IMPORT-002", 60.0)

            csv_content = "\n".join(
                [
                    "invoice_number,amount,payment_method,paid_at,notes",
                    "INV-IMPORT-002,60,transfer,2026-06-19,Paid via transfer",
                    ",,,,''",
                    "INV-NEW-ORDER,,cash,,Brownie box x2 RM30",
                ]
            )

            csv_response = await client.post(
                "/api/v1/evidence/import",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                json={
                    "source_type": "csv_export",
                    "raw_text": csv_content,
                    "filename": "june-sales.csv",
                    "mime_type": "text/csv",
                },
            )
            assert csv_response.status_code == 200
            csv_payload = csv_response.json()
            assert csv_payload["payment_proofs_created"] == 2
            assert csv_payload["invoices_created"] == 1
            assert csv_payload["needs_review_count"] == 2
            assert csv_payload["failed_count"] == 0

            drive_response = await client.post(
                "/api/v1/evidence/import",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                json={
                    "source_type": "google_drive_file",
                    "drive_url": "https://drive.google.com/file/d/abc123",
                    "filename": "receipt.jpg",
                    "mime_type": "image/jpeg",
                    "media_metadata": {"source": "google_drive", "file_id": "abc123"},
                },
            )
            assert drive_response.status_code == 200
            drive_payload = drive_response.json()
            assert drive_payload["payment_proofs_created"] == 1
            assert drive_payload["needs_review_count"] == 1

            with get_db() as conn:
                proof_row = conn.execute(
                    """
                    SELECT id
                    FROM payment_proofs
                    WHERE business_id = ? AND extracted_reference = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (business_id, "INV-IMPORT-002"),
                ).fetchone()
                payment_count = conn.execute(
                    "SELECT COUNT(*) AS count FROM payments WHERE invoice_id = ?",
                    (invoice["id"],),
                ).fetchone()["count"]
            assert proof_row is not None
            assert payment_count == 0

            approve = await client.post(
                f"/api/v1/payment-proofs/{proof_row['id']}/approve",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                json={"invoice_id": invoice["id"], "amount": 60.0, "reference": "IMPORT-APPROVED-1", "method": "transfer"},
            )
            assert approve.status_code == 200
            updated_invoice = get_invoice(invoice["id"], business_id)
            assert updated_invoice is not None
            assert updated_invoice["payment_status"] == "paid"

            readiness = await client.get(
                "/api/v1/month-end/readiness",
                headers=_auth_headers(token),
                params={"business_id": business_id, "month": "2026-06", "as_of_date": "2026-06-30"},
            )
            assert readiness.status_code == 200
            readiness_payload = readiness.json()
            assert readiness_payload["summary"]["pending_proof_count"] >= 1
            assert readiness_payload["summary"]["paid_total"] == 60.0

            export_response = await client.get(
                "/api/v1/exports/accountant",
                headers=_auth_headers(token),
                params={"business_id": business_id, "month": "2026-06", "include_proof_payloads": "true"},
            )
            assert export_response.status_code == 200
            export_payload = export_response.json()
            assert export_payload["summary"]["paid_total"] == 60.0
            assert any(proof["extracted_reference"] == "INV-IMPORT-002" for proof in export_payload["payment_proofs"])
            assert any(item["invoice_number"] == "INV-IMPORT-002" for item in export_payload["invoices"])

    asyncio.run(run())
