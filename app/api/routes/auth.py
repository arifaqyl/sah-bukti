from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.dependencies import get_current_user
from app.schemas.auth import AuthLogin, AuthMe, AuthSignup, AuthTokenResponse, LogoutResponse, MembershipResponse
from app.services.auth import authenticate_user, list_memberships, revoke_token, signup_user


router = APIRouter()


def _extract_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


@router.post("/signup", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: AuthSignup) -> dict:
    try:
        auth_result = signup_user(
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
            business_name=payload.business_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "access_token": auth_result["access_token"],
        "token_type": "bearer",
        "user": auth_result["user"],
    }


@router.post("/login", response_model=AuthTokenResponse)
async def login(payload: AuthLogin) -> dict:
    try:
        auth_result = authenticate_user(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return {
        "access_token": auth_result["access_token"],
        "token_type": "bearer",
        "user": auth_result["user"],
    }


@router.get("/me", response_model=AuthMe)
async def me(user: dict = Depends(get_current_user)) -> dict:
    return user


@router.get("/memberships", response_model=list[MembershipResponse])
async def memberships(user: dict = Depends(get_current_user)) -> list[dict]:
    return list_memberships(user["id"])


@router.post("/logout", response_model=LogoutResponse)
async def logout(authorization: str | None = Header(default=None)) -> dict:
    token = _extract_token(authorization)
    if token:
        revoke_token(token)
    return {"ok": True}
