import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from app.schemas.invoice import (
    InvoiceCreate,
    InvoicePaymentCreate,
    InvoiceResponse,
    InvoiceUpdate,
)
from app.services.exports import export_invoices
from app.services.invoices import create_invoice, get_invoice, list_invoices, record_invoice_payment, update_invoice


router = APIRouter()


@router.get("/invoices", response_model=list[InvoiceResponse])
def list_invoices_route() -> list[dict]:
    return list_invoices()


@router.get("/invoices/export")
def export_invoices_route(
    business_id: int = Query(default=1, ge=1),
    format: str = Query(default="csv"),
):
    export_format = format.lower()
    if export_format not in {"csv", "json"}:
        raise HTTPException(status_code=422, detail="format must be csv or json")
    content = export_invoices(business_id, export_format)
    if export_format == "json":
        return JSONResponse(content=json.loads(content))
    return PlainTextResponse(content=content, media_type="text/csv")


@router.post("/invoices", response_model=InvoiceResponse)
def create_invoice_route(payload: InvoiceCreate) -> dict:
    try:
        return create_invoice(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice_route(invoice_id: int) -> dict:
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.patch("/invoices/{invoice_id}", response_model=InvoiceResponse)
def update_invoice_route(invoice_id: int, payload: InvoiceUpdate) -> dict:
    try:
        invoice = update_invoice(invoice_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/invoices/{invoice_id}/payment", response_model=InvoiceResponse)
def record_payment_route(invoice_id: int, payload: InvoicePaymentCreate) -> dict:
    invoice = record_invoice_payment(invoice_id, payload.model_dump())
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice
