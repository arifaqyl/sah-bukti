import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.dependencies import BusinessContext, get_business_context_demo
from app.services.exports import export_accountant_package


router = APIRouter()


@router.get("/exports/accountant")
def accountant_export_route(
    month: str | None = Query(default=None),
    as_of_date: str | None = Query(default=None),
    include_proof_payloads: bool = Query(default=False),
    format: str = Query(default="json"),
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> object:
    try:
        payload = export_accountant_package(
            business_id=ctx.business_id,
            month=month,
            as_of_date=as_of_date,
            include_proof_payloads=include_proof_payloads,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    export_format = format.lower()
    filename_month = payload["period"]["month"] or "current"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    download_headers = {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
    }
    if export_format == "csv":
        stream = io.StringIO()
        writer = csv.DictWriter(
            stream,
            fieldnames=["invoice_number", "customer_name", "total", "payment_status", "outstanding_amount"],
        )
        writer.writeheader()
        for invoice in payload["invoices"]:
            writer.writerow(
                {
                    "invoice_number": invoice["invoice_number"],
                    "customer_name": invoice["customer_name"],
                    "total": invoice["total"],
                    "payment_status": invoice["payment_status"],
                    "outstanding_amount": invoice["outstanding_amount"],
                }
            )
        return PlainTextResponse(
            content=stream.getvalue(),
            media_type="text/csv",
            headers={
                **download_headers,
                "Content-Disposition": f'attachment; filename="sahbukti-export-{filename_month}-{timestamp}.csv"',
            },
        )
    if export_format != "json":
        raise HTTPException(status_code=422, detail="format must be csv or json")
    return JSONResponse(
        content=payload,
        headers={
            **download_headers,
            "Content-Disposition": f'attachment; filename="sahbukti-export-{filename_month}-{timestamp}.json"',
        },
    )
