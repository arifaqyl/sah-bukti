from pydantic import BaseModel, ConfigDict, Field


class InvoiceCreate(BaseModel):
    business_id: int | None = Field(default=None, ge=1)
    customer_id: int = Field(ge=1)
    invoice_number: str = Field(min_length=1, max_length=50)
    items: list[dict] = Field(default_factory=list)
    subtotal: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)
    total: float = Field(gt=0)
    payment_method: str = Field(default="pending", min_length=2, max_length=30)
    payment_status: str = Field(default="pending", min_length=3, max_length=30)
    due_date: str | None = None


class InvoiceUpdate(BaseModel):
    customer_id: int | None = Field(default=None, ge=1)
    invoice_number: str | None = Field(default=None, min_length=1, max_length=50)
    items: list[dict] | None = None
    subtotal: float | None = Field(default=None, ge=0)
    tax: float | None = Field(default=None, ge=0)
    total: float | None = Field(default=None, gt=0)
    payment_method: str | None = Field(default=None, min_length=2, max_length=30)
    payment_status: str | None = Field(default=None, min_length=3, max_length=30)
    due_date: str | None = None


class InvoicePaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    method: str = Field(min_length=2, max_length=30)
    reference: str | None = Field(default=None, max_length=100)
    confirmed: bool = True


class InvoiceResponse(InvoiceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paid_at: str | None = None
    created_at: str
    updated_at: str
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    pending_proof_count: int = 0


class PaymentLinkResponse(BaseModel):
    invoice_id: int
    provider: str
    payment_link_url: str | None = None
    invoice_number: str
    amount: float
    whatsapp_text: str
    instructions: str | None = None


class PaymentWebhookResponse(BaseModel):
    ok: bool
    invoice_id: int | None = None
    status: str


class DailyCloseCreate(BaseModel):
    business_id: int | None = Field(default=None, ge=1)
    date: str = Field(min_length=1, max_length=20)
    total_cash: float = Field(default=0, ge=0)
    total_qr: float = Field(default=0, ge=0)
    total_transfer: float = Field(default=0, ge=0)
    total_orders: int = Field(default=0, ge=0)
    total_revenue: float = Field(default=0, ge=0)


class DailyCloseResponse(DailyCloseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: str
