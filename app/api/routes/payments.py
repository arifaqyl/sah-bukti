from fastapi import APIRouter, Request

from app.schemas.invoice import PaymentWebhookResponse
from app.services.payments import handle_billplz_webhook


router = APIRouter()


@router.post("/billplz-webhook", response_model=PaymentWebhookResponse)
async def billplz_webhook_route(request: Request) -> dict:
    payload = await request.json()
    return handle_billplz_webhook(payload)
