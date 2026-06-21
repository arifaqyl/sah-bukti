import asyncio

from httpx import ASGITransport, AsyncClient

from app.db.store import reset_db
from app.main import create_app
from app.services.auth import list_memberships


def _auth_headers(token: str) -> dict:
    return {"authorization": f"Bearer {token}"}


async def _signup(client: AsyncClient, email: str, business_name: str) -> dict:
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "password123",
            "display_name": business_name,
            "business_name": business_name,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    memberships = list_memberships(payload["user"]["id"])
    assert len(memberships) == 1
    return {
        "token": payload["access_token"],
        "user_id": payload["user"]["id"],
        "business_id": memberships[0]["business_id"],
    }


def test_auth_signup_login_me_and_logout():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            signup = await client.post(
                "/api/v1/auth/signup",
                json={
                    "email": "owner@example.com",
                    "password": "password123",
                    "display_name": "Owner User",
                    "business_name": "Owner Bakery",
                },
            )
            assert signup.status_code == 201
            signup_payload = signup.json()
            assert signup_payload["token_type"] == "bearer"
            assert signup_payload["user"]["email"] == "owner@example.com"

            me = await client.get("/api/v1/auth/me", headers=_auth_headers(signup_payload["access_token"]))
            assert me.status_code == 200
            assert me.json()["email"] == "owner@example.com"

            memberships = await client.get("/api/v1/auth/memberships", headers=_auth_headers(signup_payload["access_token"]))
            assert memberships.status_code == 200
            assert len(memberships.json()) == 1
            assert memberships.json()[0]["business_name"] == "Owner Bakery"

            businesses = await client.get("/api/v1/businesses", headers=_auth_headers(signup_payload["access_token"]))
            assert businesses.status_code == 200
            assert len(businesses.json()) == 1
            assert businesses.json()[0]["name"] == "Owner Bakery"

            unauth_me = await client.get("/api/v1/auth/me")
            assert unauth_me.status_code == 401

            login = await client.post(
                "/api/v1/auth/login",
                json={"email": "owner@example.com", "password": "password123"},
            )
            assert login.status_code == 200
            assert login.json()["user"]["email"] == "owner@example.com"

            logout = await client.post("/api/v1/auth/logout", headers=_auth_headers(signup_payload["access_token"]))
            assert logout.status_code == 200
            assert logout.json() == {"ok": True}

            revoked_me = await client.get("/api/v1/auth/me", headers=_auth_headers(signup_payload["access_token"]))
            assert revoked_me.status_code == 401

    asyncio.run(run())


def test_signup_creates_fresh_tenants():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await _signup(client, "owner-a@example.com", "Owner Bakery A")
            second = await _signup(client, "owner-b@example.com", "Owner Bakery B")

            assert first["business_id"] != 1
            assert second["business_id"] != 1
            assert first["business_id"] != second["business_id"]

    asyncio.run(run())


def test_admin_cron_routes_require_owned_business_context():
    async def run() -> None:
        reset_db()
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            denied = await client.post(
                "/api/v1/admin/cron/daily-close",
                params={"business_id": 2, "date": "2026-06-18"},
            )
            assert denied.status_code == 401

            first = await _signup(client, "owner-a@example.com", "Owner Bakery A")
            second = await _signup(client, "owner-b@example.com", "Owner Bakery B")

            missing_business = await client.post(
                "/api/v1/admin/cron/daily-close",
                headers=_auth_headers(first["token"]),
                params={"date": "2026-06-18"},
            )
            assert missing_business.status_code == 400

            own_business = await client.post(
                "/api/v1/admin/cron/daily-close",
                headers=_auth_headers(first["token"]),
                params={"business_id": first["business_id"], "date": "2026-06-18"},
            )
            assert own_business.status_code == 200
            assert own_business.json()["status"] == "ok"

            other_business = await client.post(
                "/api/v1/admin/cron/daily-close",
                headers=_auth_headers(first["token"]),
                params={"business_id": second["business_id"], "date": "2026-06-18"},
            )
            assert other_business.status_code == 403

            removed_get = await client.get(
                "/admin/cron/run-daily-close",
                headers=_auth_headers(first["token"]),
            )
            assert removed_get.status_code == 404

    asyncio.run(run())
