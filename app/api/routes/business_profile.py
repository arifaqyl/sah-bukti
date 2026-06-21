from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import BusinessContext, get_business_context
from app.schemas.business_profile import BusinessProfileResponse, BusinessProfileUpdate
from app.services.business_profile import get_business_profile, update_business_profile


router = APIRouter()


@router.get("/business/profile", response_model=BusinessProfileResponse)
def get_business_profile_route(ctx: BusinessContext = Depends(get_business_context)) -> dict:
    profile = get_business_profile(ctx.business_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Business not found")
    return profile


@router.patch("/business/profile", response_model=BusinessProfileResponse)
def update_business_profile_route(
    payload: BusinessProfileUpdate,
    ctx: BusinessContext = Depends(get_business_context),
) -> dict:
    profile = update_business_profile(ctx.business_id, payload.model_dump(exclude_unset=True))
    if not profile:
        raise HTTPException(status_code=404, detail="Business not found")
    return profile
