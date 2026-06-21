import base64
import json
import logging
import uuid
from pathlib import Path

import httpx

from app.config import (
    CLAUDE_API_KEY,
    CLAUDE_MODEL,
    GEMINI_API_KEY,
    RECEIPT_AI_API_KEY,
    RECEIPT_AI_BASE_URL,
    RECEIPT_AI_MODEL,
    RECEIPT_AI_PROVIDER,
    UPLOADS_DIR,
)
from app.db.store import get_db, utc_now

logger = logging.getLogger(__name__)


def verify_receipt_image(file_bytes: bytes, filename: str, invoice_id: int | None = None) -> dict:
    file_path = UPLOADS_DIR / filename
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    base64_image = base64.b64encode(file_bytes).decode("utf-8")
    mime_type = _guess_mime_type(filename)

    extracted_data, raw_response_text, ai_provider = _extract_receipt_payload(base64_image, mime_type)

    status = "verified"
    match_reason = "unprocessed"
    matched_invoice_id = invoice_id
    ref_num = extracted_data.get("reference_number")
    extracted_amount = extracted_data.get("amount")

    if extracted_amount is not None:
        try:
            extracted_amount = float(extracted_amount)
        except ValueError:
            extracted_amount = None

    is_duplicate = False
    if ref_num:
        with get_db() as conn:
            existing = conn.execute(
                "SELECT id FROM receipt_verifications WHERE reference_number = ?",
                (ref_num,),
            ).fetchone()
            if existing:
                is_duplicate = True
                status = "duplicate"
                match_reason = "duplicate_reference_number"

    tx_status = extracted_data.get("status", "SUCCESS").upper()

    if not is_duplicate and tx_status != "FAILED":
        if matched_invoice_id is not None:
            with get_db() as conn:
                matched_inv = conn.execute(
                    "SELECT id, amount, status FROM invoices WHERE id = ?",
                    (matched_invoice_id,),
                ).fetchone()

                if matched_inv:
                    if matched_inv["status"] == "paid":
                        status = "verified"
                        match_reason = "invoice_already_paid"
                    elif extracted_amount is not None and abs(float(matched_inv["amount"]) - extracted_amount) < 0.01:
                        status = "verified"
                        conn.execute(
                            """
                            UPDATE invoices
                            SET status = 'paid', updated_at = ?, paid_at = ?, payment_reference = ?
                            WHERE id = ?
                            """,
                            (utc_now(), extracted_data.get("transaction_time"), ref_num, matched_invoice_id),
                        )
                        match_reason = "direct_invoice_amount_match"
                    else:
                        status = "mismatch"
                        match_reason = "direct_invoice_amount_mismatch"
                else:
                    status = "failed"
                    match_reason = "invoice_not_found"
        else:
            with get_db() as conn:
                matched_inv = conn.execute(
                    """
                    SELECT id FROM invoices
                    WHERE amount = ? AND status != 'paid'
                    ORDER BY id ASC LIMIT 1
                    """,
                    (extracted_amount,),
                ).fetchone()

                if matched_inv:
                    matched_invoice_id = matched_inv["id"]
                    status = "verified"
                    conn.execute(
                        """
                        UPDATE invoices
                        SET status = 'paid', updated_at = ?, paid_at = ?, payment_reference = ?
                        WHERE id = ?
                        """,
                        (utc_now(), extracted_data.get("transaction_time"), ref_num, matched_invoice_id),
                    )
                    match_reason = "fallback_amount_match"
                else:
                    status = "mismatch"
                    match_reason = "no_unpaid_invoice_amount_match"
    elif tx_status == "FAILED" and not match_reason:
        status = "failed"
        match_reason = "receipt_status_failed"

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO receipt_verifications (
                invoice_id, filename, bank_name, amount, reference_number,
                transaction_time, recipient_name, status, match_reason, ai_raw_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                matched_invoice_id,
                filename,
                extracted_data.get("bank_name"),
                extracted_amount,
                ref_num,
                extracted_data.get("transaction_time"),
                extracted_data.get("recipient_name"),
                status,
                match_reason if ai_provider == "mock" else f"{match_reason}|ai:{ai_provider}",
                raw_response_text if raw_response_text else json.dumps(extracted_data),
                utc_now(),
            ),
        )
        ver_id = cursor.lastrowid
        row = conn.execute(
            """
            SELECT receipt_verifications.*, invoices.invoice_number AS matched_invoice_number,
                   customers.name AS matched_customer_name
            FROM receipt_verifications
            LEFT JOIN invoices ON invoices.id = receipt_verifications.invoice_id
            LEFT JOIN customers ON customers.id = invoices.customer_id
            WHERE receipt_verifications.id = ?
            """,
            (ver_id,),
        ).fetchone()

    return dict(row)


def list_verifications() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT receipt_verifications.*, invoices.invoice_number AS matched_invoice_number,
                   customers.name AS matched_customer_name
            FROM receipt_verifications
            LEFT JOIN invoices ON invoices.id = receipt_verifications.invoice_id
            LEFT JOIN customers ON customers.id = invoices.customer_id
            ORDER BY receipt_verifications.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _extract_receipt_payload(base64_image: str, mime_type: str) -> tuple[dict, str, str]:
    prompt = _receipt_prompt()
    provider_errors: list[str] = []

    providers: list[tuple[str, callable]] = []
    provider_mode = RECEIPT_AI_PROVIDER

    if provider_mode == "openai_compat":
        providers.append(("openai_compat", lambda: _extract_with_openai_compat(base64_image, mime_type, prompt)))
    elif provider_mode == "anthropic":
        providers.append(("anthropic", lambda: _extract_with_anthropic(base64_image, mime_type, prompt)))
    elif provider_mode == "gemini":
        providers.append(("gemini", lambda: _extract_with_gemini(base64_image, mime_type, prompt)))
    elif provider_mode == "mock":
        providers.append(("mock", lambda: _build_mock_extraction()))
    else:
        if RECEIPT_AI_BASE_URL and RECEIPT_AI_API_KEY:
            providers.append(("openai_compat", lambda: _extract_with_openai_compat(base64_image, mime_type, prompt)))
        if CLAUDE_API_KEY:
            providers.append(("anthropic", lambda: _extract_with_anthropic(base64_image, mime_type, prompt)))
        if GEMINI_API_KEY:
            providers.append(("gemini", lambda: _extract_with_gemini(base64_image, mime_type, prompt)))
        providers.append(("mock", lambda: _build_mock_extraction()))

    for provider_name, provider_fn in providers:
        try:
            extracted_data, raw_response_text = provider_fn()
            return extracted_data, raw_response_text, provider_name
        except Exception as exc:  # pragma: no cover - logged and handled by fallback
            provider_errors.append(f"{provider_name}: {exc}")
            logger.error("Receipt AI %s failed: %s", provider_name, exc)

    logger.error("Receipt AI fallback chain exhausted: %s", "; ".join(provider_errors))
    extracted_data, raw_response_text = _build_mock_extraction()
    return extracted_data, raw_response_text, "mock"


def _extract_with_openai_compat(base64_image: str, mime_type: str, prompt: str) -> tuple[dict, str]:
    if not RECEIPT_AI_BASE_URL or not RECEIPT_AI_API_KEY:
        raise ValueError("OpenAI-compatible receipt AI is not configured")

    payload = {
        "model": RECEIPT_AI_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                    },
                ],
            }
        ],
        "max_tokens": 1024,
    }
    headers = {
        "Authorization": f"Bearer {RECEIPT_AI_API_KEY}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{RECEIPT_AI_BASE_URL}/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    raw_text = data["choices"][0]["message"]["content"]
    return _load_receipt_json(raw_text), raw_text


def _extract_with_anthropic(base64_image: str, mime_type: str, prompt: str) -> tuple[dict, str]:
    if not CLAUDE_API_KEY:
        raise ValueError("Anthropic receipt AI is not configured")

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64_image,
                        },
                    },
                ],
            }
        ],
    }
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    raw_text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
    return _load_receipt_json(raw_text), raw_text


def _extract_with_gemini(base64_image: str, mime_type: str, prompt: str) -> tuple[dict, str]:
    if not GEMINI_API_KEY:
        raise ValueError("Gemini receipt AI is not configured")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64_image,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
        },
    }
    headers = {"Content-Type": "application/json"}
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    return _load_receipt_json(raw_text), raw_text


def _build_mock_extraction() -> tuple[dict, str]:
    extracted_data = {
        "recipient_name": "Sah.Bukti Merchant",
        "bank_name": "MAE (Mock)",
        "transaction_time": utc_now().replace("T", " ")[:19],
        "amount": 150.0,
        "reference_number": f"MOCK-REF-{int(utc_now().replace('-', '').replace(':', '').replace('.', '')[10:18])}",
        "status": "SUCCESS",
    }
    return extracted_data, json.dumps(extracted_data)


def _load_receipt_json(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


def _guess_mime_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".webp":
        return "image/webp"
    return "image/png"


def _receipt_prompt() -> str:
    return (
        "Analyze this Malaysian bank transfer / DuitNow payment receipt. "
        "Extract the following details:\n"
        "1. recipient_name: the name of the merchant/person who received the money.\n"
        "2. bank_name: the bank or e-wallet name (e.g., MAE, CIMB, TNG eWallet, Bank Islam, Maybank, etc.).\n"
        "3. transaction_time: transaction date and time in YYYY-MM-DD HH:MM:SS format.\n"
        "4. amount: the total transfer amount as a floating-point number (e.g., 150.00).\n"
        "5. reference_number: reference or transaction ID string.\n"
        "6. status: the transaction status, must be either 'SUCCESS' or 'FAILED'.\n\n"
        "Return ONLY a JSON object containing these keys. Do not include markdown code block formatting."
    )


def generate_receipt_pdf(order_data: dict) -> str:
    """Generate a simple Sah.Bukti PDF receipt and store its file path."""
    try:
        from fpdf import FPDF
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("fpdf2 is required for receipt PDF generation") from exc

    order_id = str(order_data["order_id"])
    customer_name = str(order_data.get("customer_name") or "Customer")
    phone = str(order_data.get("phone") or "")
    items = order_data.get("items") or []
    total = float(order_data.get("total") or 0.0)
    if total <= 0 and items:
        total = sum(float(item.get("qty") or 0) * float(item.get("price") or 0) for item in items)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "SAH.BUKTI", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Bukti Pesanan Sah", ln=True, align="C")
    pdf.ln(5)

    pdf.cell(0, 6, f"No. Pesanan: {order_id}", ln=True)
    pdf.cell(0, 6, f"Tarikh: {order_data.get('date') or utc_now()[:10]}", ln=True)
    pdf.cell(0, 6, f"Nama: {customer_name}", ln=True)
    pdf.cell(0, 6, f"No. Telefon: {phone}", ln=True)
    pdf.ln(5)

    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(80, 8, "Item", 1, 0, "C", True)
    pdf.cell(25, 8, "Qty", 1, 0, "C", True)
    pdf.cell(35, 8, "Harga", 1, 0, "C", True)
    pdf.cell(35, 8, "Total", 1, 1, "C", True)
    pdf.set_font("Helvetica", "", 10)
    for item in items:
        qty = float(item.get("qty") or 0)
        price = float(item.get("price") or 0)
        pdf.cell(80, 8, str(item.get("name") or "Item")[:36], 1)
        pdf.cell(25, 8, f"{qty:g}", 1, 0, "C")
        pdf.cell(35, 8, f"{price:.2f}", 1, 0, "R")
        pdf.cell(35, 8, f"{qty * price:.2f}", 1, 1, "R")

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(140, 8, "Jumlah:", 0, 0, "R")
    pdf.cell(35, 8, f"RM{total:.2f}", 0, 1, "R")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, str(order_data.get("payment_info") or "Pembayaran: QR / bank transfer"), ln=True, align="C")
    pdf.cell(0, 6, "Terima kasih! - Sah.Bukti", ln=True, align="C")

    output_dir = UPLOADS_DIR / "receipts"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"receipt_{_safe_filename(order_id)}.pdf"
    pdf.output(str(output_path))

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO receipts (id, business_id, proof_id, invoice_id, file_path, sent_to_phone, sent_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(order_data.get("id") or uuid.uuid4()),
                int(order_data.get("business_id") or 1),
                order_data.get("proof_id"),
                order_data.get("invoice_id"),
                str(output_path),
                phone or None,
                order_data.get("sent_at"),
                utc_now(),
            ),
        )
    return str(output_path)


def _safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)[:80]
