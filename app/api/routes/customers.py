from fastapi import APIRouter

from app.schemas.customer import CustomerCreate, CustomerResponse
from app.services.customers import create_customer, list_customers


router = APIRouter()


@router.post("", response_model=CustomerResponse)
def create_customer_route(payload: CustomerCreate) -> dict:
    return create_customer(payload.model_dump())


@router.get("", response_model=list[CustomerResponse])
def list_customers_route() -> list[dict]:
    return list_customers()
