from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
import re

import httpx

from app.config import WHATSAPP_API_KEY, WHATSAPP_BRIDGE_URL, WHATSAPP_PROVIDER, WHATSAPP_SESSION_NAME


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

    explicit_payment = bool(re.search(r"\b(paid|payment|dah bayar|dh bayar|dh byr|bayar dah|transfer dah|done pay)\b", text, re.IGNORECASE))

    if amount_match and invoice_match:
        amount = float(amount_match.group(1).replace(",", ""))
        return PaymentInfo(
            detected=True,
            amount=amount,
            invoice_number=invoice_match.group(0).upper(),
            method=method,
            raw_text=text,
        )

    if explicit_payment:
        amount = float(amount_match.group(1).replace(",", "")) if amount_match else None
        return PaymentInfo(
            detected=True,
            amount=amount,
            invoice_number=invoice_match.group(0).upper() if invoice_match else None,
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

    def send_buttons(self, phone: str, text: str, buttons: list[str]) -> WhatsAppResult:
        """Send interactive buttons - fallback to plain text for mock/webjs."""
        btn_list = ", ".join(buttons[:3])
        return self.send_message(phone, f"{text}\n\n[{btn_list}]")

    def send_invoice(self, phone: str, invoice_number: str, total: float) -> WhatsAppResult:
        text = f"Invoice {invoice_number} confirmed. Total: RM{total:.2f}. Pay via QR/link/bank."
        return self.send_message(phone, text)

    def get_session_info(self) -> dict:
        raise NotImplementedError

    def get_qr_payload(self) -> dict:
        raise NotImplementedError

    def download_media(self, media: dict | None) -> dict | None:
        return None


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


class WahaWhatsAppClient(BaseWhatsAppClient):
    """Python adapter for WAHA (WhatsApp HTTP API)."""

    def __init__(self, base_url: str = WHATSAPP_BRIDGE_URL, session_name: str = WHATSAPP_SESSION_NAME) -> None:
        self.base_url = base_url.rstrip("/")
        self.session_name = session_name

    def _headers(self, accept: str = "application/json") -> dict:
        headers = {"Accept": accept}
        if WHATSAPP_API_KEY:
            headers["X-Api-Key"] = WHATSAPP_API_KEY
        return headers

    @staticmethod
    def _chat_id(target: str) -> str:
        normalized = (target or "").strip()
        if "@" in normalized:
            return normalized
        return f"{normalized}@c.us"

    def send_message(self, phone: str, text: str) -> WhatsAppResult:
        chat_id = self._chat_id(phone)
        payload = {
            "session": self.session_name,
            "chatId": chat_id,
            "text": text,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(f"{self.base_url}/api/sendText", json=payload, headers=self._headers())
                if response.is_error:
                    return self._error_result("sendText", chat_id, response)
            return WhatsAppResult(ok=True, provider="waha", detail="sent")
        except Exception as exc:
            return WhatsAppResult(ok=False, provider="waha", detail=str(exc))

    def send_buttons(self, phone: str, text: str, buttons: list[str]) -> WhatsAppResult:
        """Send interactive button message via WAHA sendButtons endpoint."""
        chat_id = self._chat_id(phone)
        payload = {
            "session": self.session_name,
            "chatId": chat_id,
            "title": text,
            "body": text,
            "buttons": [{"type": "reply", "reply": {"id": f"btn_{i}", "title": btn}} for i, btn in enumerate(buttons[:3])],
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(f"{self.base_url}/api/sendButtons", json=payload, headers=self._headers())
                if response.is_error:
                    return self._error_result("sendButtons", chat_id, response)
            return WhatsAppResult(ok=True, provider="waha", detail="buttons_sent")
        except Exception as exc:
            return WhatsAppResult(ok=False, provider="waha", detail=str(exc))

    def send_invoice(self, phone: str, invoice_number: str, total: float) -> WhatsAppResult:
        text = f"Invoice {invoice_number} confirmed. Total: RM{total:.2f}. Pay via QR/link/bank."
        return self.send_message(phone, text)

    def get_session_info(self) -> dict:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{self.base_url}/api/sessions/{self.session_name}", headers=self._headers())
            response.raise_for_status()
            return response.json()

    def get_qr_payload(self) -> dict:
        session = self.get_session_info()
        engine_state = ((session.get("engine") or {}).get("state") or "").upper()
        if session.get("status") == "WORKING" and engine_state == "CONNECTED":
            return {
                "ok": False,
                "connected": True,
                "detail": "Session already connected",
                "session": session,
            }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.base_url}/api/{self.session_name}/auth/qr?format=image",
                    headers=self._headers(),
                )
                if response.status_code >= 400:
                    return {"ok": False, "status_code": response.status_code, "detail": response.text}
                if "application/json" in response.headers.get("content-type", ""):
                    payload = response.json()
                    return {"ok": True, **payload}
                return {
                    "ok": True,
                    "mimetype": response.headers.get("content-type", "image/png"),
                    "data": response.content.decode("latin1"),
                }
        except Exception as exc:
            return {"ok": False, "detail": str(exc), "session": session}

    def download_media(self, media: dict | None) -> dict | None:
        if not media:
            return None
        url = str(media.get("url") or "").strip()
        if not url:
            return None
        resolved_url = url if url.startswith("http://") or url.startswith("https://") else f"{self.base_url}{url if url.startswith('/') else '/' + url}"
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(resolved_url, headers=self._headers(accept="*/*"))
                response.raise_for_status()
            return {
                "content": response.content,
                "mime_type": media.get("mimetype") or response.headers.get("content-type") or "application/octet-stream",
                "filename": media.get("filename") or "attachment",
                "url": resolved_url,
            }
        except Exception:
            return None

    def _error_result(self, action: str, chat_id: str, response: httpx.Response) -> WhatsAppResult:
        detail = f"{action} failed ({response.status_code})"
        body = (response.text or "").strip()
        if body:
            detail = f"{detail}: {body[:240]}"
        try:
            session = self.get_session_info()
            me_id = str((session.get("me") or {}).get("id") or "").strip()
        except Exception:
            me_id = ""
        if me_id and chat_id == me_id:
            detail = "WAHA cannot send a reply to the same linked WhatsApp account. Use another chat/contact for live bot replies."
        return WhatsAppResult(ok=False, provider="waha", detail=detail)


class MockWhatsAppClient(BaseWhatsAppClient):
    def send_message(self, phone: str, text: str) -> WhatsAppResult:
        return WhatsAppResult(ok=True, provider="mock", detail=f"mock:{phone}:{text}")

    def get_session_info(self) -> dict:
        return {"name": "mock", "status": "WORKING"}

    def get_qr_payload(self) -> dict:
        return {"ok": False, "detail": "mock client has no QR"}


def get_whatsapp_client() -> BaseWhatsAppClient:
    if WHATSAPP_PROVIDER == "waha":
        return WahaWhatsAppClient()
    if WHATSAPP_PROVIDER == "webjs":
        return WebJsWhatsAppClient()
    return MockWhatsAppClient()


class SahBuktiAgent:
    """Personal business assistant for WhatsApp."""

    TOOLS = {
        "forward_proof": "handle_forward_proof",
        "approve": "handle_approve",
        "edit": "handle_edit",
        "undo": "handle_undo",
        "reject": "handle_reject",
        "status": "handle_status",
        "today": "handle_daily_summary",
        "customer": "handle_customer_lookup",
        "stock": "handle_stock_check",
        "menu": "handle_send_menu",
        "receipt": "handle_send_receipt",
        "remind": "handle_send_reminder",
        "bind_group": "handle_bind_group",
        "help": "handle_help",
    }

    def __init__(self, business_id: int, owner_phone: str | None = None) -> None:
        self.business_id = business_id
        self.owner_phone = owner_phone or ""

    def route(self, phone: str, message: str) -> str:
        msg = message.strip()
        normalized = _normalize_agent_command(msg)
        cmd = normalized.lower().split()[0] if normalized else ""
        if cmd in self.TOOLS and (not self.owner_phone or phone == self.owner_phone):
            handler = getattr(self, self.TOOLS[cmd])
            return handler(phone, normalized)
        return self.handle_forward_proof(phone, normalized or message)

    def handle_forward_proof(self, phone: str, message: str) -> str:
        from app.services.evidence import ingest_whatsapp_evidence

        result = ingest_whatsapp_evidence(
            business_id=self.business_id,
            from_phone=phone,
            message=message,
            transcript=None,
            media_type="text",
            media_metadata={"agent": "sahbukti"},
        )
        return format_evidence_ack(result)

    def handle_approve(self, phone: str, message: str) -> str:  # noqa: ARG002
        parts = message.strip().split()
        proof_id = _parse_int(parts[1]) if len(parts) > 1 else None
        if proof_id is None:
            return "Usage: approve [proof_id] [amount] [reference]"
        amount = None
        reference = None
        if len(parts) > 2:
            try:
                amount = float(parts[2].replace("RM", "").replace(",", ""))
            except ValueError:
                reference = parts[2]
        if len(parts) > 3:
            reference = parts[3]
        from app.services.payment_proofs import approve_payment_proof

        try:
            proof = approve_payment_proof(
                proof_id=proof_id,
                business_id=self.business_id,
                reviewer_user_id=None,
                amount=amount,
                reference=reference,
            )
            return f"Proof {proof_id} approved. Ledger updated. Payment ID: {proof.get('approved_payment_id')}"
        except Exception as exc:
            return f"Failed to approve: {exc}"

    def handle_edit(self, phone: str, message: str) -> str:  # noqa: ARG002
        parts = message.strip().split()
        proof_id = _parse_int(parts[1]) if len(parts) > 1 else None
        if proof_id is None or len(parts) < 4:
            return "Usage: edit [proof_id] [amount] [reference]"
        try:
            amount = float(parts[2].replace("RM", "").replace(",", ""))
        except ValueError:
            return "Usage: edit [proof_id] [amount] [reference]"
        reference = parts[3]
        from app.services.payment_proofs import edit_payment_proof

        try:
            proof = edit_payment_proof(
                proof_id=proof_id,
                business_id=self.business_id,
                reviewer_user_id=None,
                amount=amount,
                reference=reference,
                decision_reason="edited_via_whatsapp",
            )
            return f"Proof {proof_id} updated to RM{float(proof.get('extracted_amount') or 0.0):.2f} ref {proof.get('extracted_reference') or reference}."
        except Exception as exc:
            return f"Failed to edit: {exc}"

    def handle_undo(self, phone: str, message: str) -> str:  # noqa: ARG002
        parts = message.strip().split()
        proof_id = _parse_int(parts[1]) if len(parts) > 1 else None
        if proof_id is None:
            return "Usage: undo [proof_id]"
        from app.services.payment_proofs import undo_payment_proof_approval

        try:
            undo_payment_proof_approval(
                proof_id=proof_id,
                business_id=self.business_id,
                reviewer_user_id=None,
                decision_reason="undone_via_whatsapp",
            )
            return f"Proof {proof_id} reverted. Ledger rolled back. You can edit and approve again."
        except Exception as exc:
            return f"Failed to undo: {exc}"

    def handle_reject(self, phone: str, message: str) -> str:  # noqa: ARG002
        parts = message.strip().split()
        proof_id = _parse_int(parts[1]) if len(parts) > 1 else None
        if proof_id is None:
            return "Usage: reject [proof_id]"
        from app.services.payment_proofs import reject_payment_proof

        try:
            reject_payment_proof(
                proof_id=proof_id,
                business_id=self.business_id,
                reviewer_user_id=None,
                decision_reason="Rejected via WhatsApp",
            )
            return f"Proof {proof_id} rejected."
        except Exception as exc:
            return f"Failed to reject: {exc}"

    def handle_status(self, phone: str, message: str) -> str:
        from app.services.payment_proofs import list_payment_proofs

        proofs = list_payment_proofs(self.business_id, review_state="needs_review")
        total = sum(float(p.get("extracted_amount") or 0.0) for p in proofs)
        lines = [f"Pending proofs: {len(proofs)}", f"Total awaiting: RM{total:.2f}"]
        for proof in proofs[:5]:
            ref = proof.get("extracted_reference") or proof.get("invoice_number") or "PENDING"
            amount = float(proof.get("extracted_amount") or 0.0)
            lines.append(f"#{proof['id']} {ref} RM{amount:.2f}")
        lines.append("Reply approve [id] or reject [id].")
        return "\n".join(lines)

    def get_pending_proof_ids(self) -> list[int]:
        from app.services.payment_proofs import list_payment_proofs
        proofs = list_payment_proofs(self.business_id, review_state="needs_review")
        return [p["id"] for p in proofs[:3]]

    def get_latest_pending_proof_id(self) -> int | None:
        proof_ids = self.get_pending_proof_ids()
        return proof_ids[0] if proof_ids else None

    def handle_daily_summary(self, phone: str, message: str) -> str:  # noqa: ARG002
        from app.services.invoices import list_invoices
        from app.services.payment_proofs import list_payment_proofs

        invoices = list_invoices(self.business_id)
        pending = list_payment_proofs(self.business_id, review_state="needs_review")
        paid_total = sum(float(i.get("total") or 0.0) for i in invoices if i.get("payment_status") == "paid")
        return (
            "Laporan Harian Sah.Bukti\n"
            f"Tarikh: {datetime.now().strftime('%d/%m/%Y')}\n"
            f"Invoices: {len(invoices)}\n"
            f"Paid total: RM{paid_total:.2f}\n"
            f"Pending proofs: {len(pending)}"
        )

    def handle_customer_lookup(self, phone: str, message: str) -> str:  # noqa: ARG002
        from app.services.customers import list_customers

        parts = message.strip().split(maxsplit=1)
        query = parts[1].lower() if len(parts) > 1 else ""
        if not query:
            return "Usage: customer [name_or_phone]"
        matches = [
            customer for customer in list_customers(self.business_id)
            if query in (customer.get("name") or "").lower() or query in (customer.get("phone") or "").lower()
        ]
        if not matches:
            return f"No customer found for {query}."
        customer = matches[0]
        return f"{customer['name']}: {customer.get('phone') or 'no phone'}"

    def handle_stock_check(self, phone: str, message: str) -> str:  # noqa: ARG002
        from app.services.inventory import list_ingredients

        parts = message.strip().split(maxsplit=1)
        query = parts[1].lower() if len(parts) > 1 else ""
        if not query:
            return "Usage: stock [item name]"
        matches = [item for item in list_ingredients(self.business_id) if query in item.get("name", "").lower()]
        if not matches:
            return f"No stock item found for {query}."
        item = matches[0]
        return f"{item['name']}: {item['current_stock']} {item.get('unit') or 'unit'} left."

    def handle_send_menu(self, phone: str, message: str) -> str:  # noqa: ARG002
        return (
            "MENU\n"
            "Nasi Lemak - RM5.00\n"
            "Nasi Goreng - RM7.00\n"
            "Roti Canai - RM3.50\n"
            "Mee Rebus - RM6.00\n"
            "Teh Tarik - RM2.00\n\n"
            "Sah.Bukti - Proof before payment."
        )

    def handle_send_receipt(self, phone: str, message: str) -> str:  # noqa: ARG002
        parts = message.strip().split()
        order_id = parts[1] if len(parts) > 1 else None
        if not order_id:
            return "Usage: receipt [order_id]"
        from app.services.receipts import generate_receipt_pdf

        try:
            path = generate_receipt_pdf(
                {
                    "order_id": order_id,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "customer_name": phone,
                    "phone": phone,
                    "items": [{"name": "Manual receipt", "qty": 1, "price": 0.0}],
                    "total": 0.0,
                }
            )
            return f"Receipt generated: {path}"
        except Exception as exc:
            return f"Failed to generate receipt: {exc}"

    def handle_send_reminder(self, phone: str, message: str) -> str:  # noqa: ARG002
        parts = message.strip().split(maxsplit=1)
        customer_phone = parts[1] if len(parts) > 1 else ""
        if not customer_phone:
            return "Usage: remind [customer_phone]"
        return f"Reminder queued for {customer_phone}."

    def handle_help(self, phone: str, message: str) -> str:  # noqa: ARG002
        return (
            "SAH.BUKTI COMMANDS\n"
            "Forward any message -> create reviewable proof/order\n"
            "status -> pending proofs\n"
            "approve [id] -> approve proof\n"
            "reject [id] -> reject proof\n"
            "today -> daily summary\n"
            "customer [phone/name] -> customer lookup\n"
            "stock [item] -> stock check\n"
            "menu -> price list\n"
            "receipt [id] -> generate receipt\n"
            "remind [phone] -> payment reminder\n"
            "help -> this list"
        )


def format_evidence_ack(result: dict) -> str:
    proof = result.get("payment_proof") or {}
    invoice = result.get("invoice") or {}
    if invoice and not proof:
        invoice_number = invoice.get("invoice_number") or f"INV-{invoice.get('id') or 'PENDING'}"
        total = float(invoice.get("total") or 0.0)
        return (
            f"Invoice {invoice_number} captured\n"
            f"Total: RM{total:.2f}\n"
            "Status: Pending confirmation\n"
            "Open Sah.Bukti Review or Invoices to confirm the order."
        )
    ref = proof.get("extracted_reference") or invoice.get("invoice_number") or "PENDING"
    amount = proof.get("extracted_amount")
    if amount is None:
        amount = invoice.get("total") or 0.0
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        amount_value = 0.0
    return (
        f"Proof #{proof.get('id') or invoice.get('id') or 'PENDING'} received for {ref}\n"
        f"Amount: RM{amount_value:.2f}\n"
        "Status: Menunggu kelulusan pemilik\n"
        f"Reply approve {proof.get('id') or ''} or reject {proof.get('id') or ''}."
    )


def _parse_int(value: str) -> int | None:
    cleaned = value.lower().lstrip("p#")
    try:
        return int(cleaned)
    except ValueError:
        return None


def _normalize_agent_command(message: str) -> str:
    msg = (message or "").strip()
    if not msg:
        return msg
    lower = msg.lower()
    if lower.startswith("✓#") or lower.startswith("approve#"):
        proof_id = _parse_int(msg.split("#", 1)[1]) if "#" in msg else None
        return f"approve {proof_id}" if proof_id is not None else msg
    if lower.startswith("✗#") or lower.startswith("reject#"):
        proof_id = _parse_int(msg.split("#", 1)[1]) if "#" in msg else None
        return f"reject {proof_id}" if proof_id is not None else msg
    if lower.startswith("↩#") or lower.startswith("undo#"):
        proof_id = _parse_int(msg.split("#", 1)[1]) if "#" in msg else None
        return f"undo {proof_id}" if proof_id is not None else msg
    compact = lower.replace("  ", " ")
    if compact.startswith("approve #"):
        return "approve " + msg.split("#", 1)[1]
    if compact.startswith("reject #"):
        return "reject " + msg.split("#", 1)[1]
    if compact.startswith("undo #"):
        return "undo " + msg.split("#", 1)[1]
    if compact.startswith("edit #"):
        return "edit " + msg.split("#", 1)[1]
    if compact in {"approve", "reject", "undo", "edit"}:
        return compact
    return msg


def extract_document_text(file_bytes: bytes, mime_type: str | None, filename: str | None = None) -> str | None:
    resolved_type = (mime_type or "").lower()
    resolved_name = (filename or "").lower()
    if "pdf" in resolved_type or resolved_name.endswith(".pdf"):
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(BytesIO(file_bytes))
            chunks: list[str] = []
            for page in reader.pages[:10]:
                text = (page.extract_text() or "").strip()
                if text:
                    chunks.append(text)
            extracted = "\n".join(chunks).strip()
            return extracted or None
        except Exception:
            return None
    if resolved_type.startswith("text/") or resolved_name.endswith(".txt") or resolved_name.endswith(".csv"):
        try:
            return file_bytes.decode("utf-8", errors="ignore").strip() or None
        except Exception:
            return None
    return None
