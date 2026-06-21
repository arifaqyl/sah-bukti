from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import BusinessContext, get_business_context_demo
from app.schemas.month_end import MonthEndReadinessResponse
from app.services.month_end import get_month_end_readiness


router = APIRouter()


@router.get("/month-end/readiness", response_model=MonthEndReadinessResponse)
def month_end_readiness_route(
    month: str = Query(...),
    as_of_date: str | None = Query(default=None),
    include_proof_payloads: bool = Query(default=False),
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> dict:
    try:
        return get_month_end_readiness(
            business_id=ctx.business_id,
            month=month,
            as_of_date=as_of_date,
            include_proof_payloads=include_proof_payloads,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
