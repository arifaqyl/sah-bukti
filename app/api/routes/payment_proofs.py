from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import BusinessContext, get_business_context
from app.schemas.payment_proof import (
    PaymentProofApproveRequest,
    PaymentProofDetailResponse,
    PaymentProofRejectRequest,
    PaymentProofResponse,
)
from app.services.payment_proofs import (
    PaymentProofConflictError,
    PaymentProofNotFoundError,
    approve_payment_proof,
    create_payment_proof,
    get_payment_proof,
    list_payment_proof_events,
    list_payment_proofs,
    reject_payment_proof,
)


router = APIRouter()


@router.post("/payment-proofs/upload", response_model=PaymentProofResponse, status_code=status.HTTP_201_CREATED)
async def upload_payment_proof_route(
    file: UploadFile = File(...),
    invoice_id: int | None = Form(default=None),
    source_channel: str = Form(default="dashboard"),
    ctx: BusinessContext = Depends(get_business_context),
) -> dict:
    try:
        return create_payment_proof(
            business_id=ctx.business_id,
            uploaded_by_user_id=ctx.user["id"],
            file_bytes=await file.read(),
            original_filename=file.filename or "proof.png",
            content_type=file.content_type,
            invoice_id=invoice_id,
            source_channel=source_channel,
        )
    except PaymentProofConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PaymentProofNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/payment-proofs", response_model=list[PaymentProofResponse])
def list_payment_proofs_route(ctx: BusinessContext = Depends(get_business_context)) -> list[dict]:
    return list_payment_proofs(ctx.business_id)


@router.get("/payment-proofs/{proof_id}", response_model=PaymentProofDetailResponse)
def get_payment_proof_route(proof_id: int, ctx: BusinessContext = Depends(get_business_context)) -> dict:
    proof = get_payment_proof(proof_id, ctx.business_id)
    if not proof:
        raise HTTPException(status_code=404, detail="Payment proof not found")
    return {
        "proof": proof,
        "events": list_payment_proof_events(proof_id, ctx.business_id),
    }


@router.post("/payment-proofs/{proof_id}/approve", response_model=PaymentProofResponse)
def approve_payment_proof_route(
    proof_id: int,
    payload: PaymentProofApproveRequest,
    ctx: BusinessContext = Depends(get_business_context),
) -> dict:
    try:
        return approve_payment_proof(
            proof_id=proof_id,
            business_id=ctx.business_id,
            reviewer_user_id=ctx.user["id"],
            invoice_id=payload.invoice_id,
            amount=payload.amount,
            reference=payload.reference,
            method=payload.method,
            decision_reason=payload.decision_reason,
        )
    except PaymentProofNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/payment-proofs/{proof_id}/reject", response_model=PaymentProofResponse)
def reject_payment_proof_route(
    proof_id: int,
    payload: PaymentProofRejectRequest,
    ctx: BusinessContext = Depends(get_business_context),
) -> dict:
    try:
        return reject_payment_proof(
            proof_id=proof_id,
            business_id=ctx.business_id,
            reviewer_user_id=ctx.user["id"],
            decision_reason=payload.decision_reason,
        )
    except PaymentProofNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
