from pydantic import BaseModel, Field


class WhatsAppWebhookRequest(BaseModel):
    message: str = Field(min_length=1)
    from_phone: str = Field(alias="from", min_length=3)
    business_id: int = Field(ge=1)


class WhatsAppWebhookResponse(BaseModel):
    invoice_number: str
    total: float
    customer_name: str
