from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import BusinessContext, get_business_context_demo
from app.schemas.invoice import PaymentLinkResponse
from app.services.payments import create_payment_link


router = APIRouter()


@router.post("/invoices/{invoice_id}/payment-link", response_model=PaymentLinkResponse)
def create_payment_link_route(
    invoice_id: int,
    provider: str | None = Query(default=None),
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> dict:
    try:
        return create_payment_link(invoice_id, ctx.business_id, provider)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/billplz-webhook")
def disabled_billplz_webhook_route() -> dict:
    raise HTTPException(status_code=404, detail="Not Found")
