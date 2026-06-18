from fastapi import APIRouter


router = APIRouter()


@router.get("")
def healthcheck() -> dict:
    return {"ok": True}
