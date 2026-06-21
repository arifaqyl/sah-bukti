from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import BusinessContext, get_business_context
from app.schemas.parser import ParseOrderRequest, ParseOrderResponse
from app.services.parser import parse_order


router = APIRouter()


@router.post("/parse-order", response_model=ParseOrderResponse)
def parse_order_route(payload: ParseOrderRequest, ctx: BusinessContext = Depends(get_business_context)) -> dict:
    if payload.business_id is not None and payload.business_id != ctx.business_id:
        raise HTTPException(status_code=403, detail="Business access denied")
    return parse_order(payload.text, ctx.business_id)
