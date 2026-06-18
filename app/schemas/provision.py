from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str
    message: str
    code: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody


class ProvisionPolicyUpdateRequest(BaseModel):
    business_id: int = Field(ge=1)
    policy: dict[str, float]


class AgingBucketResponse(BaseModel):
    bucket: str
    label: str
    count: int
    amount: float
    rate: float
    provision: float


class AgingReportResponse(BaseModel):
    month: str
    as_of: str
    total_outstanding: float
    buckets: list[AgingBucketResponse]
    total_provision: float


class JournalEntryLineResponse(BaseModel):
    account: str
    account_code: str
    debit: float
    credit: float
    type: str


class JournalEntryResponse(BaseModel):
    date: str
    description: str
    reference: str
    entries: list[JournalEntryLineResponse]
    balanced: bool
    total_debit: float
    total_credit: float


class ProvisionCalculateResponse(BaseModel):
    month: str
    total_outstanding: float
    provision_amount: float
    breakdown: list[AgingBucketResponse]
    policy_used: dict[str, float]
    journal_entry: JournalEntryResponse
    justification: str
    calculated_at: str
