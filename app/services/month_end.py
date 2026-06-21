from __future__ import annotations

from datetime import datetime

from app.services.exports import export_accountant_package
from app.services.provision import ProvisionEngine


SEVERITY_DEDUCTIONS = {
    "high": 20,
    "medium": 8,
    "low": 3,
}

BLOCKER_META = {
    "pending_payment_proofs": {
        "severity": "medium",
        "title": "Pending payment proofs",
        "message": "Review payment proofs before month-end handoff.",
        "endpoint": "/api/v1/review/payment-proofs",
        "method": "GET",
        "payload": None,
        "priority": 1,
    },
    "rejected_payment_proofs": {
        "severity": "medium",
        "title": "Rejected payment proofs",
        "message": "Resolve or document rejected payment evidence before handoff.",
        "endpoint": "/api/v1/review/payment-proofs",
        "method": "GET",
        "payload": None,
        "priority": 2,
    },
    "failed_reminders": {
        "severity": "medium",
        "title": "Failed reminders",
        "message": "Inspect reminder failures and retry if collection follow-up is still required.",
        "endpoint": "/api/v1/review/reminders",
        "method": "GET",
        "payload": None,
        "priority": 3,
    },
    "unpaid_overdue_invoices": {
        "severity": "high",
        "title": "Unpaid overdue invoices",
        "message": "Outstanding overdue invoices still need collection or write-off decisions.",
        "endpoint": "/api/v1/invoices",
        "method": "GET",
        "payload": None,
        "priority": 4,
    },
    "invalid_callback_signatures": {
        "severity": "high",
        "title": "Invalid payment callbacks",
        "message": "Provider callback signature failures must be reviewed before trusting payment events.",
        "endpoint": "/api/v1/audit/callbacks",
        "method": "GET",
        "payload": None,
        "priority": 5,
    },
    "duplicate_callback_events": {
        "severity": "medium",
        "title": "Duplicate callback events",
        "message": "Duplicate provider callbacks should be reviewed for reconciliation confidence.",
        "endpoint": "/api/v1/audit/callbacks",
        "method": "GET",
        "payload": None,
        "priority": 6,
    },
    "missing_daily_closes": {
        "severity": "medium",
        "title": "Missing daily closes",
        "message": "Some days in the month do not have a daily close record.",
        "endpoint": "/api/v1/daily-close",
        "method": "POST",
        "payload": None,
        "priority": 7,
    },
    "proof_payment_amount_mismatches": {
        "severity": "medium",
        "title": "Proof and invoice amount mismatches",
        "message": "Payment proof amounts do not match invoice totals and need review.",
        "endpoint": "/api/v1/review/payment-proofs",
        "method": "GET",
        "payload": None,
        "priority": 8,
    },
    "duplicate_payment_references": {
        "severity": "medium",
        "title": "Duplicate payment references",
        "message": "Duplicate payment references were detected and should be reconciled.",
        "endpoint": "/api/v1/payment-proofs/upload",
        "method": "GET",
        "payload": None,
        "priority": 9,
    },
}


def get_month_end_readiness(
    *,
    business_id: int,
    month: str,
    as_of_date: str | None = None,
    include_proof_payloads: bool = False,
) -> dict:
    package = export_accountant_package(
        business_id=business_id,
        month=month,
        as_of_date=as_of_date,
        include_proof_payloads=include_proof_payloads,
    )
    provision = _build_provision_section(business_id, month)
    blockers = _build_blockers(package["risk_flags"])
    data_quality = _build_data_quality(package)
    action_plan = _build_action_plan(blockers, data_quality, provision is None, month)
    score = max(0, 100 - sum(SEVERITY_DEDUCTIONS[blocker["severity"]] for blocker in blockers))
    has_high_blocker = any(blocker["severity"] == "high" for blocker in blockers)
    if score < 60 or has_high_blocker:
        readiness_status = "blocked"
    elif score >= 90:
        readiness_status = "ready"
    else:
        readiness_status = "needs_attention"

    summary = {
        "invoice_total": package["summary"]["invoice_total"],
        "paid_total": package["summary"]["paid_total"],
        "pending_total": package["summary"]["pending_total"],
        "overdue_total": package["summary"]["overdue_total"],
        "provision_amount": provision["provision_amount"] if provision else 0.0,
        "pending_proof_count": package["summary"]["proof_needs_review_count"],
        "failed_reminder_count": package["summary"]["reminder_failed_count"],
        "callback_issue_count": package["summary"]["callback_issue_count"],
        "missing_daily_close_count": _count_flag_items(package["risk_flags"], "missing_daily_closes"),
    }
    return {
        "business_id": business_id,
        "month": month,
        "as_of_date": as_of_date,
        "generated_at": package["generated_at"],
        "readiness_status": readiness_status,
        "readiness_score": score,
        "summary": summary,
        "provision": provision
        or {
            "total_outstanding": 0.0,
            "provision_amount": 0.0,
            "breakdown": [],
            "journal_entry": None,
            "justification": "No unpaid invoices found for this period.",
        },
        "blockers": blockers,
        "action_plan": action_plan,
        "data_quality": data_quality,
        "accountant_export": {
            "endpoint": "/api/v1/exports/accountant",
            "params": {
                "month": month,
                "include_proof_payloads": include_proof_payloads,
            },
        },
    }


def _build_provision_section(business_id: int, month: str) -> dict | None:
    engine = ProvisionEngine()
    try:
        result = engine.calculate(business_id, month)
    except LookupError:
        return None
    return {
        "total_outstanding": result["total_outstanding"],
        "provision_amount": result["provision_amount"],
        "breakdown": result["breakdown"],
        "journal_entry": result["journal_entry"],
        "justification": result["justification"],
    }


def _build_blockers(risk_flags: list[dict]) -> list[dict]:
    blockers: list[dict] = []
    for flag in risk_flags:
        meta = BLOCKER_META.get(flag["type"])
        if not meta:
            continue
        blockers.append(
            {
                "type": flag["type"],
                "severity": meta["severity"],
                "title": meta["title"],
                "message": meta["message"],
                "count": flag["count"],
                "items": flag["items"],
            }
        )
    return blockers


def _build_action_plan(
    blockers: list[dict],
    data_quality: dict,
    missing_provision: bool,
    month: str,
) -> list[dict]:
    actions: list[dict] = []
    seen_titles: set[str] = set()

    for blocker in sorted(blockers, key=lambda item: BLOCKER_META[item["type"]]["priority"]):
        meta = BLOCKER_META[blocker["type"]]
        if meta["title"] in seen_titles:
            continue
        payload = meta["payload"]
        if blocker["type"] == "missing_daily_closes" and blocker["items"]:
            payload = {
                "date": blocker["items"][0]["date"],
                "total_cash": 0.0,
                "total_qr": 0.0,
                "total_transfer": 0.0,
                "total_orders": 0,
                "total_revenue": 0.0,
            }
        actions.append(
            {
                "priority": len(actions) + 1,
                "title": meta["title"],
                "action": meta["message"],
                "endpoint": meta["endpoint"],
                "method": meta["method"],
                "payload": payload,
            }
        )
        seen_titles.add(meta["title"])

    _append_data_quality_action(
        actions,
        seen_titles,
        data_quality["missing_customer_phone_count"] > 0,
        "Missing customer phone numbers",
        "Update customer contact details so reminders and follow-up can be sent reliably.",
        "/api/v1/customers",
        "GET",
    )
    _append_data_quality_action(
        actions,
        seen_titles,
        data_quality["missing_due_date_count"] > 0,
        "Missing invoice due dates",
        "Add due dates to invoices so overdue tracking and provision logic stay reliable.",
        "/api/v1/invoices",
        "GET",
    )
    _append_data_quality_action(
        actions,
        seen_titles,
        data_quality["pending_payment_method_count"] > 0,
        "Pending payment methods",
        "Clean up invoices still marked with pending payment methods before handoff.",
        "/api/v1/invoices",
        "GET",
    )
    _append_data_quality_action(
        actions,
        seen_titles,
        data_quality["proof_without_invoice_count"] > 0,
        "Proofs without invoices",
        "Link unmatched payment proofs to the correct invoice before handoff.",
        "/api/v1/review/payment-proofs",
        "GET",
    )
    _append_data_quality_action(
        actions,
        seen_titles,
        missing_provision,
        "No provision data",
        "Run provision calculation for the month before accountant handoff.",
        "/api/v1/provision/calculate",
        "GET",
        {"month": month},
    )
    return actions


def _append_data_quality_action(
    actions: list[dict],
    seen_titles: set[str],
    should_add: bool,
    title: str,
    action: str,
    endpoint: str,
    method: str,
    payload: dict | None = None,
) -> None:
    if not should_add or title in seen_titles:
        return
    actions.append(
        {
            "priority": len(actions) + 1,
            "title": title,
            "action": action,
            "endpoint": endpoint,
            "method": method,
            "payload": payload,
        }
    )
    seen_titles.add(title)


def _build_data_quality(package: dict) -> dict:
    invoices = package["invoices"]
    proofs = package["payment_proofs"]
    return {
        "missing_customer_phone_count": sum(1 for invoice in invoices if not invoice.get("customer_phone")),
        "missing_due_date_count": sum(1 for invoice in invoices if not invoice.get("due_date")),
        "pending_payment_method_count": sum(1 for invoice in invoices if invoice.get("payment_method") == "pending"),
        "proof_without_invoice_count": sum(1 for proof in proofs if proof.get("invoice_id") is None),
        "callback_issue_count": package["summary"]["callback_issue_count"],
    }


def _count_flag_items(risk_flags: list[dict], flag_type: str) -> int:
    for flag in risk_flags:
        if flag["type"] == flag_type:
            return int(flag["count"])
    return 0
