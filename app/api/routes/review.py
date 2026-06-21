from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import BusinessContext, get_business_context, get_business_context_demo
from app.schemas.review import (
    PaymentProofAuditResponse,
    PaymentProofReviewQueueResponse,
    ProviderCallbackAuditResponse,
    ReminderAuditResponse,
    ReminderReviewQueueResponse,
)
from app.services.payment_proofs import get_payment_proof, list_payment_proof_events, list_payment_proofs
from app.services.payment_proofs import (
    PaymentProofNotFoundError,
    approve_payment_proof,
    edit_payment_proof,
    reject_payment_proof,
    undo_payment_proof_approval,
)
from app.services.payments import list_provider_callback_events
from app.services.reminders import get_reminder, list_reminder_events, list_reminders


router = APIRouter()


@router.get("/review/payment-proofs", response_model=list[PaymentProofReviewQueueResponse])
def review_payment_proofs_route(
    review_state: str | None = Query(default="needs_review"),
    invoice_number: str | None = Query(default=None),
    source_channel: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> list[dict]:
    return list_payment_proofs(
        ctx.business_id,
        review_state=review_state,
        invoice_number=invoice_number,
        source_channel=source_channel,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/review/reminders", response_model=list[ReminderReviewQueueResponse])
def review_reminders_route(
    status: str | None = Query(default=None),
    invoice_number: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> list[dict]:
    return list_reminders(
        ctx.business_id,
        status=status,
        invoice_number=invoice_number,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("/review/{proof_id}/approve")
def approve_review_payment_proof_route(
    proof_id: int,
    payload: dict | None = None,
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> dict:
    payload = payload or {}
    try:
        return approve_payment_proof(
            proof_id=proof_id,
            business_id=ctx.business_id,
            reviewer_user_id=ctx.user["id"],
            invoice_id=payload.get("invoice_id"),
            amount=payload.get("amount"),
            reference=payload.get("reference"),
            method=payload.get("method") or "transfer",
            decision_reason=payload.get("decision_reason") or "approved_from_review_queue",
        )
    except PaymentProofNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/review/{proof_id}/reject")
def reject_review_payment_proof_route(
    proof_id: int,
    payload: dict | None = None,
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> dict:
    payload = payload or {}
    try:
        return reject_payment_proof(
            proof_id=proof_id,
            business_id=ctx.business_id,
            reviewer_user_id=ctx.user["id"],
            decision_reason=payload.get("decision_reason") or "rejected_from_review_queue",
        )
    except PaymentProofNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/review/{proof_id}")
def edit_review_payment_proof_route(
    proof_id: int,
    payload: dict | None = None,
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> dict:
    payload = payload or {}
    try:
        return edit_payment_proof(
            proof_id=proof_id,
            business_id=ctx.business_id,
            reviewer_user_id=ctx.user["id"],
            amount=payload.get("amount"),
            reference=payload.get("reference"),
            method=payload.get("method"),
            decision_reason=payload.get("decision_reason") or "edited_from_review_queue",
        )
    except PaymentProofNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/review/{proof_id}/undo")
def undo_review_payment_proof_route(
    proof_id: int,
    payload: dict | None = None,
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> dict:
    payload = payload or {}
    try:
        return undo_payment_proof_approval(
            proof_id=proof_id,
            business_id=ctx.business_id,
            reviewer_user_id=ctx.user["id"],
            decision_reason=payload.get("decision_reason") or "undone_from_review_queue",
        )
    except PaymentProofNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/audit/payment-proofs/{proof_id}", response_model=PaymentProofAuditResponse)
def audit_payment_proof_route(proof_id: int, ctx: BusinessContext = Depends(get_business_context)) -> dict:
    proof = get_payment_proof(proof_id, ctx.business_id)
    if not proof:
        raise HTTPException(status_code=404, detail="Payment proof not found")
    return {
        "proof": proof,
        "events": list_payment_proof_events(proof_id, ctx.business_id),
    }


@router.get("/audit/reminders/{reminder_id}", response_model=ReminderAuditResponse)
def audit_reminder_route(reminder_id: int, ctx: BusinessContext = Depends(get_business_context)) -> dict:
    reminder = get_reminder(reminder_id, ctx.business_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {
        "reminder": reminder,
        "events": list_reminder_events(reminder_id, ctx.business_id),
    }


@router.get("/audit/callbacks", response_model=list[ProviderCallbackAuditResponse])
def audit_callbacks_route(
    status: str | None = Query(default=None),
    invoice_number: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    ctx: BusinessContext = Depends(get_business_context),
) -> list[dict]:
    return list_provider_callback_events(
        ctx.business_id,
        status=status,
        invoice_number=invoice_number,
        date_from=date_from,
        date_to=date_to,
    )
