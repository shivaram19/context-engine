"""
WhatsApp message handler — WATI webhook integration.

Receives messages from WhatsApp, queries the knowledge base, sends responses via WATI API.

Webhook response is always HTTP 200 immediately (<100ms) — processing happens async.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from infra.config import settings
from infra.container import get_container
from infra.database import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["whatsapp"])

# WATI API client (session-level to reuse connections)
_wati_client: Optional[httpx.AsyncClient] = None


async def get_wati_client() -> httpx.AsyncClient:
    """Get or create WATI HTTP client."""
    global _wati_client
    if _wati_client is None:
        _wati_client = httpx.AsyncClient(
            base_url=settings.wati_api_url,
            headers={"Authorization": f"Bearer {settings.wati_api_key}"},
            timeout=30.0,
        )
    return _wati_client


class WATIIncomingMessage(BaseModel):
    """WATI webhook payload for incoming message."""
    from_phone: str  # Sender's WhatsApp number
    message_type: str  # "text", "image", "document", etc.
    message_body: str  # Message text (empty for non-text)
    timestamp: int  # Unix timestamp


@router.post("/whatsapp")
async def whatsapp_webhook(payload: WATIIncomingMessage, background_tasks: BackgroundTasks):
    """
    Receive WhatsApp message from WATI.

    Always returns 200 immediately (<100ms).
    Processing (query, response) happens in background.
    """
    # Validate message
    if payload.message_type != "text" or not payload.message_body.strip():
        logger.debug(f"[WhatsAppHandler] skipping non-text message from {payload.from_phone}")
        return {"status": "ok"}  # Acknowledge to WATI anyway

    logger.info(f"[WhatsAppHandler] received message from {payload.from_phone}: {len(payload.message_body)} chars")

    # Add processing to background queue
    background_tasks.add_task(
        process_whatsapp_message,
        from_phone=payload.from_phone,
        message_text=payload.message_body,
        timestamp=payload.timestamp,
    )

    # Return 200 immediately to WATI
    return {"status": "ok"}


async def process_whatsapp_message(from_phone: str, message_text: str, timestamp: int) -> None:
    """
    Process WhatsApp message: lookup user, query, send response.

    Runs in background — errors logged but not raised.
    """
    try:
        # 1. Lookup user by phone number
        user_data = await lookup_user_by_phone(from_phone)

        if not user_data:
            # User not found — send registration message
            logger.warning(f"[WhatsAppHandler] user not found for phone {from_phone}")
            await send_wati_message(
                from_phone,
                "You're not registered. Ask your admin to add you to the knowledge base.",
                use_template=False,
                last_message_time=timestamp,
            )
            return

        user_id, org_id, company_name = user_data

        # 2. Query the knowledge base
        container = get_container()
        query_service = container["query_service"]

        result = query_service.query(
            user_id=user_id,
            org_id=org_id,
            query_text=message_text,
            company_name=company_name,
        )

        # 3. Format response
        response_text = format_whatsapp_response(result.answer, result.citations)

        # 4. Send via WATI
        await send_wati_message(
            from_phone,
            response_text,
            use_template=is_session_expired(timestamp),
            last_message_time=timestamp,
        )

        logger.info(f"[WhatsAppHandler] responded to {from_phone} with {len(response_text)} chars")

    except Exception as e:
        logger.error(f"[WhatsAppHandler] failed to process message from {from_phone}: {e}")
        # Don't send error message to user — just log


async def lookup_user_by_phone(whatsapp_phone: str) -> Optional[tuple]:
    """
    Lookup user by WhatsApp phone number.

    Returns (user_id, org_id, company_name) or None if not found.
    """
    try:
        conn = await get_connection()

        row = await conn.fetchrow(
            """
            SELECT u.id, u.org_id, o.name
            FROM users u
            JOIN organisations o ON u.org_id = o.id
            WHERE u.whatsapp_phone = $1
            LIMIT 1
            """,
            whatsapp_phone,
        )

        await conn.close()

        if row:
            return (str(row[0]), str(row[1]), row[2])
        return None

    except Exception as e:
        logger.error(f"[WhatsAppHandler] lookup_user_by_phone failed: {e}")
        return None


def format_whatsapp_response(answer: str, citations: list[dict]) -> str:
    """
    Format QueryResult into WhatsApp message.

    Includes answer + numbered citations.
    """
    response = answer

    if citations:
        response += "\n\nSources:"
        for i, citation in enumerate(citations, 1):
            url = citation.get("url", "")
            title = citation.get("title", "Unknown")
            response += f"\n{i}. {title}\n{url}"

    return response


def is_session_expired(timestamp: int) -> bool:
    """
    Check if session is expired (>24h since last message).

    If expired, use template message instead of session message (WATI requirement).
    """
    message_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - message_time

    return delta > timedelta(hours=24)


async def send_wati_message(
    from_phone: str,
    message_text: str,
    use_template: bool = False,
    last_message_time: int = None,
) -> None:
    """
    Send message via WATI API.

    Uses session message endpoint (fast, in-session) if session active.
    Uses template message endpoint if session expired (requires template).

    Args:
        from_phone: Recipient WhatsApp number
        message_text: Message to send
        use_template: If True, use template message API (slower but works for expired sessions)
        last_message_time: Unix timestamp of last message (for session expiry check)
    """
    try:
        client = await get_wati_client()

        payload = {
            "customParams": {},
            "messageText": message_text,
        }

        # Choose endpoint based on session status
        if use_template:
            # Template message (for expired sessions)
            # Note: real implementation would use a template with placeholder
            endpoint = f"/api/sendTemplateMessage/{from_phone}"
            payload["templateName"] = "knowledge_base_response"  # pre-created template
        else:
            # Session message (fast, in-session)
            endpoint = f"/api/sendSessionMessage/{from_phone}"

        response = await client.post(endpoint, json=payload)
        response.raise_for_status()

        logger.debug(f"[WhatsAppHandler] sent message to {from_phone} via {endpoint}")

    except Exception as e:
        logger.error(f"[WhatsAppHandler] failed to send WATI message to {from_phone}: {e}")
        # Don't raise — message loss is not critical


async def close_wati_client() -> None:
    """Close WATI HTTP client on shutdown."""
    global _wati_client
    if _wati_client:
        await _wati_client.aclose()
        _wati_client = None
        logger.debug("[WhatsAppHandler] WATI client closed")
