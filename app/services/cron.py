from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.store import get_db, get_default_business_id, utc_now
from app.services.inventory import get_reorder_alerts
from app.services.provision import ProvisionEngine


LOCAL_TZ = ZoneInfo("Asia/Kuala_Lumpur")
scheduler = AsyncIOScheduler(timezone=LOCAL_TZ)
logger = logging.getLogger(__name__)


def list_business_ids() -> list[int]:
    with get_db() as conn:
        rows = conn.execute("SELECT id FROM businesses ORDER BY id ASC").fetchall()
    return [int(row["id"]) for row in rows]


def _get_business_ids() -> list[int]:
    """Get all active business IDs."""
    return list_business_ids()


def _today_iso() -> str:
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ).date().isoformat()


def _start_of_this_month() -> str:
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ).date().replace(day=1).isoformat()


def _start_of_last_month() -> str:
    today = datetime.now(timezone.utc).astimezone(LOCAL_TZ).date()
    last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    return last_month.isoformat()


def resolve_daily_close_date(value: str | None = None) -> str:
    if value is None:
        return datetime.now(timezone.utc).astimezone(LOCAL_TZ).date().isoformat()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("Invalid date format. Expected YYYY-MM-DD") from exc


def resolve_provision_month(value: str | None = None) -> str:
    if value is not None:
        try:
            return datetime.strptime(value, "%Y-%m").strftime("%Y-%m")
        except ValueError as exc:
            raise ValueError("Invalid month format. Expected YYYY-MM") from exc
    local_now = datetime.now(timezone.utc).astimezone(LOCAL_TZ)
    previous_month_end = local_now.replace(day=1) - timedelta(days=1)
    return previous_month_end.strftime("%Y-%m")


def _parse_timestamp(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        parsed = datetime.fromisoformat(raw_value)
    except ValueError:
        try:
            parsed = datetime.strptime(raw_value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(LOCAL_TZ)


def _effective_close_date(row) -> date | None:
    timestamp = _parse_timestamp(row["paid_at"]) or _parse_timestamp(row["created_at"])
    return timestamp.date() if timestamp else None


def _normalize_method(method: str | None) -> str:
    normalized = (method or "").strip().lower()
    if "cash" in normalized:
        return "cash"
    if "qr" in normalized or "duitnow" in normalized:
        return "qr"
    if normalized and normalized not in {"pending", "unknown"}:
        return "transfer"
    return "unknown"


def _build_daily_close_totals(business_id: int, close_date: str) -> dict:
    target_date = datetime.strptime(close_date, "%Y-%m-%d").date()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, total, payment_method, payment_status, created_at, paid_at
            FROM invoices
            WHERE business_id = ?
              AND payment_status = 'paid'
            ORDER BY id ASC
            """,
            (business_id,),
        ).fetchall()

    totals = {
        "business_id": business_id,
        "date": close_date,
        "total_cash": 0.0,
        "total_qr": 0.0,
        "total_transfer": 0.0,
        "total_orders": 0,
        "total_revenue": 0.0,
    }

    for row in rows:
        effective_date = _effective_close_date(row)
        if effective_date != target_date:
            continue
        amount = round(float(row["total"]), 2)
        totals["total_orders"] += 1
        totals["total_revenue"] = round(totals["total_revenue"] + amount, 2)
        bucket = _normalize_method(row["payment_method"])
        if bucket == "cash":
            totals["total_cash"] = round(totals["total_cash"] + amount, 2)
        elif bucket == "qr":
            totals["total_qr"] = round(totals["total_qr"] + amount, 2)
        elif bucket == "transfer":
            totals["total_transfer"] = round(totals["total_transfer"] + amount, 2)

    return totals


def _upsert_daily_close(summary: dict) -> dict:
    with get_db() as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM daily_ops
            WHERE business_id = ? AND date = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (summary["business_id"], summary["date"]),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE daily_ops
                SET total_cash = ?,
                    total_qr = ?,
                    total_transfer = ?,
                    total_orders = ?,
                    total_revenue = ?
                WHERE id = ?
                """,
                (
                    summary["total_cash"],
                    summary["total_qr"],
                    summary["total_transfer"],
                    summary["total_orders"],
                    summary["total_revenue"],
                    existing["id"],
                ),
            )
            row = conn.execute("SELECT * FROM daily_ops WHERE id = ?", (existing["id"],)).fetchone()
        else:
            cursor = conn.execute(
                """
                INSERT INTO daily_ops (
                    business_id,
                    date,
                    total_cash,
                    total_qr,
                    total_transfer,
                    total_orders,
                    total_revenue,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary["business_id"],
                    summary["date"],
                    summary["total_cash"],
                    summary["total_qr"],
                    summary["total_transfer"],
                    summary["total_orders"],
                    summary["total_revenue"],
                    utc_now(),
                ),
            )
            row = conn.execute("SELECT * FROM daily_ops WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def run_daily_close(business_id: int | None = None, close_date: str | None = None) -> dict:
    resolved_business_id = int(business_id or get_default_business_id())
    resolved_date = resolve_daily_close_date(close_date)
    logger.info("Running daily close for business=%s date=%s", resolved_business_id, resolved_date)
    summary = _build_daily_close_totals(resolved_business_id, resolved_date)
    daily_close = _upsert_daily_close(summary)
    reorder_alerts = get_reorder_alerts(resolved_business_id)
    for item in reorder_alerts:
        logger.warning(
            "LOW STOCK: %s (business=%s) - %s %s remaining (reorder at %s). Supplier: %s",
            item["name"],
            resolved_business_id,
            item["current_stock"],
            item["unit"],
            item["reorder_point"],
            item["supplier"] or "unknown",
        )
    return {
        "status": "ok",
        "business_id": resolved_business_id,
        "date": resolved_date,
        "daily_close": daily_close,
        "reorder_alerts": reorder_alerts,
    }


def run_monthly_provision(business_id: int | None = None, month: str | None = None) -> dict:
    resolved_business_id = int(business_id or get_default_business_id())
    resolved_month = resolve_provision_month(month)
    logger.info("Running monthly provision for business=%s month=%s", resolved_business_id, resolved_month)
    engine = ProvisionEngine()
    with get_db() as conn:
        row = conn.execute("SELECT provision_policy FROM businesses WHERE id = ?", (resolved_business_id,)).fetchone()
    policy = None
    if row and row["provision_policy"]:
        try:
            policy = json.loads(row["provision_policy"])
        except json.JSONDecodeError:
            policy = None
    try:
        result = engine.calculate(resolved_business_id, resolved_month, policy=policy)
    except LookupError as exc:
        return {
            "status": "skipped",
            "business_id": resolved_business_id,
            "month": resolved_month,
            "reason": str(exc),
        }

    with get_db() as conn:
        snapshot = conn.execute(
            """
            SELECT *
            FROM provision_snapshots
            WHERE business_id = ? AND month = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (resolved_business_id, resolved_month),
        ).fetchone()

    return {
        "status": "ok",
        "business_id": resolved_business_id,
        "month": resolved_month,
        "snapshot": dict(snapshot) if snapshot else None,
        "result": result,
    }


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


@scheduler.scheduled_job("cron", id="daily-close-job", hour=23, minute=59)
async def daily_close_job() -> list[dict]:
    today = _today_iso()
    logger.info("Running scheduled daily close for %s", today)
    results = [run_daily_close(business_id=business_id, close_date=today) for business_id in _get_business_ids()]
    logger.info("Scheduled daily close complete for %s", today)
    return results


@scheduler.scheduled_job("cron", id="monthly-provision-job", day=1, hour=8, minute=0)
async def monthly_provision_job() -> list[dict]:
    target_month = _start_of_last_month()[:7]
    logger.info("Running scheduled monthly provision for %s", target_month)
    results = [run_monthly_provision(business_id=business_id, month=target_month) for business_id in _get_business_ids()]
    logger.info("Scheduled monthly provision complete for %s", target_month)
    return results
