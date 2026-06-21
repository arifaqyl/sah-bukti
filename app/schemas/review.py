from pydantic import BaseModel, ConfigDict

from app.schemas.payment_proof import PaymentProofDetailResponse, PaymentProofResponse
from app.schemas.reminder import ReminderDetailResponse, ReminderResponse


class ProviderCallbackAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    event_key: str
    invoice_number: str | None = None
    transaction_id: str | None = None
    payload_json: dict | None = None
    payload_hash: str
    signature_valid: int
    processing_status: str
    processed_invoice_id: int | None = None
    created_at: str
    processed_at: str | None = None


class PaymentProofAuditResponse(PaymentProofDetailResponse):
    pass


class ReminderAuditResponse(ReminderDetailResponse):
    pass


class PaymentProofReviewQueueResponse(PaymentProofResponse):
    pass


class ReminderReviewQueueResponse(ReminderResponse):
    pass
