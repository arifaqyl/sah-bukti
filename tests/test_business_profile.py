import asyncio

from httpx import ASGITransport, AsyncClient

from app.db.store import reset_db
from app.main import create_app
from app.services.auth import list_memberships


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


def test_business_profile_get_and_patch():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client, "profile-owner@example.com", "Profile Biz")
            headers = _auth_headers(token)

            current = await client.get(
                "/api/v1/business/profile",
                headers=headers,
                params={"business_id": business_id},
            )
            assert current.status_code == 200
            assert current.json()["name"] == "Profile Biz"

            updated = await client.patch(
                "/api/v1/business/profile",
                headers=headers,
                params={"business_id": business_id},
                json={
                    "name": "Warung Profile",
                    "tagline": "reviewable evidence",
                    "theme_color": "#D4A853",
                    "owner_whatsapp": "60123456789",
                    "industry": "food",
                },
            )
            assert updated.status_code == 200
            payload = updated.json()
            assert payload["business_id"] == business_id
            assert payload["name"] == "Warung Profile"
            assert payload["tagline"] == "reviewable evidence"
            assert payload["theme_color"] == "#D4A853"
            assert payload["owner_whatsapp"] == "60123456789"
            assert payload["industry"] == "food"

    asyncio.run(run())


def test_invalid_theme_color_rejected():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token, business_id = await _signup(client, "theme-owner@example.com", "Theme Biz")
            response = await client.patch(
                "/api/v1/business/profile",
                headers=_auth_headers(token),
                params={"business_id": business_id},
                json={"theme_color": "gold"},
            )
            assert response.status_code == 422

    asyncio.run(run())


def test_cross_tenant_business_profile_denied():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_a, _business_a = await _signup(client, "profile-a@example.com", "Profile A")
            _token_b, business_b = await _signup(client, "profile-b@example.com", "Profile B")

            response = await client.get(
                "/api/v1/business/profile",
                headers=_auth_headers(token_a),
                params={"business_id": business_b},
            )
            assert response.status_code == 403

    asyncio.run(run())
