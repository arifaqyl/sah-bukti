from fastapi import APIRouter, File, UploadFile
import uuid

from app.schemas.receipt import ReceiptResponse, ReceiptVerificationDetail
from app.services.receipts import list_verifications, verify_receipt_image

router = APIRouter()


@router.post("/verify")
async def verify_receipt(file: UploadFile = File(...), invoice_id: int | None = None) -> dict:
    file_bytes = await file.read()
    # Generate a unique filename to avoid collision
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    result = verify_receipt_image(file_bytes, unique_filename, invoice_id)
    return result


@router.get("", response_model=list[ReceiptVerificationDetail])
def list_receipts_route() -> list[dict]:
    results = list_verifications()
    formatted = []
    for r in results:
        formatted.append({
            "receipt": {
                "id": r["id"],
                "invoice_id": r["invoice_id"],
                "filename": r["filename"],
                "bank_name": r["bank_name"],
                "amount": r["amount"],
                "reference_number": r["reference_number"],
                "transaction_time": r["transaction_time"],
                "recipient_name": r["recipient_name"],
                "status": r["status"],
                "match_reason": r["match_reason"],
                "created_at": r["created_at"],
            },
            "matched_invoice_number": r["matched_invoice_number"],
            "matched_customer_name": r["matched_customer_name"]
        })
    return formatted
