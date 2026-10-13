
import os
import hmac
import hashlib
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")
API_VERSION = os.getenv("WHATSAPP_API_VERSION", "")

# Temporary in-memory storage. Use a database in production.
MESSAGES: dict[str, dict[str, Any]] = {}


class SendMessageRequest(BaseModel):
    to: str = Field(
        description="Recipient number, e.g. 919876543210"
    )
    body: str = Field(min_length=1, max_length=4096)


def get_config():
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID or not API_VERSION:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp Cloud API credentials are not configured.",
        )

    return ACCESS_TOKEN, PHONE_NUMBER_ID


def verify_signature(raw_body: bytes, signature: str) -> bool:
    if not APP_SECRET or not signature.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        APP_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@router.post("/send")
async def send_message(payload: SendMessageRequest):
    token, phone_number_id = get_config()

    # Accept either 919876543210 or +919876543210.
    recipient = payload.to.strip().replace("+", "")

    if not recipient.isdigit() or not recipient or recipient.startswith("0"):
        raise HTTPException(
            status_code=422,
            detail="Use an international phone number, e.g. 919876543210.",
        )

    url = (
        f"https://graph.facebook.com/{API_VERSION}/"
        f"{phone_number_id}/messages"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": payload.body,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=20) as http:
            response = await http.post(
                url,
                headers=headers,
                json=body,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to WhatsApp Cloud API.",
        ) from exc

    try:
        result = response.json()
    except ValueError:
        result = {"error": {"message": "Invalid response from Meta."}}

    if not response.is_success:
        # Meta's error response helps diagnose invalid tokens,
        # recipient restrictions, permissions, and API errors.
        raise HTTPException(
            status_code=response.status_code,
            detail=result,
        )

    messages = result.get("messages", [])
    message_id = messages[0].get("id") if messages else None

    if message_id:
        MESSAGES[message_id] = {
            "id": message_id,
            "to": recipient,
            "status": "accepted",
        }

    return {
        "hello": "hello",
        "message_id": message_id,
        "status": "accepted",
        "to": recipient,
    }


# Meta calls this GET endpoint when verifying your webhook.
@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
):
    if (
        hub_mode == "subscribe"
        and VERIFY_TOKEN
        and hmac.compare_digest(hub_verify_token, VERIFY_TOKEN)
    ):
        return PlainTextResponse(hub_challenge)

    raise HTTPException(
        status_code=403,
        detail="Webhook verification failed.",
    )


# Meta sends incoming messages and delivery updates here.
@router.post("/webhook")
async def receive_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(raw_body, signature):
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook signature.",
        )

    try:
        data = await request.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON.",
        ) from exc

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Incoming WhatsApp messages.
            for incoming in value.get("messages", []):
                sender = incoming.get("from")
                message_type = incoming.get("type")
                message_id = incoming.get("id")

                text_body = (
                    incoming.get("text", {}).get("body")
                    if message_type == "text"
                    else None
                )

                print(
                    f"WhatsApp incoming: from={sender}, "
                    f"type={message_type}, body={text_body}"
                )

                if message_id:
                    MESSAGES[message_id] = {
                        "id": message_id,
                        "from": sender,
                        "type": message_type,
                        "body": text_body,
                        "status": "received",
                    }

            # Delivery-status callbacks for messages sent by us.
            for status_event in value.get("statuses", []):
                message_id = status_event.get("id")

                if message_id:
                    MESSAGES.setdefault(
                        message_id,
                        {"id": message_id},
                    )
                    MESSAGES[message_id].update({
                        "status": status_event.get("status"),
                        "recipient_id": status_event.get("recipient_id"),
                        "errors": status_event.get("errors"),
                    })

    return {
        "hello": "hello",
        "received": True,
    }


@router.get("/messages/{message_id}")
async def get_message(message_id: str):
    message = MESSAGES.get(message_id)

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Message not found in local webhook history.",
        )

    return {
        "hello": "hello",
        **message,
    }
