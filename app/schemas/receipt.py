from pydantic import BaseModel, ConfigDict


class ReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int | None = None
    filename: str
    bank_name: str | None = None
    amount: float | None = None
    reference_number: str | None = None
    transaction_time: str | None = None
    recipient_name: str | None = None
    status: str
    match_reason: str | None = None
    created_at: str


class ReceiptVerificationDetail(BaseModel):
    receipt: ReceiptResponse
    matched_invoice_number: str | None = None
    matched_customer_name: str | None = None
