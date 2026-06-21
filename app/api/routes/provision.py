from __future__ import annotations

import json
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.dependencies import BusinessContext, get_business_context
from app.schemas.provision import (
    AgingReportResponse,
    ErrorResponse,
    ProvisionCalculateResponse,
    ProvisionPolicyUpdateRequest,
)
from app.services.aging import AgingService
from app.services.provision import ProvisionEngine


router = APIRouter()
engine = ProvisionEngine()
aging_service = AgingService(engine.db)
_REQUEST_LOG: dict[str, deque[float]] = defaultdict(deque)
_RATE_LIMIT = 30
_RATE_WINDOW_SECONDS = 60


@router.get("/provision/aging", response_model=AgingReportResponse, responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def aging_route(
    request: Request,
    month: str = Query(),
    ctx: BusinessContext = Depends(get_business_context),
):
    limited = _check_rate_limit(request, "aging")
    if limited:
        return limited
    try:
        engine._validate_business_exists(ctx.business_id)
        breakdown = engine.get_aging(ctx.business_id, month)
        total_outstanding = round(sum(bucket["amount"] for bucket in breakdown), 2)
        if total_outstanding == 0:
            return _error_response(404, "no_data", "No unpaid invoices found for this business in this period")
        return {
            "month": month,
            "as_of": aging_service.month_end(month),
            "total_outstanding": total_outstanding,
            "buckets": breakdown,
            "total_provision": round(sum(bucket["provision"] for bucket in breakdown), 2),
        }
    except LookupError:
        return _error_response(404, "not_found", "Business not found")
    except ValueError as exc:
        return _error_response(422, "validation_error", str(exc))


@router.get("/provision/calculate", response_model=ProvisionCalculateResponse, responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def calculate_route(
    request: Request,
    month: str = Query(),
    policy: str | None = Query(default=None),
    ctx: BusinessContext = Depends(get_business_context),
):
    limited = _check_rate_limit(request, "calculate")
    if limited:
        return limited
    try:
        parsed_policy = _parse_policy(policy)
        result = engine.calculate(ctx.business_id, month, parsed_policy)
        return result
    except LookupError as exc:
        code = "no_data" if "No unpaid invoices" in str(exc) else "not_found"
        return _error_response(404, code, str(exc))
    except ValueError as exc:
        return _policy_or_month_error(exc)


@router.get("/provision/export", responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def export_route(
    request: Request,
    month: str = Query(),
    format: str = Query(default="csv"),
    policy: str | None = Query(default=None),
    ctx: BusinessContext = Depends(get_business_context),
):
    limited = _check_rate_limit(request, "export")
    if limited:
        return limited
    try:
        parsed_policy = _parse_policy(policy)
        result = engine.calculate(ctx.business_id, month, parsed_policy)
        if format.lower() == "json":
            return result
        csv_text = engine.export_csv(ctx.business_id, result)
        return PlainTextResponse(content=csv_text, media_type="text/csv")
    except LookupError as exc:
        code = "no_data" if "No unpaid invoices" in str(exc) else "not_found"
        return _error_response(404, code, str(exc))
    except ValueError as exc:
        return _policy_or_month_error(exc)


@router.post("/provision/policy", responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def policy_route(payload: ProvisionPolicyUpdateRequest, ctx: BusinessContext = Depends(get_business_context)):
    try:
        if payload.business_id != ctx.business_id:
            raise HTTPException(status_code=403, detail="Business access denied")
        updated = engine.update_policy(ctx.business_id, payload.policy)
        return {"business_id": ctx.business_id, "policy": updated}
    except LookupError:
        return _error_response(404, "not_found", "Business not found")
    except ValueError as exc:
        return _policy_or_month_error(exc)


def _parse_policy(policy: str | None) -> dict | None:
    if not policy:
        return None
    try:
        loaded = json.loads(policy)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid provision policy format") from exc
    if not isinstance(loaded, dict):
        raise ValueError("Invalid provision policy format")
    return loaded


def _policy_or_month_error(exc: ValueError):
    try:
        details = json.loads(str(exc))
        if isinstance(details, list):
            return _error_response(422, "validation_error", "Invalid provision policy format", details)
    except json.JSONDecodeError:
        pass
    return _error_response(422, "validation_error", str(exc))


def _error_response(status_code: int, code: str, message: str, details: list[dict] | None = None):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or []}},
    )


def _check_rate_limit(request: Request, scope: str):
    key = f"{scope}:{request.client.host if request.client else 'local'}"
    now = time.time()
    bucket = _REQUEST_LOG[key]
    while bucket and now - bucket[0] > _RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT:
        return _error_response(429, "rate_limited", "Too many provision requests. Try again later.")
    bucket.append(now)
    return None
