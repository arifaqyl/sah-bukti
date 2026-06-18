from __future__ import annotations

from dataclasses import dataclass
import re

import httpx

from app.config import WHATSAPP_BRIDGE_URL, WHATSAPP_PROVIDER, WHATSAPP_SESSION_NAME


@dataclass
class WhatsAppResult:
    ok: bool
    provider: str
    detail: str


@dataclass
class PaymentInfo:
    detected: bool
    amount: float | None
    invoice_number: str | None
    method: str | None
    raw_text: str


def detect_payment(text: str) -> PaymentInfo:
    """
    Extract payment info from a WhatsApp message.

    Matches patterns like:
    - "Paid RM200 for INV-P1 via QR"
    - "Payment RM150 transfer to INV-O3"
    - "QR paid 300 for INV-P2"
    """
    amount_match = re.search(r"RM\s*([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
    if not amount_match:
        amount_match = re.search(r"(?:paid|payment)\s+([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)

    invoice_match = re.search(r"INV-[A-Z0-9-]+", text, re.IGNORECASE)

    method = "cash"
    text_lower = text.lower()
    if any(keyword in text_lower for keyword in ["qr", "duitnow", "duit now"]):
        method = "qr"
    elif any(keyword in text_lower for keyword in ["transfer", "bank", "fp"]):
        method = "transfer"
    elif any(keyword in text_lower for keyword in ["cash", "tunai"]):
        method = "cash"

    if amount_match and invoice_match:
        amount = float(amount_match.group(1).replace(",", ""))
        return PaymentInfo(
            detected=True,
            amount=amount,
            invoice_number=invoice_match.group(0).upper(),
            method=method,
            raw_text=text,
        )

    return PaymentInfo(
        detected=False,
        amount=None,
        invoice_number=None,
        method=None,
        raw_text=text,
    )


class BaseWhatsAppClient:
    def send_message(self, phone: str, text: str) -> WhatsAppResult:
        raise NotImplementedError

    def send_invoice(self, phone: str, invoice_number: str, total: float) -> WhatsAppResult:
        text = f"Invoice {invoice_number} confirmed. Total: RM{total:.2f}. Pay via QR/link/bank."
        return self.send_message(phone, text)


class WebJsWhatsAppClient(BaseWhatsAppClient):
    """Python adapter for a local whatsapp-web.js bridge process."""

    def __init__(self, base_url: str = WHATSAPP_BRIDGE_URL, session_name: str = WHATSAPP_SESSION_NAME) -> None:
        self.base_url = base_url
        self.session_name = session_name

    def send_message(self, phone: str, text: str) -> WhatsAppResult:
        payload = {
            "session": self.session_name,
            "phone": phone,
            "text": text,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(f"{self.base_url}/send", json=payload)
                response.raise_for_status()
            return WhatsAppResult(ok=True, provider="webjs", detail="sent")
        except Exception as exc:
            return WhatsAppResult(ok=False, provider="webjs", detail=str(exc))

    def send_invoice(self, phone: str, invoice_number: str, total: float) -> WhatsAppResult:
        text = f"Invoice {invoice_number} confirmed. Total: RM{total:.2f}. Pay via QR/link/bank."
        return self.send_message(phone, text)


class MockWhatsAppClient(BaseWhatsAppClient):
    def send_message(self, phone: str, text: str) -> WhatsAppResult:
        return WhatsAppResult(ok=True, provider="mock", detail=f"mock:{phone}:{text}")


def get_whatsapp_client() -> BaseWhatsAppClient:
    if WHATSAPP_PROVIDER == "webjs":
        return WebJsWhatsAppClient()
    return MockWhatsAppClient()
