from pydantic import BaseModel, Field


class ParsedOrderItem(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)


class ParseOrderRequest(BaseModel):
    text: str = Field(min_length=1)
    business_id: int | None = Field(default=None, ge=1)


class ParseOrderResponse(BaseModel):
    customer_name: str | None = None
    items: list[ParsedOrderItem]
    total: float = Field(ge=0)
    payment_method: str
    source: str
