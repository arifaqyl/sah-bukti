from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import BusinessContext, get_business_context_demo
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services.customers import create_customer, delete_customer, list_customers, update_customer


router = APIRouter()


@router.post("", response_model=CustomerResponse)
def create_customer_route(payload: CustomerCreate, ctx: BusinessContext = Depends(get_business_context_demo)) -> dict:
    if payload.business_id is not None and payload.business_id != ctx.business_id:
        raise HTTPException(status_code=403, detail="Business access denied")
    data = payload.model_dump()
    data["business_id"] = ctx.business_id
    return create_customer(data)


@router.get("", response_model=list[CustomerResponse])
def list_customers_route(ctx: BusinessContext = Depends(get_business_context_demo)) -> list[dict]:
    return list_customers(ctx.business_id)


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer_route(
    customer_id: int,
    payload: CustomerUpdate,
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> dict:
    row = update_customer(customer_id, payload.model_dump(exclude_unset=True), ctx.business_id)
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")
    return row


@router.delete("/{customer_id}", status_code=204)
def delete_customer_route(customer_id: int, ctx: BusinessContext = Depends(get_business_context_demo)) -> None:
    try:
        deleted = delete_customer(customer_id, ctx.business_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
