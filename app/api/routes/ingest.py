from fastapi import APIRouter

from app.schemas.ingest import WhatsAppIngestRequest, WhatsAppIngestResponse
from app.services.ingest import ingest_whatsapp


router = APIRouter()


@router.post("/ingest/whatsapp", response_model=WhatsAppIngestResponse)
def ingest_whatsapp_route(payload: WhatsAppIngestRequest) -> dict:
    return ingest_whatsapp(payload.raw_text)
