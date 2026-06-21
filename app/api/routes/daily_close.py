import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.dependencies import BusinessContext, get_business_context
from app.schemas.invoice import DailyCloseCreate, DailyCloseResponse
from app.services.exports import export_daily_ops
from app.services.daily_close import create_daily_close, get_daily_close, list_daily_close


router = APIRouter()


@router.post("/daily-close", response_model=DailyCloseResponse)
def daily_close_route(payload: DailyCloseCreate, ctx: BusinessContext = Depends(get_business_context)) -> dict:
    if payload.business_id is not None and payload.business_id != ctx.business_id:
        raise HTTPException(status_code=403, detail="Business access denied")
    data = payload.model_dump()
    data["business_id"] = ctx.business_id
    return create_daily_close(data)


@router.get("/daily-ops", response_model=list[DailyCloseResponse])
def daily_ops_route(ctx: BusinessContext = Depends(get_business_context)) -> list[dict]:
    return list_daily_close(ctx.business_id)


@router.get("/daily-ops/export")
def export_daily_ops_route(
    format: str = Query(default="csv"),
    ctx: BusinessContext = Depends(get_business_context),
):
    export_format = format.lower()
    if export_format not in {"csv", "json"}:
        raise HTTPException(status_code=422, detail="format must be csv or json")
    content = export_daily_ops(ctx.business_id, export_format)
    if export_format == "json":
        return JSONResponse(content=json.loads(content))
    return PlainTextResponse(content=content, media_type="text/csv")


@router.get("/daily-ops/{date}", response_model=DailyCloseResponse)
def daily_ops_by_date_route(date: str, ctx: BusinessContext = Depends(get_business_context)) -> dict:
    row = get_daily_close(date, ctx.business_id)
    if not row:
        raise HTTPException(status_code=404, detail="Daily close not found")
    return row
