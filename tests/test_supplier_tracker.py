import asyncio

from httpx import ASGITransport, AsyncClient

from app.db.store import reset_db
from app.main import create_app
from app.services.auth import list_memberships


def _auth_headers(token: str) -> dict:
    return {"authorization": f"Bearer {token}"}


async def _signup(client: AsyncClient, email: str = "supplier-owner@example.com") -> tuple[str, int]:
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "password123", "business_name": "Supplier Biz"},
    )
    assert response.status_code == 201
    payload = response.json()
    memberships = list_memberships(payload["user"]["id"])
    return payload["access_token"], memberships[0]["business_id"]


def test_ingredient_notes_create_and_update():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client)
            headers = _auth_headers(token)

            created = await client.post(
                "/api/v1/inventory/ingredients",
                headers=headers,
                params={"business_id": business_id},
                json={
                    "name": "Flour",
                    "unit": "kg",
                    "current_stock": 2,
                    "reorder_point": 5,
                    "supplier": "Sime Darby",
                    "notes": "Call every Friday",
                },
            )
            assert created.status_code == 201
            ingredient = created.json()
            assert ingredient["notes"] == "Call every Friday"

            updated = await client.patch(
                f"/api/v1/inventory/ingredients/{ingredient['id']}",
                headers=headers,
                params={"business_id": business_id},
                json={"notes": "Weekend restock priority"},
            )
            assert updated.status_code == 200
            assert updated.json()["notes"] == "Weekend restock priority"

    asyncio.run(run())


def test_supplier_tracker_groups_and_counts_low_stock():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client)
            headers = _auth_headers(token)

            payloads = [
                {
                    "name": "Flour",
                    "unit": "kg",
                    "current_stock": 2,
                    "reorder_point": 5,
                    "supplier": "Sime Darby",
                    "notes": "Call every Friday",
                },
                {
                    "name": "Sugar",
                    "unit": "kg",
                    "current_stock": 8,
                    "reorder_point": 5,
                    "supplier": "Sime Darby",
                    "notes": "Bulk order weekly",
                },
                {
                    "name": "Eggs",
                    "unit": "pcs",
                    "current_stock": 20,
                    "reorder_point": 30,
                    "supplier": None,
                    "notes": "Farm Fresh backup",
                },
            ]
            for payload in payloads:
                response = await client.post(
                    "/api/v1/inventory/ingredients",
                    headers=headers,
                    params={"business_id": business_id},
                    json=payload,
                )
                assert response.status_code == 201

            supplier_summary = await client.get(
                "/api/v1/inventory/suppliers",
                headers=headers,
                params={"business_id": business_id},
            )
            assert supplier_summary.status_code == 200
            data = supplier_summary.json()["suppliers"]
            assert len(data) == 2

            grouped = {row["supplier"]: row for row in data}
            assert grouped["Sime Darby"]["ingredient_count"] == 2
            assert grouped["Sime Darby"]["low_stock_count"] == 1
            assert grouped["Sime Darby"]["ingredients"][0]["notes"] is not None

            assert grouped["Unassigned supplier"]["ingredient_count"] == 1
            assert grouped["Unassigned supplier"]["low_stock_count"] == 1
            assert grouped["Unassigned supplier"]["ingredients"][0]["name"] == "Eggs"

    asyncio.run(run())
