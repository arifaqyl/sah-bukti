from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.schemas.auth import BusinessListItem
from app.services.auth import list_businesses_for_user


router = APIRouter()


@router.get("/businesses", response_model=list[BusinessListItem])
async def list_businesses_route(user: dict = Depends(get_current_user)) -> list[dict]:
    return list_businesses_for_user(user["id"])
