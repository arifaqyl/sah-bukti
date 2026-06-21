from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import BusinessContext, get_business_context, require_owner_context
from app.schemas.reminder import (
    ReminderDetailResponse,
    ReminderGenerateRequest,
    ReminderGenerateResponse,
    ReminderPolicyResponse,
    ReminderPolicyUpsert,
    ReminderResponse,
)
from app.services.reminders import (
    ReminderNotFoundError,
    generate_reminders,
    get_reminder,
    get_reminder_policies,
    list_reminder_events,
    list_reminders,
    send_reminder,
    upsert_reminder_policy,
)


router = APIRouter()


@router.get("/reminders/policies", response_model=list[ReminderPolicyResponse])
def get_reminder_policies_route(ctx: BusinessContext = Depends(get_business_context)) -> list[dict]:
    return get_reminder_policies(ctx.business_id)


@router.post("/reminders/policies", response_model=ReminderPolicyResponse)
def upsert_reminder_policy_route(
    payload: ReminderPolicyUpsert,
    ctx: BusinessContext = Depends(require_owner_context),
) -> dict:
    try:
        return upsert_reminder_policy(ctx.business_id, payload.model_dump())
    except ReminderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/reminders", response_model=list[ReminderResponse])
def list_reminders_route(ctx: BusinessContext = Depends(get_business_context)) -> list[dict]:
    return list_reminders(ctx.business_id)


@router.post("/reminders/generate", response_model=ReminderGenerateResponse)
def generate_reminders_route(
    payload: ReminderGenerateRequest,
    ctx: BusinessContext = Depends(require_owner_context),
) -> dict:
    try:
        return generate_reminders(
            business_id=ctx.business_id,
            actor_user_id=ctx.user["id"],
            as_of_date=payload.as_of_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reminders/{reminder_id}", response_model=ReminderDetailResponse)
def get_reminder_route(reminder_id: int, ctx: BusinessContext = Depends(get_business_context)) -> dict:
    reminder = get_reminder(reminder_id, ctx.business_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {
        "reminder": reminder,
        "events": list_reminder_events(reminder_id, ctx.business_id),
    }


@router.post("/reminders/{reminder_id}/send", response_model=ReminderResponse)
def send_reminder_route(reminder_id: int, ctx: BusinessContext = Depends(require_owner_context)) -> dict:
    try:
        return send_reminder(
            reminder_id=reminder_id,
            business_id=ctx.business_id,
            actor_user_id=ctx.user["id"],
        )
    except ReminderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
