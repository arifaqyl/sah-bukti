from pydantic import BaseModel, ConfigDict, Field


class ReminderPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    name: str
    channel: str
    min_days_overdue: int
    cadence_days: int
    enabled: int
    template_text: str
    created_at: str
    updated_at: str


class ReminderPolicyUpsert(BaseModel):
    id: int | None = Field(default=None, ge=1)
    name: str = Field(min_length=1, max_length=120)
    channel: str = Field(default="mock", min_length=2, max_length=30)
    min_days_overdue: int = Field(default=1, ge=1, le=365)
    cadence_days: int = Field(default=3, ge=1, le=365)
    enabled: bool = True
    template_text: str = Field(min_length=1, max_length=500)


class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    invoice_id: int
    customer_id: int
    policy_id: int
    channel: str
    status: str
    days_overdue: int
    outstanding_amount: float
    message_text: str
    dedupe_key: str
    generated_for_date: str
    generated_at: str
    sent_at: str | None = None
    last_error: str | None = None
    invoice_number: str
    customer_name: str
    customer_phone: str | None = None
    policy_name: str


class ReminderEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reminder_id: int
    actor_user_id: int | None = None
    event_type: str
    event_payload: dict | None = None
    created_at: str


class ReminderDetailResponse(BaseModel):
    reminder: ReminderResponse
    events: list[ReminderEventResponse]


class ReminderGenerateRequest(BaseModel):
    as_of_date: str | None = Field(default=None, max_length=10)


class ReminderGenerateResponse(BaseModel):
    as_of_date: str
    generated_count: int
    suppressed_count: int
    reminders: list[ReminderResponse]
