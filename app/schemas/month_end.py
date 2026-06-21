from pydantic import BaseModel


class MonthEndSummaryResponse(BaseModel):
    invoice_total: float
    paid_total: float
    pending_total: float
    overdue_total: float
    provision_amount: float
    pending_proof_count: int
    failed_reminder_count: int
    callback_issue_count: int
    missing_daily_close_count: int


class MonthEndProvisionResponse(BaseModel):
    total_outstanding: float
    provision_amount: float
    breakdown: list[dict]
    journal_entry: dict | None = None
    justification: str


class MonthEndBlockerResponse(BaseModel):
    type: str
    severity: str
    title: str
    message: str
    count: int
    items: list[dict]


class MonthEndActionResponse(BaseModel):
    priority: int
    title: str
    action: str
    endpoint: str
    method: str
    payload: dict | None = None


class MonthEndDataQualityResponse(BaseModel):
    missing_customer_phone_count: int
    missing_due_date_count: int
    pending_payment_method_count: int
    proof_without_invoice_count: int
    callback_issue_count: int


class MonthEndAccountantExportResponse(BaseModel):
    endpoint: str
    params: dict


class MonthEndReadinessResponse(BaseModel):
    business_id: int
    month: str
    as_of_date: str | None = None
    generated_at: str
    readiness_status: str
    readiness_score: int
    summary: MonthEndSummaryResponse
    provision: MonthEndProvisionResponse
    blockers: list[MonthEndBlockerResponse]
    action_plan: list[MonthEndActionResponse]
    data_quality: MonthEndDataQualityResponse
    accountant_export: MonthEndAccountantExportResponse
