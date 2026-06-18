import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from app.schemas.invoice import DailyCloseCreate, DailyCloseResponse
from app.services.exports import export_daily_ops
from app.services.daily_close import create_daily_close, get_daily_close, list_daily_close


router = APIRouter()


@router.post("/daily-close", response_model=DailyCloseResponse)
def daily_close_route(payload: DailyCloseCreate) -> dict:
    return create_daily_close(payload.model_dump())


@router.get("/daily-ops", response_model=list[DailyCloseResponse])
def daily_ops_route(business_id: int = Query(default=1, ge=1)) -> list[dict]:
    return [row for row in list_daily_close() if int(row["business_id"]) == business_id]


@router.get("/daily-ops/export")
def export_daily_ops_route(
    business_id: int = Query(default=1, ge=1),
    format: str = Query(default="csv"),
):
    export_format = format.lower()
    if export_format not in {"csv", "json"}:
        raise HTTPException(status_code=422, detail="format must be csv or json")
    content = export_daily_ops(business_id, export_format)
    if export_format == "json":
        return JSONResponse(content=json.loads(content))
    return PlainTextResponse(content=content, media_type="text/csv")


@router.get("/daily-ops/{date}", response_model=DailyCloseResponse)
def daily_ops_by_date_route(date: str) -> dict:
    row = get_daily_close(date)
    if not row:
        raise HTTPException(status_code=404, detail="Daily close not found")
    return row
