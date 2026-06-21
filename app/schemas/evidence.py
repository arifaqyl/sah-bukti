from pydantic import BaseModel, Field

from app.schemas.invoice import InvoiceResponse
from app.schemas.payment_proof import PaymentProofResponse


class WhatsAppEvidenceRequest(BaseModel):
    business_id: int | None = Field(default=None, ge=1)
    from_phone: str = Field(min_length=3)
    message: str | None = Field(default=None)
    transcript: str | None = Field(default=None)
    media_type: str = Field(default="text", min_length=2, max_length=40)
    media_metadata: dict = Field(default_factory=dict)


class WhatsAppEvidenceResponse(BaseModel):
    business_id: int
    intent: str
    from_phone: str
    media_type: str
    normalized_text: str | None = None
    payment_proof: PaymentProofResponse | None = None
    invoice: InvoiceResponse | None = None
    parsed: dict | None = None
    message: str


class EvidenceImportRequest(BaseModel):
    business_id: int | None = Field(default=None, ge=1)
    source_type: str = Field(min_length=2, max_length=40)
    raw_text: str | None = None
    drive_url: str | None = None
    filename: str | None = None
    mime_type: str | None = None
    media_metadata: dict = Field(default_factory=dict)


class EvidenceImportFailure(BaseModel):
    row_number: int | None = None
    message: str


class EvidenceImportResponse(BaseModel):
    business_id: int
    source_type: str
    imported_count: int
    payment_proofs_created: int
    invoices_created: int
    needs_review_count: int
    failed_count: int
    failures: list[EvidenceImportFailure] = Field(default_factory=list)
