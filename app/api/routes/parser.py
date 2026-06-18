from fastapi import APIRouter

from app.schemas.parser import ParseOrderRequest, ParseOrderResponse
from app.services.parser import parse_order


router = APIRouter()


@router.post("/parse-order", response_model=ParseOrderResponse)
def parse_order_route(payload: ParseOrderRequest) -> dict:
    return parse_order(payload.text, payload.business_id)
