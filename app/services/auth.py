import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.db.store import get_db, utc_now


TOKEN_TTL_HOURS = 24 * 7
PASSWORD_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt, expected = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    iterations = int(iterations_raw)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return secrets.compare_digest(digest.hex(), expected)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _public_user(row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
    }


def _create_access_token_in_conn(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)).isoformat()
    conn.execute(
        """
        INSERT INTO auth_tokens (user_id, token_hash, expires_at, revoked, created_at)
        VALUES (?, ?, ?, 0, ?)
        """,
        (user_id, hash_token(token), expires_at, utc_now()),
    )
    return token


def create_user_and_business(email: str, password: str, display_name: str | None = None, business_name: str | None = None) -> dict:
    now = utc_now()
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
        if existing:
            raise ValueError("Email already registered")

        cursor = conn.execute(
            """
            INSERT INTO users (email, password_hash, display_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email.lower(), hash_password(password), display_name, now, now),
        )
        user_id = cursor.lastrowid
        resolved_business_name = business_name or display_name or email.split("@", 1)[0]
        conn.execute(
            """
            INSERT INTO businesses (name, owner_whatsapp, industry, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (resolved_business_name, None, "general", now, now),
        )
        business_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        conn.execute(
            """
            INSERT INTO business_memberships (user_id, business_id, role, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, business_id, "owner", now),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _public_user(row)


def signup_user(email: str, password: str, display_name: str | None = None, business_name: str | None = None) -> dict:
    now = utc_now()
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
        if existing:
            raise ValueError("Email already registered")

        cursor = conn.execute(
            """
            INSERT INTO users (email, password_hash, display_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email.lower(), hash_password(password), display_name, now, now),
        )
        user_id = cursor.lastrowid
        resolved_business_name = business_name or display_name or email.split("@", 1)[0]
        business_cursor = conn.execute(
            """
            INSERT INTO businesses (name, owner_whatsapp, industry, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (resolved_business_name, None, "general", now, now),
        )
        business_id = business_cursor.lastrowid
        conn.execute(
            """
            INSERT INTO business_memberships (user_id, business_id, role, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, business_id, "owner", now),
        )
        token = _create_access_token_in_conn(conn, int(user_id))
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"user": _public_user(row), "access_token": token}


def authenticate_user(email: str, password: str) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email.lower(),)).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            raise ValueError("Invalid email or password")
        token = _create_access_token_in_conn(conn, int(row["id"]))
        user = _public_user(row)
    return {"user": user, "access_token": token}


def create_access_token(user_id: int) -> str:
    with get_db() as conn:
        return _create_access_token_in_conn(conn, user_id)


def get_user_by_token(token: str) -> dict | None:
    token_hash = hash_token(token)
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT u.*
            FROM auth_tokens t
            JOIN users u ON u.id = t.user_id
            WHERE t.token_hash = ?
              AND t.revoked = 0
              AND t.expires_at > ?
            LIMIT 1
            """,
            (token_hash, utc_now()),
        ).fetchone()
    return _public_user(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _public_user(row) if row else None


def get_business(business_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM businesses WHERE id = ?", (business_id,)).fetchone()
    return dict(row) if row else None


def get_membership(user_id: int, business_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT bm.*
            FROM business_memberships bm
            WHERE bm.user_id = ? AND bm.business_id = ?
            """,
            (user_id, business_id),
        ).fetchone()
    return dict(row) if row else None


def list_memberships(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT bm.*, b.name AS business_name
            FROM business_memberships bm
            JOIN businesses b ON b.id = bm.business_id
            WHERE bm.user_id = ?
            ORDER BY bm.business_id ASC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_businesses_for_user(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                b.id,
                b.name,
                b.owner_whatsapp,
                b.whatsapp_group_chat_id,
                b.whatsapp_group_name,
                b.industry,
                b.tagline,
                b.theme_color,
                bm.role
            FROM business_memberships bm
            JOIN businesses b ON b.id = bm.business_id
            WHERE bm.user_id = ?
            ORDER BY b.id ASC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def business_has_members(business_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 AS ok FROM business_memberships WHERE business_id = ? LIMIT 1",
            (business_id,),
        ).fetchone()
    return bool(row)


def is_owner(user_id: int, business_id: int) -> bool:
    membership = get_membership(user_id, business_id)
    return bool(membership and membership["role"] == "owner")


def revoke_token(token: str) -> None:
    with get_db() as conn:
        conn.execute("UPDATE auth_tokens SET revoked = 1 WHERE token_hash = ?", (hash_token(token),))
