from pydantic import BaseModel, ConfigDict, Field


class PaymentProofResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    invoice_id: int | None = None
    invoice_number: str | None = None
    uploaded_by_user_id: int | None = None
    approved_payment_id: int | None = None
    source_channel: str
    file_path: str
    file_hash: str
    mime_type: str
    file_size_bytes: int
    ocr_status: str
    ocr_error: str | None = None
    ocr_payload: dict | None = None
    extracted_amount: float | None = None
    extracted_reference: str | None = None
    extracted_paid_at: str | None = None
    confidence_score: float | None = None
    review_state: str
    decision_reason: str | None = None
    created_at: str
    reviewed_at: str | None = None


class PaymentProofEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_proof_id: int
    actor_user_id: int | None = None
    event_type: str
    event_payload: dict | None = None
    created_at: str


class PaymentProofDetailResponse(BaseModel):
    proof: PaymentProofResponse
    events: list[PaymentProofEventResponse]


class PaymentProofApproveRequest(BaseModel):
    invoice_id: int | None = Field(default=None, ge=1)
    amount: float | None = Field(default=None, gt=0)
    reference: str | None = Field(default=None, max_length=100)
    method: str = Field(default="transfer", min_length=2, max_length=30)
    decision_reason: str | None = Field(default=None, max_length=240)


class PaymentProofRejectRequest(BaseModel):
    decision_reason: str = Field(min_length=1, max_length=240)
