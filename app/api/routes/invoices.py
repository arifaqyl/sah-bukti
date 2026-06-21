import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from app.api.dependencies import BusinessContext, get_business_context, get_business_context_demo
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceResponse,
    InvoiceUpdate,
)
from app.services.exports import export_invoices
from app.services.invoices import create_invoice, delete_invoice, get_invoice, list_invoices, update_invoice
from app.services.receipts import generate_receipt_pdf


router = APIRouter()


@router.get("/invoices", response_model=list[InvoiceResponse])
def list_invoices_route(ctx: BusinessContext = Depends(get_business_context_demo)) -> list[dict]:
    return list_invoices(ctx.business_id)


@router.get("/invoices/export")
def export_invoices_route(
    format: str = Query(default="csv"),
    ctx: BusinessContext = Depends(get_business_context_demo),
):
    export_format = format.lower()
    if export_format not in {"csv", "json"}:
        raise HTTPException(status_code=422, detail="format must be csv or json")
    content = export_invoices(ctx.business_id, export_format)
    if export_format == "json":
        return JSONResponse(content=json.loads(content))
    return PlainTextResponse(content=content, media_type="text/csv")


@router.post("/invoices", response_model=InvoiceResponse)
def create_invoice_route(payload: InvoiceCreate, ctx: BusinessContext = Depends(get_business_context_demo)) -> dict:
    try:
        if payload.business_id is not None and payload.business_id != ctx.business_id:
            raise HTTPException(status_code=403, detail="Business access denied")
        data = payload.model_dump()
        data["business_id"] = ctx.business_id
        return create_invoice(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice_route(invoice_id: int, ctx: BusinessContext = Depends(get_business_context_demo)) -> dict:
    invoice = get_invoice(invoice_id, ctx.business_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.patch("/invoices/{invoice_id}", response_model=InvoiceResponse)
def update_invoice_route(
    invoice_id: int,
    payload: InvoiceUpdate,
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> dict:
    try:
        invoice = update_invoice(invoice_id, payload.model_dump(exclude_unset=True), ctx.business_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.delete("/invoices/{invoice_id}", status_code=204)
def delete_invoice_route(invoice_id: int, ctx: BusinessContext = Depends(get_business_context_demo)) -> None:
    try:
        deleted = delete_invoice(invoice_id, ctx.business_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Invoice not found")


@router.get("/invoices/{invoice_id}/receipt")
def download_invoice_receipt_route(
    invoice_id: int,
    ctx: BusinessContext = Depends(get_business_context_demo),
):
    invoice = get_invoice(invoice_id, ctx.business_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    items = []
    for item in invoice.get("items") or []:
        qty = float(item.get("quantity") or item.get("qty") or 0)
        price = float(item.get("unit_price") or item.get("price") or 0)
        items.append(
            {
                "name": item.get("name") or "Item",
                "qty": qty,
                "price": price,
            }
        )

    payment_status = str(invoice.get("payment_status") or "pending")
    payment_method = str(invoice.get("payment_method") or "pending")
    if payment_status == "paid":
        payment_info = f"Pembayaran disahkan: {payment_method}"
    elif payment_status == "partial":
        payment_info = f"Pembayaran separa direkodkan: {payment_method}"
    else:
        payment_info = "Status pembayaran: Menunggu semakan / kelulusan"

    path = generate_receipt_pdf(
        {
            "business_id": ctx.business_id,
            "invoice_id": invoice["id"],
            "order_id": invoice["invoice_number"],
            "date": (invoice.get("created_at") or "")[:10],
            "customer_name": invoice.get("customer_name") or "Customer",
            "phone": invoice.get("customer_phone") or "",
            "items": items,
            "total": float(invoice.get("total") or 0.0),
            "payment_info": payment_info,
        }
    )
    return FileResponse(path, media_type="application/pdf", filename=f"{invoice['invoice_number']}.pdf")


@router.post("/invoices/{invoice_id}/payment", response_model=InvoiceResponse)
def record_payment_route(
    invoice_id: int,  # noqa: ARG001 - kept for a clear legacy-route error.
    ctx: BusinessContext = Depends(get_business_context),  # noqa: ARG001
) -> dict:
    raise HTTPException(
        status_code=410,
        detail="Direct invoice payment recording is disabled. Submit payment proof and approve it instead.",
    )
