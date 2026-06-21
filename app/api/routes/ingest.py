from fastapi import APIRouter, HTTPException

from app.schemas.ingest import WhatsAppIngestRequest, WhatsAppIngestResponse


router = APIRouter()


@router.post("/ingest/whatsapp", response_model=WhatsAppIngestResponse)
def ingest_whatsapp_route(payload: WhatsAppIngestRequest) -> dict:  # noqa: ARG001
    raise HTTPException(
        status_code=410,
        detail="Deprecated ingest route. Use /api/v1/evidence/whatsapp so evidence stays reviewable.",
    )
