from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
import logging

from app.api.dependencies import BusinessContext, get_business_context, get_business_context_demo
from app.db.store import get_default_business_id
from app.config import DEFAULT_OWNER_WHATSAPP, SAHBUKTI_WEBHOOK_SECRET, WHATSAPP_ALLOWED_NUMBERS, WHATSAPP_LINK_UI_ENABLED, WHATSAPP_PROVIDER
from app.schemas.whatsapp import WhatsAppWebhookRequest, WhatsAppWebhookResponse
from app.services.auth import business_has_members, get_business
from app.services.business_profile import bind_whatsapp_group
from app.services.evidence import ingest_whatsapp_evidence
from app.services.whatsapp import (
    SahBuktiAgent,
    extract_document_text,
    format_evidence_ack,
    get_whatsapp_client,
    _normalize_agent_command,
)


router = APIRouter()
logger = logging.getLogger(__name__)


def _normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    return str(value).split("@", 1)[0].strip()


def _resolve_allowed_private_numbers(business: dict) -> set[str]:
    owner_phone = _normalize_phone(business.get("owner_whatsapp"))
    allowed = {_normalize_phone(number) for number in WHATSAPP_ALLOWED_NUMBERS if _normalize_phone(number)}
    if not owner_phone:
        owner_phone = _normalize_phone(DEFAULT_OWNER_WHATSAPP)
    if owner_phone:
        allowed.add(owner_phone)
    return {number for number in allowed if number}


def whatsapp_webhook_route(
    payload: WhatsAppWebhookRequest,
    x_sahbukti_webhook_secret: str | None = None,
    token: str | None = None,
) -> dict:
    return _handle_whatsapp_webhook_payload(
        raw=payload.model_dump(by_alias=True),
        x_sahbukti_webhook_secret=x_sahbukti_webhook_secret,
        token=token,
    )


@router.post("/webhook/whatsapp", response_model=WhatsAppWebhookResponse, status_code=status.HTTP_201_CREATED)
@router.post("/whatsapp/webhook", response_model=WhatsAppWebhookResponse, status_code=status.HTTP_201_CREATED)
async def whatsapp_webhook_http_route(
    request: Request,
    x_sahbukti_webhook_secret: str | None = Header(default=None, alias="x-sahbukti-webhook-secret"),
    token: str | None = Query(default=None),
) -> dict:
    raw = await request.json()
    return _handle_whatsapp_webhook_payload(
        raw=raw,
        x_sahbukti_webhook_secret=x_sahbukti_webhook_secret,
        token=token,
    )


def _handle_whatsapp_webhook_payload(
    *,
    raw: dict,
    x_sahbukti_webhook_secret: str | None,
    token: str | None,
) -> dict:
    if not SAHBUKTI_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="WhatsApp webhook secret is not configured")
    if x_sahbukti_webhook_secret != SAHBUKTI_WEBHOOK_SECRET and token != SAHBUKTI_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    normalized = _normalize_whatsapp_payload(raw)
    business_id = normalized["business_id"]
    if normalized.get("media_type") != "text" or (normalized.get("media_metadata") or {}).get("has_media"):
        logger.info(
            "WhatsApp webhook normalized: business_id=%s from_phone=%s reply_target=%s is_group=%s from_me=%s media_type=%s event=%s metadata=%s raw_keys=%s payload_keys=%s",
            business_id,
            normalized.get("from_phone"),
            normalized.get("reply_target"),
            normalized.get("is_group"),
            normalized.get("from_me"),
            normalized.get("media_type"),
            normalized.get("event"),
            normalized.get("media_metadata"),
            sorted((raw or {}).keys()),
            sorted(((raw or {}).get("payload") or {}).keys()) if isinstance((raw or {}).get("payload"), dict) else [],
        )
    if not get_business(business_id) or not business_has_members(business_id):
        raise HTTPException(status_code=403, detail="Business webhook target denied")

    business = get_business(business_id) or {}
    owner_phone = _normalize_phone(business.get("owner_whatsapp") or DEFAULT_OWNER_WHATSAPP)
    allowed_private_numbers = _resolve_allowed_private_numbers(business)

    # Private only, allow only explicitly trusted numbers.
    if allowed_private_numbers and _normalize_phone(normalized["from_phone"]) not in allowed_private_numbers:
        if normalized.get("media_type") != "text" or (normalized.get("media_metadata") or {}).get("has_media"):
            logger.info(
                "WhatsApp webhook ignored not-allowed: allowed=%s normalized_from=%s chat_id=%s metadata=%s",
                sorted(allowed_private_numbers),
                normalized.get("from_phone"),
                normalized.get("chat_id"),
                normalized.get("media_metadata"),
            )
        return {"invoice_number": "IGNORED_NOT_ALLOWED", "total": 0.0, "customer_name": normalized["from_phone"]}

    # Reject all group messages.
    if normalized.get("is_group"):
        if normalized.get("media_type") != "text" or (normalized.get("media_metadata") or {}).get("has_media"):
            logger.info(
                "WhatsApp webhook ignored group: allowed=%s normalized_from=%s chat_id=%s metadata=%s",
                sorted(allowed_private_numbers),
                normalized.get("from_phone"),
                normalized.get("chat_id"),
                normalized.get("media_metadata"),
            )
        return {"invoice_number": "IGNORED_GROUP", "total": 0.0, "customer_name": normalized["from_phone"]}

    phone = normalized["from_phone"]
    reply_target = normalized.get("reply_target") or phone
    message = normalized["message"]
    transcript = normalized.get("transcript")
    media_type = normalized.get("media_type") or "text"
    media_metadata = normalized.get("media_metadata") or {}
    if "event" not in raw:
        result = ingest_whatsapp_evidence(
            business_id=business_id,
            from_phone=phone,
            message=message,
            transcript=transcript,
            media_type=media_type,
            media_metadata=media_metadata,
        )
        get_whatsapp_client().send_message(reply_target, format_evidence_ack(result))
        return {
            "invoice_number": result["invoice"]["invoice_number"] if result.get("invoice") else (result["payment_proof"]["extracted_reference"] or "REVIEW-PENDING"),
            "total": result["invoice"]["total"] if result.get("invoice") else float(result["payment_proof"]["extracted_amount"] or 0.0),
            "customer_name": result["invoice"]["customer_name"] if result.get("invoice") else phone,
        }

    if _should_ignore_whatsapp_message(normalized):
        if normalized.get("media_type") != "text" or (normalized.get("media_metadata") or {}).get("has_media"):
            logger.info(
                "WhatsApp webhook ignored by filter: from_phone=%s media_type=%s transcript=%s message=%s metadata=%s",
                normalized.get("from_phone"),
                normalized.get("media_type"),
                bool(normalized.get("transcript")),
                bool(normalized.get("message")),
                normalized.get("media_metadata"),
            )
        return {"invoice_number": "IGNORED", "total": 0.0, "customer_name": phone}

    agent = SahBuktiAgent(business_id=business_id, owner_phone=business.get("owner_whatsapp") or "")
    normalized_command = _normalize_agent_command(message)
    command = normalized_command.lower().split()[0] if normalized_command else ""
    if media_type == "text" and command in agent.TOOLS and (not owner_phone or _normalize_phone(phone) == owner_phone):
        reply = agent.route(phone, message)
    else:
        result = ingest_whatsapp_evidence(
            business_id=business_id,
            from_phone=phone,
            message=message,
            transcript=transcript,
            media_type=media_type,
            media_metadata=media_metadata,
        )
        if media_type != "text" or media_metadata.get("has_media"):
            logger.info(
                "WhatsApp evidence created: intent=%s proof_id=%s invoice_id=%s review_state=%s metadata=%s",
                result.get("intent"),
                (result.get("payment_proof") or {}).get("id"),
                (result.get("invoice") or {}).get("id"),
                (result.get("payment_proof") or {}).get("review_state"),
                media_metadata,
            )
        reply = format_evidence_ack(result)

    whatsapp = get_whatsapp_client()
    whatsapp.send_message(reply_target, reply)
    proof_ids = agent.get_pending_proof_ids()
    if proof_ids and WHATSAPP_PROVIDER == "waha":
        if reply.startswith("Pending proofs:"):
            primary_id = proof_ids[0]
            whatsapp.send_buttons(
                reply_target,
                "Quick actions",
                [f"Approve #{primary_id}", f"Reject #{primary_id}", "Status"],
            )
        elif reply.startswith("Proof #"):
            latest_id = proof_ids[0]
            whatsapp.send_buttons(
                reply_target,
                "Review this proof",
                [f"Approve #{latest_id}", f"Reject #{latest_id}", "Status"],
            )

    return {
        "invoice_number": normalized.get("reference") or "REVIEW-PENDING",
        "total": float(normalized.get("amount") or 0.0),
        "customer_name": phone,
    }


@router.post("/agent/command")
@router.post("/whatsapp/agent/command")
def agent_command_route(
    payload: dict,
    ctx: BusinessContext = Depends(get_business_context_demo),
) -> dict:
    phone = str(payload.get("from_phone") or payload.get("from") or "").strip()
    message = str(payload.get("message") or "").strip()
    if not phone or not message:
        raise HTTPException(status_code=400, detail="from_phone and message are required")

    owner_phone = _normalize_phone(ctx.business.get("owner_whatsapp") or DEFAULT_OWNER_WHATSAPP)
    if _normalize_phone(phone) != owner_phone:
        return {"reply": "Only owner can run commands", "sent": False}

    agent = SahBuktiAgent(
        business_id=ctx.business_id,
        owner_phone=owner_phone,
    )
    reply = agent.route(phone, message)
    send_result = get_whatsapp_client().send_message(phone, reply)
    return {
        "reply": reply,
        "sent": send_result.ok,
        "provider": send_result.provider,
        "detail": send_result.detail,
    }


@router.get("/whatsapp/session")
def whatsapp_session_route(ctx: BusinessContext = Depends(get_business_context_demo)) -> dict:  # noqa: ARG001
    client = get_whatsapp_client()
    session = client.get_session_info()
    engine_state = str((session.get("engine") or {}).get("state") or session.get("status") or "").upper()
    return {
        "name": session.get("name") or "default",
        "status": "CONNECTED" if engine_state == "CONNECTED" else engine_state or "UNKNOWN",
        "link_ui_enabled": WHATSAPP_LINK_UI_ENABLED,
    }


@router.get("/whatsapp/session/qr")
def whatsapp_session_qr_route(ctx: BusinessContext = Depends(get_business_context_demo)) -> dict:  # noqa: ARG001
    if not WHATSAPP_LINK_UI_ENABLED:
        return {"ok": False, "detail": "WhatsApp linking is disabled on the public demo."}
    client = get_whatsapp_client()
    return client.get_qr_payload()


def _normalize_whatsapp_payload(raw: dict) -> dict:
    if "event" in raw and "payload" in raw:
        payload = raw.get("payload") or {}
        chat_target = str(payload.get("chatId") or payload.get("from") or "").strip()
        is_group = chat_target.endswith("@g.us")
        sender_target = str(payload.get("participant") or payload.get("author") or payload.get("from") or payload.get("chatId") or "").strip()
        # WAHA/WPP self-chat and some private forwards can surface synthetic LID-like
        # sender ids such as `false_...@lid_...` even when chatId still carries the
        # real owner phone in `6012...@c.us`. In that case prefer the chat target.
        if (
            not is_group
            and chat_target.endswith(("@c.us", "@s.whatsapp.net"))
            and (
                sender_target.startswith("false_")
                or "@lid" in sender_target
            )
        ):
            sender_target = chat_target
        phone = sender_target.split("@", 1)[0]
        media = payload.get("media") if isinstance(payload.get("media"), dict) else {}
        payload_type = str(payload.get("type") or raw.get("event") or "").lower()
        media_mimetype = str(media.get("mimetype") or "").lower()
        media_filename = str(media.get("filename") or "").strip() or None
        body = str(payload.get("body") or payload.get("caption") or payload.get("text") or "").strip()
        media_type = "text"
        if media_mimetype:
            if "pdf" in media_mimetype:
                media_type = "document"
            elif media_mimetype.startswith("image/"):
                media_type = "receipt_image"
            elif media_mimetype.startswith("audio/"):
                media_type = "voice_note"
            else:
                media_type = "document"
        elif payload_type in {"document", "application"}:
            media_type = "document"
        elif payload_type in {"image", "photo"}:
            media_type = "receipt_image"
        elif payload_type in {"audio", "ptt", "voice", "voice_note"}:
            media_type = "voice_note"
        downloaded = get_whatsapp_client().download_media(media)
        document_text = None
        if downloaded:
            document_text = extract_document_text(
                downloaded["content"],
                downloaded.get("mime_type"),
                downloaded.get("filename"),
            )
        if not body and document_text:
            body = document_text
        if media_type != "text":
            logger.info(
                "WhatsApp inbound media: event=%s type=%s has_media=%s mimetype=%s filename=%s url=%s from=%s",
                raw.get("event"),
                payload_type,
                bool(payload.get("hasMedia")),
                media_mimetype or None,
                media_filename,
                bool(media.get("url")),
                phone,
            )
        business_id = int(raw.get("business_id") or payload.get("business_id") or get_default_business_id())
        return {
            "business_id": business_id,
            "from_phone": phone,
            "reply_target": chat_target or phone,
            "message": body,
            "transcript": document_text,
            "media_type": media_type,
            "media_metadata": {
                "event_id": raw.get("id") or raw.get("eventId") or raw.get("event_id"),
                "message_id": payload.get("id") or payload.get("_data", {}).get("id", {}).get("_serialized"),
                "filename": media_filename,
                "mimetype": media_mimetype or None,
                "has_media": bool(payload.get("hasMedia")),
                "media_url": media.get("url"),
                "group_name": (
                    payload.get("notifyName")
                    or (payload.get("_data") or {}).get("notifyName")
                    or (payload.get("_data") or {}).get("chat", {}).get("formattedTitle")
                ),
            },
            "from_me": bool(payload.get("fromMe")),
            "event": raw.get("event"),
            "amount": None,
            "reference": None,
            "chat_id": chat_target,
            "is_group": is_group,
            "group_name": (
                payload.get("notifyName")
                or (payload.get("_data") or {}).get("notifyName")
                or (payload.get("_data") or {}).get("chat", {}).get("formattedTitle")
            ),
        }
    phone = str(raw.get("from") or raw.get("from_phone") or "").strip()
    return {
        "business_id": int(raw.get("business_id") or get_default_business_id()),
        "from_phone": phone,
        "reply_target": str(raw.get("reply_target") or raw.get("chat_id") or phone).strip(),
        "message": str(raw.get("message") or "").strip(),
        "transcript": str(raw.get("transcript") or "").strip() or None,
        "media_type": str(raw.get("media_type") or "text").strip() or "text",
        "media_metadata": raw.get("media_metadata") or {},
        "from_me": False,
        "event": "manual",
        "amount": None,
        "reference": None,
        "chat_id": str(raw.get("chat_id") or phone).strip(),
        "is_group": str(raw.get("chat_id") or "").strip().endswith("@g.us"),
        "group_name": raw.get("group_name"),
    }


def _should_ignore_whatsapp_message(payload: dict) -> bool:
    message = (payload.get("message") or "").strip()
    transcript = (payload.get("transcript") or "").strip()
    media_type = (payload.get("media_type") or "text").strip().lower()
    media_metadata = payload.get("media_metadata") or {}
    has_media = bool(media_metadata.get("has_media")) or media_type != "text"
    if not message:
        if transcript or has_media:
            return False
        return True
    if not payload.get("from_me"):
        return False
    auto_prefixes = (
        "Proof #",
        "Pending proofs:",
        "Laporan Harian",
        "MENU",
        "SAH.BUKTI COMMANDS",
        "Receipt generated:",
        "Reminder queued",
        "Failed to",
        "Usage:",
    )
    return message.startswith(auto_prefixes)
