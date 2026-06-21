#!/usr/bin/env python3
"""Seed realistic demo data for Sah.Bukti."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.store import DB_PATH, get_db


BAKERY_ITEMS = {
    "roti_canai": {"name": "Roti Canai", "unit_price": 1.50},
    "nasi_lemak": {"name": "Nasi Lemak", "unit_price": 5.00},
    "teh_tarik": {"name": "Teh Tarik", "unit_price": 2.50},
    "kuih_muih": {"name": "Kuih-Muih", "unit_price": 3.00},
}
DEMO_OWNER_PHONE = "60123456789"

MALAYSIAN_METHODS = ["cash", "qr", "transfer"]

INVOICE_NUMBERS = [
    "INV-CUR1", "INV-CUR2",
    "INV-A1", "INV-A2", "INV-A3",
    "INV-B1",
    "INV-WO1",
]


def ensure_business(conn):
    row = conn.execute("SELECT id FROM businesses ORDER BY id ASC LIMIT 1").fetchone()
    now = datetime.now(timezone.utc).isoformat()
    if row is None:
        conn.execute(
            """
            INSERT INTO businesses (name, owner_whatsapp, industry, tagline, theme_color, provision_policy, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Sah.Bukti Demo",
                DEMO_OWNER_PHONE,
                "baker",
                "reviewable evidence for Malaysian micro-sellers",
                "#D4A853",
                json.dumps({"current": 0.0, "31-60": 0.05, "61-90": 0.10, "91-180": 0.20, "180+": 1.0}),
                now,
                now,
            ),
        )
        return conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    business_id = row["id"]
    conn.execute(
        """
        UPDATE businesses
        SET owner_whatsapp = ?, tagline = ?, theme_color = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            DEMO_OWNER_PHONE,
            "reviewable evidence for Malaysian micro-sellers",
            "#D4A853",
            now,
            business_id,
        ),
    )
    return business_id


def ensure_demo_owner(conn, business_id: int) -> int:
    row = conn.execute(
        """
        SELECT u.id
        FROM business_memberships bm
        JOIN users u ON u.id = bm.user_id
        WHERE bm.business_id = ?
        ORDER BY CASE WHEN bm.role = 'owner' THEN 0 ELSE 1 END, bm.id ASC
        LIMIT 1
        """,
        (business_id,),
    ).fetchone()
    if row:
        return int(row["id"])

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO users (email, password_hash, display_name, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("demo@sahbukti.local", "seeded-demo-account", "Sah.Bukti Demo Owner", now, now),
    )
    user_id = int(conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])
    conn.execute(
        """
        INSERT INTO business_memberships (user_id, business_id, role, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, business_id, "owner", now),
    )
    return user_id


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def add_customer(conn, business_id: int, name: str, phone: str | None = None) -> int:
    now = iso(datetime.now(timezone.utc))
    existing = conn.execute(
        "SELECT id FROM customers WHERE business_id = ? AND name = ?",
        (business_id, name),
    ).fetchone()
    if existing:
        return existing["id"]
    conn.execute(
        """
        INSERT INTO customers (business_id, name, phone, email, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (business_id, name, phone, f"{name.lower().replace(' ', '.')}@demo.local", now),
    )
    return conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


def add_invoice(
    conn,
    *,
    business_id: int,
    customer_id: int,
    invoice_number: str,
    total: float,
    payment_method: str,
    payment_status: str,
    created_at: datetime,
    due_date: datetime | None = None,
    paid_at: datetime | None = None,
    amount_paid: float = 0.0,
    items: list[dict] | None = None,
):
    subtotal = float(Decimal(str(total)) - Decimal("0.00"))
    conn.execute(
        """
        INSERT OR REPLACE INTO invoices (
            business_id, customer_id, invoice_number, items,
            subtotal, tax, total,
            payment_method, payment_status,
            due_date, created_at, paid_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            business_id,
            customer_id,
            invoice_number,
            json.dumps(items or []),
            subtotal,
            0.0,
            total,
            payment_method,
            payment_status,
            iso(due_date) if due_date else None,
            iso(created_at),
            iso(paid_at) if paid_at else None,
            iso(created_at),
        ),
    )
    inv_id = conn.execute("SELECT id FROM invoices WHERE invoice_number = ?", (invoice_number,)).fetchone()["id"]

    conn.execute("DELETE FROM payments WHERE invoice_id = ?", (inv_id,))
    if amount_paid > 0.0:
        conn.execute(
            """
            INSERT INTO payments (invoice_id, amount, method, reference, confirmed, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                inv_id,
                amount_paid,
                payment_method if payment_method != "pending" else "cash",
                f"DEMO-{inv_id}",
                1,
                iso(paid_at or created_at),
            ),
        )

    return inv_id


def add_ingredient(
    conn,
    business_id: int,
    name: str,
    unit: str,
    current_stock: float,
    reorder_point: float,
    supplier: str | None = None,
    notes: str | None = None,
):
    now = iso(datetime.now(timezone.utc))
    conn.execute(
        """
        INSERT OR REPLACE INTO ingredients (business_id, name, unit, current_stock, reorder_point, supplier, notes, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (business_id, name, unit, current_stock, reorder_point, supplier, notes, now),
    )


def add_daily_ops(conn, business_id: int, date: datetime, orders: int, revenue: float):
    cash = round(revenue * 0.45, 2)
    qr = round(revenue * 0.35, 2)
    transfer = round(revenue * 0.20, 2)
    conn.execute(
        """
        INSERT OR REPLACE INTO daily_ops (business_id, date, total_cash, total_qr, total_transfer, total_orders, total_revenue, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (business_id, date.strftime("%Y-%m-%d"), cash, qr, transfer, orders, round(revenue, 2), iso(date)),
    )


def make_items(*keys, base_qty=1):
    items = []
    for key in keys:
        item = BAKERY_ITEMS[key]
        items.append({
            "name": item["name"],
            "qty": base_qty,
            "unit_price": item["unit_price"],
        })
    return items


def add_proof(
    conn,
    business_id: int,
    uploaded_by_user_id: int | None,
    invoice_number: str,
    amount: float,
    reference: str,
    source: str = "whatsapp",
    state: str = "needs_review",
):
    inv = conn.execute("SELECT id FROM invoices WHERE invoice_number = ?", (invoice_number,)).fetchone()
    inv_id = inv["id"] if inv else None
    now = iso(datetime.now(timezone.utc))
    conn.execute(
        """
        INSERT INTO payment_proofs (business_id, invoice_id, uploaded_by_user_id, source_channel, file_path, file_hash, mime_type, file_size_bytes, extracted_amount, extracted_reference, review_state, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (business_id, inv_id, uploaded_by_user_id, source, "/demo/proof", f"hash-{reference}", "text/plain", 0, amount, reference, state, now),
    )


def main() -> int:
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found at {DB_PATH}. Run the app once to init the database.")

    with get_db() as conn:
        # Deduplicate customers first
        conn.execute("""
            DELETE FROM customers WHERE id NOT IN (
                SELECT MIN(id) FROM customers GROUP BY business_id, name
            )
        """)
        
        business_id = ensure_business(conn)
        demo_owner_user_id = ensure_demo_owner(conn, business_id)

        # Idempotent cleanup: only remove records seeded by this script
        for num in INVOICE_NUMBERS:
            inv = conn.execute("SELECT id FROM invoices WHERE invoice_number = ?", (num,)).fetchone()
            if inv:
                proof_rows = conn.execute(
                    "SELECT id FROM payment_proofs WHERE invoice_id = ?",
                    (inv["id"],),
                ).fetchall()
                for proof_row in proof_rows:
                    proof_id = int(proof_row["id"])
                    conn.execute("DELETE FROM payment_proof_events WHERE payment_proof_id = ?", (proof_id,))
                    conn.execute("DELETE FROM receipts WHERE proof_id = ?", (proof_id,))
                    conn.execute("DELETE FROM provider_callback_events WHERE proof_id = ?", (proof_id,))
                conn.execute("DELETE FROM payment_proofs WHERE invoice_id = ?", (inv["id"],))
                conn.execute("DELETE FROM receipts WHERE invoice_id = ?", (inv["id"],))
                conn.execute("DELETE FROM provider_callback_events WHERE processed_invoice_id = ?", (inv["id"],))
                conn.execute("DELETE FROM reminders WHERE invoice_id = ?", (inv["id"],))
                conn.execute("DELETE FROM payments WHERE invoice_id = ?", (inv["id"],))
                conn.execute("DELETE FROM invoices WHERE id = ?", (inv["id"],))
        conn.execute("DELETE FROM daily_ops WHERE date NOT IN (SELECT date FROM daily_ops) OR business_id = ?", (business_id,))
        conn.execute("DELETE FROM ingredients WHERE business_id = ?", (business_id,))

        # Customers
        ahmad = add_customer(conn, business_id, "Ahmad", "60111111111")
        siti = add_customer(conn, business_id, "Siti", "60122222222")
        lim = add_customer(conn, business_id, "Lim", "60133333333")
        mega = add_customer(conn, business_id, "Mega Catering", "60144444444")

        today = datetime.now(timezone.utc).date()

        def d(days_ago: int) -> datetime:
            return datetime.combine(today - timedelta(days=days_ago), datetime.min.time())

        # Provision story:
        # Current (0-7 days): 2 invoices
        add_invoice(
            conn, business_id=business_id, customer_id=ahmad,
            invoice_number="INV-CUR1", total=45.00, payment_method="qr",
            payment_status="pending", created_at=d(2), due_date=d(9),
            items=make_items("roti_canai", "teh_tarik", base_qty=2),
        )
        add_invoice(
            conn, business_id=business_id, customer_id=siti,
            invoice_number="INV-CUR2", total=62.50, payment_method="transfer",
            payment_status="pending", created_at=d(5), due_date=d(12),
            items=make_items("nasi_lemak", "kuih_muih"),
        )

        # 31-60 days aged (CNY ghosting): 3 invoices
        add_invoice(
            conn, business_id=business_id, customer_id=ahmad,
            invoice_number="INV-A1", total=180.00, payment_method="qr",
            payment_status="pending", created_at=d(35), due_date=d(42),
            items=make_items("nasi_lemak", "roti_canai", "teh_tarik", base_qty=3),
        )
        add_invoice(
            conn, business_id=business_id, customer_id=siti,
            invoice_number="INV-A2", total=220.00, payment_method="cash",
            payment_status="pending", created_at=d(45), due_date=d(52),
            items=make_items("kuih_muih", base_qty=4),
        )
        add_invoice(
            conn, business_id=business_id, customer_id=lim,
            invoice_number="INV-A3", total=140.00, payment_method="transfer",
            payment_status="pending", created_at=d(55), due_date=d(62),
            items=make_items("roti_canai", base_qty=6),
        )

        # 61-90 days (corporate dragging): 1 invoice
        add_invoice(
            conn, business_id=business_id, customer_id=mega,
            invoice_number="INV-B1", total=350.00, payment_method="qr",
            payment_status="pending", created_at=d(75), due_date=d(82),
            items=make_items("nasi_lemak", "roti_canai", "teh_tarik", "kuih_muih", base_qty=10),
        )

        # 180+ days (write-off risk): 1 invoice
        add_invoice(
            conn, business_id=business_id, customer_id=ahmad,
            invoice_number="INV-WO1", total=260.00, payment_method="cash",
            payment_status="pending", created_at=d(190), due_date=d(197),
            items=make_items("nasi_lemak", base_qty=8),
        )

        # Ingredients with realistic Malaysian bakery stock levels
        add_ingredient(conn, business_id, "Flour", "kg", 8.0, 10.0, "Sime Darby", "Call Sime Darby every Friday")
        add_ingredient(conn, business_id, "Sugar", "kg", 3.0, 10.0, "Malayan Sugar", "Low stock before weekend bulk orders")
        add_ingredient(conn, business_id, "Butter", "kg", 12.0, 5.0, "Lamsoon", "Keep chilled on delivery")
        add_ingredient(conn, business_id, "Eggs", "pcs", 80.0, 100.0, "Farm Fresh", "Confirm next-morning delivery slots")

        # 30 days of daily_ops (weekends higher)
        for i in range(30):
            ops_date = today - timedelta(days=i)
            weekday = ops_date.weekday()
            if weekday >= 5:  # Sat/Sun
                orders = 45 + (i % 7) * 3
                revenue = orders * 6.50
            else:
                orders = 20 + (i % 5) * 2
                revenue = orders * 5.80
            add_daily_ops(conn, business_id, datetime.combine(ops_date, datetime.min.time()), orders, revenue)

        # Demo payment proofs for Review queue (show in frontend)
        add_proof(conn, business_id, demo_owner_user_id, "INV-CUR1", 45.0, "TXN-DEMO-001")
        add_proof(conn, business_id, demo_owner_user_id, "INV-CUR2", 62.5, "TXN-DEMO-002")

        conn.commit()

    print(f"Seeded demo data into {DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
