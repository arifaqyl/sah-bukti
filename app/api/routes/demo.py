from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import BusinessContext, get_business_context_demo


router = APIRouter()


@router.post("/demo/seed")
def seed_demo_route(ctx: BusinessContext = Depends(get_business_context_demo)) -> dict:  # noqa: ARG001
    try:
        from scripts.seed_demo import main as seed_demo_main

        seed_demo_main()
        return {"ok": True, "detail": "Demo data seeded"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
