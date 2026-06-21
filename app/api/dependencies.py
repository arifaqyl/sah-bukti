from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Query, status

from app.db.store import get_db
from app.services.auth import get_business, get_membership, get_user_by_token


DEMO_BUSINESS_ID = 1


@dataclass(frozen=True)
class BusinessContext:
    user: dict
    business_id: int
    business: dict
    role: str


def _extract_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


async def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return user


async def get_business_context(
    business_id: int | None = Query(default=None, ge=1),
    user: dict = Depends(get_current_user),
) -> BusinessContext:
    if business_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="business_id is required")

    business = get_business(business_id)
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    membership = get_membership(user["id"], business_id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business access denied")

    return BusinessContext(
        user=user,
        business_id=business_id,
        business=business,
        role=membership["role"],
    )


async def get_business_context_demo(
    business_id: int | None = Query(default=None, ge=1),
    demo: int | None = Query(default=0),
    authorization: str | None = Header(default=None),
) -> BusinessContext:
    token = _extract_token(authorization)
    if demo == 1 and not token:
        bid = business_id or DEMO_BUSINESS_ID
        if bid != DEMO_BUSINESS_ID:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business access denied")
        business = get_business(bid)
        if not business:
            business = {"id": DEMO_BUSINESS_ID, "name": "Demo Shop", "owner_whatsapp": None}
        demo_user = {
            "id": 1,
            "display_name": "Demo Owner",
            "email": "demo@sahbukti.com",
        }
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.display_name, u.email
                FROM business_memberships bm
                JOIN users u ON u.id = bm.user_id
                WHERE bm.business_id = ?
                ORDER BY CASE WHEN bm.role = 'owner' THEN 0 ELSE 1 END, bm.id ASC
                LIMIT 1
                """,
                (bid,),
            ).fetchone()
        if row:
            demo_user = {
                "id": int(row["id"]),
                "display_name": row["display_name"] or "Demo Owner",
                "email": row["email"],
            }
        return BusinessContext(
            user=demo_user,
            business_id=bid,
            business=business,
            role="owner",
        )

    user = await get_current_user(authorization)
    if business_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="business_id is required")

    business = get_business(business_id)
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    membership = get_membership(user["id"], business_id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business access denied")

    return BusinessContext(
        user=user,
        business_id=business_id,
        business=business,
        role=membership["role"],
    )


async def require_owner_context(ctx: BusinessContext = Depends(get_business_context)) -> BusinessContext:
    if ctx.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required")
    return ctx
