from pydantic import BaseModel


class WhatsAppIngestRequest(BaseModel):
    raw_text: str


class WhatsAppIngestResponse(BaseModel):
    extracted_name: str | None = None
    extracted_amount: float | None = None
    extracted_due_date: str | None = None
    extracted_item: str | None = None
    summary: str
