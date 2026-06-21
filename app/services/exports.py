import csv
import io
import json
from calendar import monthrange
from datetime import datetime, timezone

from app.db.store import get_db, utc_now
from app.services.payment_proofs import list_payment_proofs
from app.services.payments import list_provider_callback_events
from app.services.provision import ProvisionEngine
from app.services.reminders import list_reminders


CALLBACK_ISSUE_STATUSES = {
    "missing_signature",
    "invalid_signature",
    "invoice_not_found",
    "missing_invoice_reference",
    "duplicate_event",
}


def export_invoices(business_id: int, export_format: str) -> str:
    rows = _fetch_rows(
        """
        SELECT
            i.id,
            i.invoice_number,
            c.name AS customer_name,
            c.phone AS customer_phone,
            i.total,
            i.payment_method,
            i.payment_status,
            i.due_date,
            i.created_at,
            i.paid_at
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE i.business_id = ?
        ORDER BY i.created_at DESC, i.id DESC
        """,
        (business_id,),
    )
    if export_format == "json":
        return json.dumps(rows, indent=2)
    return _rows_to_csv(
        [
            "id",
            "invoice_number",
            "customer_name",
            "customer_phone",
            "total",
            "payment_method",
            "payment_status",
            "due_date",
            "created_at",
            "paid_at",
        ],
        rows,
    )


def export_daily_ops(business_id: int, export_format: str) -> str:
    rows = _fetch_rows(
        """
        SELECT
            id,
            date,
            total_cash,
            total_qr,
            total_transfer,
            total_orders,
            total_revenue,
            created_at
        FROM daily_ops
        WHERE business_id = ?
        ORDER BY date DESC, id DESC
        """,
        (business_id,),
    )
    if export_format == "json":
        return json.dumps(rows, indent=2)
    return _rows_to_csv(
        [
            "id",
            "date",
            "total_cash",
            "total_qr",
            "total_transfer",
            "total_orders",
            "total_revenue",
            "created_at",
        ],
        rows,
    )


def export_inventory(business_id: int, export_format: str) -> str:
    rows = _fetch_rows(
        """
        SELECT
            id,
            name,
            unit,
            current_stock,
            reorder_point,
            supplier,
            notes,
            last_updated
        FROM ingredients
        WHERE business_id = ?
        ORDER BY name ASC, id DESC
        """,
        (business_id,),
    )
    if export_format == "json":
        return json.dumps(rows, indent=2)
    return _rows_to_csv(
        [
            "id",
            "name",
            "unit",
            "current_stock",
            "reorder_point",
            "supplier",
            "notes",
            "last_updated",
        ],
        rows,
    )


def export_accountant_package(
    *,
    business_id: int,
    month: str | None = None,
    as_of_date: str | None = None,
    include_proof_payloads: bool = False,
) -> dict:
    resolved_month, period_start, period_end, resolved_as_of = _resolve_period(month, as_of_date)
    invoices = _fetch_accountant_invoices(business_id, period_start, period_end, resolved_as_of)
    payments = _fetch_accountant_payments(business_id, period_start, period_end)
    payment_proofs = _filter_payment_proofs_for_period(
        list_payment_proofs(
            business_id,
            review_state=None,
            invoice_number=None,
            source_channel=None,
            date_from=None,
            date_to=None,
        ),
        invoices,
        period_start=period_start,
        period_end=period_end,
    )
    if not include_proof_payloads:
        payment_proofs = [{**proof, "ocr_payload": None} for proof in payment_proofs]
    reminders = list_reminders(
        business_id,
        status=None,
        invoice_number=None,
        date_from=period_start,
        date_to=period_end,
    )
    daily_closes = _fetch_accountant_daily_closes(business_id, period_start, period_end)
    provider_callbacks = list_provider_callback_events(
        business_id,
        status=None,
        invoice_number=None,
        date_from=period_start,
        date_to=period_end,
    )
    provision = _build_provision_section(business_id, resolved_month)
    risk_flags = _build_risk_flags(
        business_id=business_id,
        invoices=invoices,
        payment_proofs=payment_proofs,
        reminders=reminders,
        daily_closes=daily_closes,
        provider_callbacks=provider_callbacks,
        month=resolved_month,
        as_of_date=resolved_as_of,
    )
    summary = _build_summary(
        invoices=invoices,
        payments=payments,
        payment_proofs=payment_proofs,
        reminders=reminders,
        provider_callbacks=provider_callbacks,
        as_of_date=resolved_as_of,
    )
    return {
        "business_id": business_id,
        "generated_at": utc_now(),
        "period": {
            "month": resolved_month,
            "as_of_date": resolved_as_of,
        },
        "summary": summary,
        "invoices": invoices,
        "payments": payments,
        "payment_proofs": payment_proofs,
        "reminders": reminders,
        "daily_closes": daily_closes,
        "provision": provision,
        "provider_callbacks": provider_callbacks,
        "risk_flags": risk_flags,
    }


def _fetch_rows(query: str, params: tuple) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _fetch_accountant_invoices(
    business_id: int,
    period_start: str | None,
    period_end: str | None,
    as_of_date: str | None,
) -> list[dict]:
    outstanding_cutoff = as_of_date or period_end
    where_clauses = ["i.business_id = ?"]
    where_params: list[object] = [business_id]
    if period_start:
        where_clauses.append("date(i.created_at) >= date(?)")
        where_params.append(period_start)
    if period_end:
        where_clauses.append("date(i.created_at) <= date(?)")
        where_params.append(period_end)

    paid_filter = ""
    select_params: list[object] = []
    if outstanding_cutoff:
        paid_filter = "AND date(p.created_at) <= date(?)"
        select_params.append(outstanding_cutoff)

    query = f"""
        SELECT
            i.id,
            i.customer_id,
            i.invoice_number,
            c.name AS customer_name,
            c.phone AS customer_phone,
            i.total,
            i.payment_method,
            i.payment_status,
            i.due_date,
            i.created_at,
            i.paid_at,
            ROUND(COALESCE(SUM(CASE WHEN p.confirmed = 1 {paid_filter} THEN p.amount ELSE 0 END), 0), 2) AS paid_amount
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        LEFT JOIN payments p ON p.invoice_id = i.id
        WHERE {' AND '.join(where_clauses)}
        GROUP BY i.id, i.customer_id, i.invoice_number, c.name, c.phone, i.total, i.payment_method, i.payment_status, i.due_date, i.created_at, i.paid_at
        ORDER BY date(i.created_at) DESC, i.id DESC
    """
    rows = _fetch_rows(query, tuple(select_params + where_params))
    resolved_as_of = as_of_date or period_end or datetime.now(timezone.utc).date().isoformat()
    for row in rows:
        paid_amount = float(row["paid_amount"] or 0.0)
        total = float(row["total"])
        outstanding_amount = round(max(total - paid_amount, 0.0), 2)
        is_overdue = bool(row.get("due_date")) and outstanding_amount > 0 and row["due_date"] < resolved_as_of
        row["paid_amount"] = paid_amount
        row["outstanding_amount"] = outstanding_amount
        row["is_overdue"] = is_overdue
    return rows


def _fetch_accountant_payments(
    business_id: int,
    period_start: str | None,
    period_end: str | None,
) -> list[dict]:
    where_clauses = ["i.business_id = ?"]
    params: list[object] = [business_id]
    if period_start:
        where_clauses.append("date(p.created_at) >= date(?)")
        params.append(period_start)
    if period_end:
        where_clauses.append("date(p.created_at) <= date(?)")
        params.append(period_end)
    return _fetch_rows(
        f"""
        SELECT
            p.id,
            p.invoice_id,
            i.invoice_number,
            p.amount,
            p.method,
            p.reference,
            p.confirmed,
            p.created_at
        FROM payments p
        JOIN invoices i ON i.id = p.invoice_id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY date(p.created_at) DESC, p.id DESC
        """,
        tuple(params),
    )


def _fetch_accountant_daily_closes(
    business_id: int,
    period_start: str | None,
    period_end: str | None,
) -> list[dict]:
    where_clauses = ["business_id = ?"]
    params: list[object] = [business_id]
    if period_start:
        where_clauses.append("date(date) >= date(?)")
        params.append(period_start)
    if period_end:
        where_clauses.append("date(date) <= date(?)")
        params.append(period_end)
    return _fetch_rows(
        f"""
        SELECT
            id,
            date,
            total_cash,
            total_qr,
            total_transfer,
            total_orders,
            total_revenue,
            created_at
        FROM daily_ops
        WHERE {' AND '.join(where_clauses)}
        ORDER BY date DESC, id DESC
        """,
        tuple(params),
    )


def _filter_payment_proofs_for_period(
    payment_proofs: list[dict],
    invoices: list[dict],
    *,
    period_start: str | None,
    period_end: str | None,
) -> list[dict]:
    invoice_ids = {int(invoice["id"]) for invoice in invoices}
    filtered: list[dict] = []
    for proof in payment_proofs:
        invoice_id = proof.get("invoice_id")
        if invoice_id is not None and int(invoice_id) in invoice_ids:
            filtered.append(proof)
            continue
        created_at = str(proof.get("created_at") or "")
        created_date = created_at[:10] if len(created_at) >= 10 else None
        if period_start and created_date and created_date < period_start:
            continue
        if period_end and created_date and created_date > period_end:
            continue
        filtered.append(proof)
    return filtered


def _build_provision_section(business_id: int, month: str | None) -> dict | None:
    if month is None:
        return None
    engine = ProvisionEngine()
    try:
        breakdown = engine.get_aging(business_id, month)
    except LookupError:
        return None
    total_outstanding = round(sum(float(bucket["amount"]) for bucket in breakdown), 2)
    provision_amount = round(sum(float(bucket["provision"]) for bucket in breakdown), 2)
    return {
        "month": month,
        "total_outstanding": total_outstanding,
        "provision_amount": provision_amount,
        "breakdown": breakdown,
    }


def _build_summary(
    *,
    invoices: list[dict],
    payments: list[dict],
    payment_proofs: list[dict],
    reminders: list[dict],
    provider_callbacks: list[dict],
    as_of_date: str | None,
) -> dict:
    resolved_as_of = as_of_date or datetime.now(timezone.utc).date().isoformat()
    paid_count = 0
    pending_count = 0
    overdue_count = 0
    pending_total = 0.0
    overdue_total = 0.0
    for invoice in invoices:
        outstanding = float(invoice.get("outstanding_amount") or 0.0)
        due_date = invoice.get("due_date")
        if outstanding <= 0.0 or invoice.get("payment_status") == "paid":
            paid_count += 1
        else:
            pending_count += 1
            pending_total += outstanding
            if due_date and due_date < resolved_as_of:
                overdue_count += 1
                overdue_total += outstanding
    callback_issue_count = sum(1 for row in provider_callbacks if row["processing_status"] in CALLBACK_ISSUE_STATUSES)
    return {
        "invoice_total": round(sum(float(invoice["total"]) for invoice in invoices), 2),
        "paid_total": round(sum(float(payment["amount"]) for payment in payments), 2),
        "pending_total": round(pending_total, 2),
        "overdue_total": round(overdue_total, 2),
        "invoice_count": len(invoices),
        "paid_count": paid_count,
        "pending_count": pending_count,
        "overdue_count": overdue_count,
        "proof_needs_review_count": sum(1 for proof in payment_proofs if proof["review_state"] == "needs_review"),
        "reminder_failed_count": sum(1 for reminder in reminders if reminder["status"] == "failed"),
        "callback_issue_count": callback_issue_count,
    }


def _build_risk_flags(
    *,
    business_id: int,
    invoices: list[dict],
    payment_proofs: list[dict],
    reminders: list[dict],
    daily_closes: list[dict],
    provider_callbacks: list[dict],
    month: str | None,
    as_of_date: str | None,
) -> list[dict]:
    flags: list[dict] = []
    pending_proofs = [proof for proof in payment_proofs if proof["review_state"] == "needs_review"]
    rejected_proofs = [proof for proof in payment_proofs if proof["review_state"] == "rejected"]
    failed_reminders = [reminder for reminder in reminders if reminder["status"] == "failed"]
    overdue_invoices = [invoice for invoice in invoices if invoice.get("is_overdue")]
    invalid_callbacks = [row for row in provider_callbacks if row["processing_status"] == "invalid_signature"]
    duplicate_callbacks = [row for row in provider_callbacks if row["processing_status"] == "duplicate_event"]
    duplicate_payment_references = _find_duplicate_payment_references(business_id)
    amount_mismatches = _find_proof_amount_mismatches(business_id, payment_proofs)

    _append_flag(flags, "pending_payment_proofs", pending_proofs, "medium")
    _append_flag(flags, "rejected_payment_proofs", rejected_proofs, "medium")
    _append_flag(flags, "failed_reminders", failed_reminders, "medium")
    _append_flag(flags, "unpaid_overdue_invoices", overdue_invoices, "high")
    _append_flag(flags, "invalid_callback_signatures", invalid_callbacks, "high")
    _append_flag(flags, "duplicate_callback_events", duplicate_callbacks, "medium")
    _append_flag(flags, "duplicate_payment_references", duplicate_payment_references, "medium")
    _append_flag(flags, "proof_payment_amount_mismatches", amount_mismatches, "medium")

    if month:
        missing_days = _find_missing_daily_closes(month, as_of_date, daily_closes)
        _append_flag(flags, "missing_daily_closes", missing_days, "medium")
    return flags


def _append_flag(flags: list[dict], flag_type: str, items: list[dict], severity: str) -> None:
    if not items:
        return
    flags.append(
        {
            "type": flag_type,
            "severity": severity,
            "count": len(items),
            "items": items,
        }
    )


def _find_duplicate_payment_references(business_id: int) -> list[dict]:
    return _fetch_rows(
        """
        SELECT
            p.reference,
            COUNT(*) AS duplicate_count
        FROM payments p
        JOIN invoices i ON i.id = p.invoice_id
        WHERE i.business_id = ? AND p.reference IS NOT NULL AND p.reference != ''
        GROUP BY p.reference
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC, p.reference ASC
        """,
        (business_id,),
    )


def _find_proof_amount_mismatches(business_id: int, payment_proofs: list[dict]) -> list[dict]:
    invoice_ids = [proof["invoice_id"] for proof in payment_proofs if proof.get("invoice_id") is not None and proof.get("extracted_amount") is not None]
    if not invoice_ids:
        return []
    placeholders = ",".join("?" for _ in invoice_ids)
    rows = _fetch_rows(
        f"""
        SELECT
            pp.id AS payment_proof_id,
            pp.invoice_id,
            i.invoice_number,
            pp.extracted_amount,
            i.total AS invoice_total
        FROM payment_proofs pp
        JOIN invoices i ON i.id = pp.invoice_id
        WHERE pp.business_id = ?
          AND pp.invoice_id IN ({placeholders})
          AND pp.extracted_amount IS NOT NULL
          AND ABS(pp.extracted_amount - i.total) >= 0.01
        ORDER BY pp.id DESC
        """,
        (business_id, *invoice_ids),
    )
    return rows


def _find_missing_daily_closes(month: str, as_of_date: str | None, daily_closes: list[dict]) -> list[dict]:
    month_start = datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
    last_day = monthrange(month_start.year, month_start.month)[1]
    month_end = month_start.replace(day=last_day)
    if as_of_date:
        resolved_as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        if resolved_as_of.year == month_start.year and resolved_as_of.month == month_start.month and resolved_as_of < month_end:
            month_end = resolved_as_of
    existing = {row["date"] for row in daily_closes}
    missing: list[dict] = []
    cursor = month_start
    while cursor <= month_end:
        iso = cursor.isoformat()
        if iso not in existing:
            missing.append({"date": iso})
        cursor = cursor.fromordinal(cursor.toordinal() + 1)
    return missing


def _resolve_period(month: str | None, as_of_date: str | None) -> tuple[str | None, str | None, str | None, str | None]:
    resolved_month = None
    period_start = None
    period_end = None
    resolved_as_of = None
    if month:
        month_dt = datetime.strptime(month, "%Y-%m")
        resolved_month = month_dt.strftime("%Y-%m")
        period_start = f"{resolved_month}-01"
        period_end = f"{resolved_month}-{monthrange(month_dt.year, month_dt.month)[1]:02d}"
    if as_of_date:
        resolved_as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date().isoformat()
        if resolved_month is None:
            resolved_month = resolved_as_of[:7]
            period_end = resolved_as_of
        elif period_end and resolved_as_of < period_end:
            period_end = resolved_as_of
    if resolved_month is None:
        today = datetime.now(timezone.utc).date()
        resolved_month = today.strftime("%Y-%m")
        period_start = f"{resolved_month}-01"
        period_end = today.isoformat()
        resolved_as_of = today.isoformat()
    return resolved_month, period_start, period_end, resolved_as_of


def _rows_to_csv(fieldnames: list[str], rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in fieldnames})
    return output.getvalue()
