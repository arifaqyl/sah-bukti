from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime

from app.config import REMINDER_PROVIDER
from app.db.store import get_db, utc_now
from app.services.whatsapp import get_whatsapp_client


DEFAULT_REMINDER_TEMPLATE = (
    "Hi {customer_name}, friendly reminder that invoice {invoice_number} "
    "for RM{outstanding_amount:.2f} is overdue by {days_overdue} day(s). "
    "Please reply once payment is made."
)


class ReminderError(Exception):
    pass


class ReminderNotFoundError(ReminderError):
    pass


@dataclass(frozen=True)
class ReminderNotificationResult:
    ok: bool
    provider: str
    detail: str


class BaseReminderNotifier:
    def send(self, reminder: dict, customer: dict) -> ReminderNotificationResult:
        raise NotImplementedError


class MockReminderNotifier(BaseReminderNotifier):
    def send(self, reminder: dict, customer: dict) -> ReminderNotificationResult:
        return ReminderNotificationResult(ok=True, provider="mock", detail=f"mock:{customer.get('phone') or ''}")


class WhatsAppReminderNotifier(BaseReminderNotifier):
    def send(self, reminder: dict, customer: dict) -> ReminderNotificationResult:
        if not customer.get("phone"):
            return ReminderNotificationResult(ok=False, provider="whatsapp", detail="missing_phone")
        result = get_whatsapp_client().send_message(customer["phone"], reminder["message_text"])
        return ReminderNotificationResult(ok=result.ok, provider=result.provider, detail=result.detail)


def get_reminder_notifier() -> BaseReminderNotifier:
    if REMINDER_PROVIDER == "whatsapp":
        return WhatsAppReminderNotifier()
    return MockReminderNotifier()


def get_reminder_policies(business_id: int) -> list[dict]:
    ensure_default_reminder_policy(business_id)
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM reminder_policies
            WHERE business_id = ?
            ORDER BY id ASC
            """,
            (business_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_reminder_policy(business_id: int, payload: dict) -> dict:
    now = utc_now()
    with get_db() as conn:
        policy_id = payload.get("id")
        if policy_id is None:
            cursor = conn.execute(
                """
                INSERT INTO reminder_policies (
                    business_id, name, channel, min_days_overdue, cadence_days, enabled, template_text, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    business_id,
                    payload["name"],
                    payload["channel"],
                    payload["min_days_overdue"],
                    payload["cadence_days"],
                    1 if payload.get("enabled", True) else 0,
                    payload["template_text"],
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM reminder_policies WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return dict(row)

        conn.execute(
            """
            UPDATE reminder_policies
            SET name = ?, channel = ?, min_days_overdue = ?, cadence_days = ?, enabled = ?, template_text = ?, updated_at = ?
            WHERE id = ? AND business_id = ?
            """,
            (
                payload["name"],
                payload["channel"],
                payload["min_days_overdue"],
                payload["cadence_days"],
                1 if payload.get("enabled", True) else 0,
                payload["template_text"],
                now,
                policy_id,
                business_id,
            ),
        )
        row = conn.execute(
            "SELECT * FROM reminder_policies WHERE id = ? AND business_id = ?",
            (policy_id, business_id),
        ).fetchone()
    if not row:
        raise ReminderNotFoundError("Reminder policy not found")
    return dict(row)


def list_reminders(
    business_id: int,
    *,
    status: str | None = None,
    invoice_number: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    where_clauses = ["r.business_id = ?"]
    params: list[object] = [business_id]
    if status:
        where_clauses.append("r.status = ?")
        params.append(status)
    if invoice_number:
        where_clauses.append("i.invoice_number = ?")
        params.append(invoice_number)
    if date_from:
        where_clauses.append("date(r.generated_for_date) >= date(?)")
        params.append(date_from)
    if date_to:
        where_clauses.append("date(r.generated_for_date) <= date(?)")
        params.append(date_to)

    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT r.*, i.invoice_number, c.name AS customer_name, c.phone AS customer_phone, rp.name AS policy_name
            FROM reminders r
            JOIN invoices i ON i.id = r.invoice_id
            JOIN customers c ON c.id = r.customer_id
            JOIN reminder_policies rp ON rp.id = r.policy_id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY r.id DESC
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def get_reminder(reminder_id: int, business_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT r.*, i.invoice_number, c.name AS customer_name, c.phone AS customer_phone, rp.name AS policy_name
            FROM reminders r
            JOIN invoices i ON i.id = r.invoice_id
            JOIN customers c ON c.id = r.customer_id
            JOIN reminder_policies rp ON rp.id = r.policy_id
            WHERE r.id = ? AND r.business_id = ?
            """,
            (reminder_id, business_id),
        ).fetchone()
    return dict(row) if row else None


def list_reminder_events(reminder_id: int, business_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT re.*
            FROM reminder_events re
            JOIN reminders r ON r.id = re.reminder_id
            WHERE re.reminder_id = ? AND r.business_id = ?
            ORDER BY re.id ASC
            """,
            (reminder_id, business_id),
        ).fetchall()
    return [_deserialize_event(row) for row in rows]


def generate_reminders(
    *,
    business_id: int,
    actor_user_id: int | None,
    as_of_date: str | None = None,
) -> dict:
    target_date = _resolve_date(as_of_date)
    policies = [policy for policy in get_reminder_policies(business_id) if int(policy["enabled"]) == 1]
    overdue_invoices = list_overdue_invoices(business_id, target_date.isoformat())

    generated: list[dict] = []
    suppressed = 0
    for policy in policies:
        for invoice in overdue_invoices:
            if invoice["days_overdue"] < int(policy["min_days_overdue"]):
                continue
            if _should_suppress_by_cadence(invoice["invoice_id"], int(policy["id"]), int(policy["cadence_days"]), target_date.isoformat()):
                suppressed += 1
                continue
            dedupe_key = f"{invoice['invoice_id']}:{policy['id']}:{target_date.isoformat()}"
            reminder = _create_reminder(invoice, policy, dedupe_key, target_date.isoformat())
            if reminder is None:
                suppressed += 1
                continue
            _append_reminder_event(reminder["id"], actor_user_id, "generated", {"as_of_date": target_date.isoformat()})
            generated.append(reminder)

    return {
        "as_of_date": target_date.isoformat(),
        "generated_count": len(generated),
        "suppressed_count": suppressed,
        "reminders": generated,
    }


def send_reminder(*, reminder_id: int, business_id: int, actor_user_id: int | None) -> dict:
    reminder = get_reminder(reminder_id, business_id)
    if not reminder:
        raise ReminderNotFoundError("Reminder not found")
    if reminder["status"] == "sent":
        return reminder

    invoice = _get_invoice_summary(reminder["invoice_id"], business_id)
    if not invoice:
        raise ReminderNotFoundError("Invoice not found")
    if invoice["payment_status"] == "paid":
        raise ValueError("Paid invoices cannot receive reminders")

    customer = {"id": reminder["customer_id"], "name": reminder["customer_name"], "phone": reminder["customer_phone"]}
    notifier = get_reminder_notifier()
    result = notifier.send(reminder, customer)

    now = utc_now()
    with get_db() as conn:
        if result.ok:
            conn.execute(
                """
                UPDATE reminders
                SET status = 'sent', sent_at = ?, last_error = NULL
                WHERE id = ? AND business_id = ?
                """,
                (now, reminder_id, business_id),
            )
        else:
            conn.execute(
                """
                UPDATE reminders
                SET status = 'failed', last_error = ?
                WHERE id = ? AND business_id = ?
                """,
                (result.detail, reminder_id, business_id),
            )
    _append_reminder_event(
        reminder_id,
        actor_user_id,
        "sent" if result.ok else "send_failed",
        {"provider": result.provider, "detail": result.detail},
    )
    return get_reminder(reminder_id, business_id)


def ensure_default_reminder_policy(business_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM reminder_policies
            WHERE business_id = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (business_id,),
        ).fetchone()
        if row:
            return dict(row)
        now = utc_now()
        cursor = conn.execute(
            """
            INSERT INTO reminder_policies (
                business_id, name, channel, min_days_overdue, cadence_days, enabled, template_text, created_at, updated_at
            )
            VALUES (?, ?, 'mock', 1, 3, 1, ?, ?, ?)
            """,
            (business_id, "Default overdue reminder", DEFAULT_REMINDER_TEMPLATE, now, now),
        )
        created = conn.execute("SELECT * FROM reminder_policies WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(created)


def list_overdue_invoices(business_id: int, as_of_date: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                i.id AS invoice_id,
                i.customer_id,
                i.invoice_number,
                i.total,
                i.payment_status,
                i.due_date,
                c.name AS customer_name,
                c.phone AS customer_phone,
                MAX(0, CAST(julianday(?) - julianday(i.due_date) AS INTEGER)) AS days_overdue,
                ROUND(i.total - COALESCE(SUM(CASE WHEN p.confirmed = 1 THEN p.amount ELSE 0 END), 0), 2) AS outstanding_amount
            FROM invoices i
            JOIN customers c ON c.id = i.customer_id
            LEFT JOIN payments p ON p.invoice_id = i.id
            WHERE i.business_id = ?
              AND i.payment_status != 'paid'
              AND i.due_date IS NOT NULL
              AND date(i.due_date) < date(?)
            GROUP BY i.id, i.customer_id, i.invoice_number, i.total, i.payment_status, i.due_date, c.name, c.phone
            HAVING outstanding_amount > 0
            ORDER BY days_overdue DESC, i.id ASC
            """,
            (as_of_date, business_id, as_of_date),
        ).fetchall()
    return [dict(row) for row in rows]


def _create_reminder(invoice: dict, policy: dict, dedupe_key: str, generated_for_date: str) -> dict | None:
    message_text = _render_message(invoice, policy)
    now = utc_now()
    with get_db() as conn:
        try:
            cursor = conn.execute(
                """
                INSERT INTO reminders (
                    business_id, invoice_id, customer_id, policy_id, channel, status,
                    days_overdue, outstanding_amount, message_text, dedupe_key, generated_for_date, generated_at
                )
                VALUES (?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(policy["business_id"]),
                    invoice["invoice_id"],
                    invoice["customer_id"],
                    policy["id"],
                    policy["channel"],
                    int(invoice["days_overdue"]),
                    float(invoice["outstanding_amount"]),
                    message_text,
                    dedupe_key,
                    generated_for_date,
                    now,
                ),
            )
        except sqlite3.IntegrityError:
            return None
        row = conn.execute(
            """
            SELECT r.*, i.invoice_number, c.name AS customer_name, c.phone AS customer_phone, rp.name AS policy_name
            FROM reminders r
            JOIN invoices i ON i.id = r.invoice_id
            JOIN customers c ON c.id = r.customer_id
            JOIN reminder_policies rp ON rp.id = r.policy_id
            WHERE r.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row) if row else None


def _render_message(invoice: dict, policy: dict) -> str:
    return str(policy["template_text"]).format(
        customer_name=invoice["customer_name"],
        invoice_number=invoice["invoice_number"],
        outstanding_amount=float(invoice["outstanding_amount"]),
        days_overdue=int(invoice["days_overdue"]),
        due_date=invoice["due_date"],
    )


def _should_suppress_by_cadence(invoice_id: int, policy_id: int, cadence_days: int, as_of_date: str) -> bool:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT generated_for_date
            FROM reminders
            WHERE invoice_id = ? AND policy_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (invoice_id, policy_id),
        ).fetchone()
    if not row:
        return False
    last_date = datetime.strptime(row["generated_for_date"], "%Y-%m-%d").date()
    current = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    return (current - last_date).days < cadence_days


def _append_reminder_event(reminder_id: int, actor_user_id: int | None, event_type: str, payload: dict | None) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO reminder_events (reminder_id, actor_user_id, event_type, event_payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                reminder_id,
                actor_user_id,
                event_type,
                json.dumps(payload) if payload is not None else None,
                utc_now(),
            ),
        )


def _deserialize_event(row) -> dict:
    data = dict(row)
    payload = data.get("event_payload")
    if isinstance(payload, str):
        try:
            data["event_payload"] = json.loads(payload)
        except json.JSONDecodeError:
            data["event_payload"] = None
    return data


def _resolve_date(value: str | None) -> date:
    if value is None:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Invalid date format. Expected YYYY-MM-DD") from exc


def _get_invoice_summary(invoice_id: int, business_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT i.id, i.payment_status, i.invoice_number, c.name AS customer_name, c.phone AS customer_phone
            FROM invoices i
            JOIN customers c ON c.id = i.customer_id
            WHERE i.id = ? AND i.business_id = ?
            """,
            (invoice_id, business_id),
        ).fetchone()
    return dict(row) if row else None
