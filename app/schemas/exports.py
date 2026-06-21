from pydantic import BaseModel


class AccountantExportPeriod(BaseModel):
    month: str | None = None
    as_of_date: str | None = None


class AccountantExportSummary(BaseModel):
    invoice_total: float
    paid_total: float
    pending_total: float
    overdue_total: float
    invoice_count: int
    paid_count: int
    pending_count: int
    overdue_count: int
    proof_needs_review_count: int
    reminder_failed_count: int
    callback_issue_count: int


class AccountantExportResponse(BaseModel):
    business_id: int
    generated_at: str
    period: AccountantExportPeriod
    summary: AccountantExportSummary
    invoices: list[dict]
    payments: list[dict]
    payment_proofs: list[dict]
    reminders: list[dict]
    daily_closes: list[dict]
    provision: dict | None = None
    provider_callbacks: list[dict]
    risk_flags: list[dict]
