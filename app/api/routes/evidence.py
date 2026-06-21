from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import BusinessContext, get_business_context_demo
from app.schemas.evidence import (
    EvidenceImportRequest,
    EvidenceImportResponse,
    WhatsAppEvidenceRequest,
    WhatsAppEvidenceResponse,
)
from app.services.evidence import ingest_whatsapp_evidence
from app.services.evidence_import import ingest_evidence_import


router = APIRouter()


@router.post("/evidence/whatsapp", response_model=WhatsAppEvidenceResponse)
def evidence_whatsapp_route(
    payload: WhatsAppEvidenceRequest,
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> dict:
    if payload.business_id is not None and payload.business_id != ctx.business_id:
        raise HTTPException(status_code=403, detail="Business access denied")
    try:
        return ingest_whatsapp_evidence(
            business_id=ctx.business_id,
            from_phone=payload.from_phone,
            message=payload.message,
            transcript=payload.transcript,
            media_type=payload.media_type,
            media_metadata=payload.media_metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/evidence/import", response_model=EvidenceImportResponse)
def evidence_import_route(
    payload: EvidenceImportRequest,
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> dict:
    if payload.business_id is not None and payload.business_id != ctx.business_id:
        raise HTTPException(status_code=403, detail="Business access denied")
    try:
        return ingest_evidence_import(
            business_id=ctx.business_id,
            source_type=payload.source_type,
            raw_text=payload.raw_text,
            file_content=None,
            filename=payload.filename,
            mime_type=payload.mime_type,
            drive_url=payload.drive_url,
            media_metadata=payload.media_metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
