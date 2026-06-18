import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import DB_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS businesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    owner_whatsapp TEXT,
    industry TEXT DEFAULT 'general',
    provision_policy TEXT DEFAULT '{"current": 0.0, "31-60": 0.05, "61-90": 0.10, "91-180": 0.20, "180+": 1.0}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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

CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    unit TEXT DEFAULT 'pcs',
    current_stock REAL NOT NULL DEFAULT 0,
    reorder_point REAL NOT NULL DEFAULT 0,
    supplier TEXT,
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
            conn.executescript(sql_file.read_text(encoding="utf-8"))


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
        row = conn.execute("SELECT id FROM businesses ORDER BY id ASC LIMIT 1").fetchone()
        if row is None:
            now = utc_now()
            conn.execute(
                """
                INSERT INTO businesses (name, owner_whatsapp, industry, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("Kede Demo", None, "general", now, now),
            )
    run_migrations()


def reset_db() -> None:
    with get_db() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        for table in (
            "provision_snapshots",
            "daily_ops",
            "ingredients",
            "payments",
            "invoices",
            "customers",
            "businesses",
        ):
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute("PRAGMA foreign_keys = ON")
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
