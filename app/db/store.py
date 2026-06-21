import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import RLock

from app.config import DB_PATH


DB_LOCK = RLock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_db():
    with DB_LOCK:
        conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_SQL)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS businesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    owner_whatsapp TEXT,
    whatsapp_group_chat_id TEXT,
    whatsapp_group_name TEXT,
    industry TEXT DEFAULT 'general',
    tagline TEXT,
    theme_color TEXT,
    provision_policy TEXT DEFAULT '{"current": 0.0, "31-60": 0.05, "61-90": 0.10, "91-180": 0.20, "180+": 1.0}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS business_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    business_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'staff',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(business_id) REFERENCES businesses(id),
    UNIQUE(user_id, business_id)
);

CREATE TABLE IF NOT EXISTS auth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES businesses(id)
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    invoice_number TEXT UNIQUE NOT NULL,
    items TEXT NOT NULL DEFAULT '[]',
    subtotal REAL NOT NULL DEFAULT 0,
    tax REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL,
    payment_method TEXT NOT NULL DEFAULT 'pending',
    payment_status TEXT NOT NULL DEFAULT 'pending',
    due_date TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    paid_at TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES businesses(id),
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    method TEXT NOT NULL,
    reference TEXT,
    confirmed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(invoice_id) REFERENCES invoices(id)
);

CREATE TABLE IF NOT EXISTS payment_proofs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    invoice_id INTEGER,
    uploaded_by_user_id INTEGER,
    approved_payment_id INTEGER,
    source_channel TEXT NOT NULL DEFAULT 'dashboard',
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    ocr_status TEXT NOT NULL DEFAULT 'pending',
    ocr_error TEXT,
    ocr_payload TEXT,
    extracted_amount REAL,
    extracted_reference TEXT,
    extracted_paid_at TEXT,
    confidence_score REAL,
    review_state TEXT NOT NULL DEFAULT 'needs_review',
    decision_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TEXT,
    FOREIGN KEY(business_id) REFERENCES businesses(id),
    FOREIGN KEY(invoice_id) REFERENCES invoices(id),
    FOREIGN KEY(uploaded_by_user_id) REFERENCES users(id),
    FOREIGN KEY(approved_payment_id) REFERENCES payments(id),
    UNIQUE(business_id, file_hash)
);

CREATE TABLE IF NOT EXISTS payment_proof_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_proof_id INTEGER NOT NULL,
    actor_user_id INTEGER,
    event_type TEXT NOT NULL,
    event_payload TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(payment_proof_id) REFERENCES payment_proofs(id),
    FOREIGN KEY(actor_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS provider_callback_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER,
    provider TEXT NOT NULL,
    event_key TEXT NOT NULL,
    invoice_number TEXT,
    transaction_id TEXT,
    transaction_reference TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    raw_payload TEXT,
    payload_hash TEXT NOT NULL,
    signature_valid INTEGER NOT NULL DEFAULT 0,
    processing_status TEXT NOT NULL,
    processed_invoice_id INTEGER,
    proof_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    received_at TEXT,
    processed_at TEXT,
    FOREIGN KEY(business_id) REFERENCES businesses(id),
    FOREIGN KEY(proof_id) REFERENCES payment_proofs(id),
    FOREIGN KEY(processed_invoice_id) REFERENCES invoices(id),
    UNIQUE(provider, event_key)
);

CREATE TABLE IF NOT EXISTS whatsapp_sessions (
    phone TEXT PRIMARY KEY,
    state TEXT DEFAULT '{}',
    customer_name TEXT,
    current_order TEXT DEFAULT '[]',
    total_amount REAL DEFAULT 0,
    last_order_date TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS receipts (
    id TEXT PRIMARY KEY,
    business_id INTEGER NOT NULL,
    proof_id INTEGER,
    invoice_id INTEGER,
    file_path TEXT NOT NULL,
    sent_to_phone TEXT,
    sent_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(business_id) REFERENCES businesses(id),
    FOREIGN KEY(proof_id) REFERENCES payment_proofs(id),
    FOREIGN KEY(invoice_id) REFERENCES invoices(id)
);

CREATE TABLE IF NOT EXISTS reminder_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'mock',
    min_days_overdue INTEGER NOT NULL DEFAULT 1,
    cadence_days INTEGER NOT NULL DEFAULT 3,
    enabled INTEGER NOT NULL DEFAULT 1,
    template_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES businesses(id)
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    invoice_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    policy_id INTEGER NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    days_overdue INTEGER NOT NULL DEFAULT 0,
    outstanding_amount REAL NOT NULL DEFAULT 0,
    message_text TEXT NOT NULL,
    dedupe_key TEXT NOT NULL,
    generated_for_date TEXT NOT NULL,
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,
    last_error TEXT,
    FOREIGN KEY(business_id) REFERENCES businesses(id),
    FOREIGN KEY(invoice_id) REFERENCES invoices(id),
    FOREIGN KEY(customer_id) REFERENCES customers(id),
    FOREIGN KEY(policy_id) REFERENCES reminder_policies(id),
    UNIQUE(business_id, dedupe_key)
);

CREATE TABLE IF NOT EXISTS reminder_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reminder_id INTEGER NOT NULL,
    actor_user_id INTEGER,
    event_type TEXT NOT NULL,
    event_payload TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(reminder_id) REFERENCES reminders(id),
    FOREIGN KEY(actor_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    unit TEXT DEFAULT 'pcs',
    current_stock REAL NOT NULL DEFAULT 0,
    reorder_point REAL NOT NULL DEFAULT 0,
    supplier TEXT,
    notes TEXT,
    last_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES businesses(id)
);

CREATE TABLE IF NOT EXISTS daily_ops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    total_cash REAL NOT NULL DEFAULT 0,
    total_qr REAL NOT NULL DEFAULT 0,
    total_transfer REAL NOT NULL DEFAULT 0,
    total_orders INTEGER NOT NULL DEFAULT 0,
    total_revenue REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES businesses(id)
);

CREATE TABLE IF NOT EXISTS provision_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    month TEXT NOT NULL,
    total_outstanding REAL NOT NULL DEFAULT 0,
    provision_amount REAL NOT NULL DEFAULT 0,
    policy_used TEXT,
    journal_entry TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES businesses(id)
);
"""

def run_migrations() -> None:
    migrations_dir = DB_PATH.parent.parent / "migrations"
    if not migrations_dir.exists():
        return
    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        return
    with get_db() as conn:
        for sql_file in sql_files:
            try:
                conn.executescript(sql_file.read_text(encoding="utf-8"))
            except sqlite3.OperationalError as exc:
                lowered = str(exc).lower()
                if "duplicate column name" not in lowered and "no such table" not in lowered:
                    raise


def init_db() -> None:
    with get_db() as conn:
        row = conn.execute("SELECT id FROM businesses ORDER BY id ASC LIMIT 1").fetchone()
        business_id = int(row["id"]) if row is not None else None
        if row is None:
            now = utc_now()
            conn.execute(
                """
                INSERT INTO businesses (name, owner_whatsapp, industry, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("Sah.Bukti Demo", None, "general", now, now),
            )
            business_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        user_row = conn.execute(
            "SELECT id FROM users WHERE email = ? LIMIT 1",
            ("demo@sahbukti.local",),
        ).fetchone()
        if user_row is None:
            now = utc_now()
            conn.execute(
                """
                INSERT INTO users (email, password_hash, display_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("demo@sahbukti.local", "seeded-demo-account", "Sah.Bukti Demo Owner", now, now),
            )
            user_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        else:
            user_id = int(user_row["id"])
        membership = conn.execute(
            """
            SELECT id
            FROM business_memberships
            WHERE user_id = ? AND business_id = ?
            LIMIT 1
            """,
            (user_id, business_id),
        ).fetchone()
        if membership is None:
            now = utc_now()
            conn.execute(
                """
                INSERT INTO business_memberships (user_id, business_id, role, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, business_id, "owner", now),
            )
    run_migrations()


def reset_db() -> None:
    with DB_LOCK:
        time.sleep(0.05)
        conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = OFF")
            tables = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            ).fetchall()
            for row in tables:
                conn.execute(f"DROP TABLE IF EXISTS {row['name']}")
            sqlite_sequence = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_sequence'"
            ).fetchone()
            if sqlite_sequence:
                conn.execute("DELETE FROM sqlite_sequence")
            conn.commit()
        finally:
            conn.close()
        for path in (DB_PATH.with_name(f"{DB_PATH.name}-wal"), DB_PATH.with_name(f"{DB_PATH.name}-shm")):
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass
        init_db()
        try:
            from app.services.provision import ProvisionEngine

            ProvisionEngine._cache.clear()
        except Exception:
            pass


def get_default_business_id() -> int:
    with get_db() as conn:
        row = conn.execute("SELECT id FROM businesses ORDER BY id ASC LIMIT 1").fetchone()
    if row is None:
        raise RuntimeError("No business exists in the database")
    return int(row["id"])
