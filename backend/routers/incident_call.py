"""CORTEX incident calling router: outbound Vapi calls and inbound Vapi webhooks.

Required environment variables:
    VAPI_API_KEY
    VAPI_ASSISTANT_ID
    VAPI_PHONE_NUMBER_ID

Optional environment variables:
    VAPI_API_URL             Defaults to https://api.vapi.ai
    VAPI_WEBHOOK_SECRET      Shared secret expected in X-Cortex-Webhook-Secret

Mount the router with:
    app.include_router(incident.router, prefix="/api")

Vapi Server URL:
    https://YOUR_PUBLIC_HOST/api/incident-calls

POST /api/incident-calls
    - Vapi webhook payload containing "message": authenticate and store event.
    - Incident request containing "customer_number" and incident fields: create call.

GET /api/incident-calls/{call_id}
    Retrieve the state and result known to this process.

IMPORTANT: CALL_RESULTS and IDEMPOTENCY_KEYS are in-memory development stores.
Use a database/Redis and atomic idempotency handling for production.
"""

from __future__ import annotations

import hmac
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/incident-calls", tags=["Incident Calls"])

VAPI_API_URL = os.getenv("VAPI_API_URL", "https://api.vapi.ai").rstrip("/")
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID")
VAPI_WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET")

# Development-only stores. These are not shared between workers and reset on restart.
CALL_RESULTS: dict[str, dict[str, Any]] = {}
IDEMPOTENCY_KEYS: dict[str, str] = {}


class IncidentCallRequest(BaseModel):
    """Payload the CORTEX orchestrator sends to initiate an incident call."""

    model_config = ConfigDict(extra="allow")

    customer_number: str = Field(
        ...,
        description="Recipient phone number in E.164 format, e.g. +919876543210",
    )
    recipient_name: str = Field(default="there", min_length=1, max_length=100)
    recipient_role: str = Field(default="Responsible operator", max_length=120)

    incident_id: str = Field(..., min_length=1, max_length=100)
    incident_title: str = Field(..., min_length=1, max_length=200)
    detected_at: str | None = None
    facility_name: str | None = None
    asset: str = Field(..., min_length=1, max_length=200)
    affected_system: str | None = None
    issue: str = Field(..., min_length=1, max_length=1000)
    severity: Literal["Critical", "High", "Medium", "Low", "Informational"] = "High"
    incident_status: str = "Open"

    rca_summary: str | None = None
    root_cause: str | None = None
    supporting_evidence: str | None = None
    telemetry: str | None = None
    impact: str | None = None
    recommended_action: str = Field(..., min_length=1, max_length=1500)
    response_deadline: str | None = None

    escalation_criteria: str | None = None
    escalation_contact: str | None = None
    additional_instructions: str | None = None
    call_objective: str = (
        "Explain the incident, communicate the required action, and obtain acknowledgement."
    )
    required_acknowledgement: str = (
        "Confirm whether you can take responsibility for the recommended action."
    )
    request_id: str | None = Field(
        default=None,
        max_length=200,
        description="Optional idempotency key to reduce duplicate calls on retries.",
    )

    @field_validator("customer_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        value = value.strip()
        # E.164: leading +, first digit 1-9, and 8-15 digits total.
        if not re.fullmatch(r"\+[1-9]\d{7,14}", value):
            raise ValueError(
                "customer_number must be E.164, for example +919876543210"
            )
        return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_vapi_config() -> None:
    missing = [
        key
        for key, value in (
            ("VAPI_API_KEY", VAPI_API_KEY),
            ("VAPI_ASSISTANT_ID", VAPI_ASSISTANT_ID),
            ("VAPI_PHONE_NUMBER_ID", VAPI_PHONE_NUMBER_ID),
        )
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Missing Vapi configuration: {', '.join(missing)}",
        )


def _first_message(incident: IncidentCallRequest) -> str:
    """Build an opening message using supplied incident values."""
    message = (
        f"Hello {incident.recipient_name}. This is Cortex. "
        f"{incident.severity} alert for {incident.asset}: {incident.issue} "
    )
    if incident.root_cause:
        message += f"The suspected cause is {incident.root_cause}. "
    elif incident.rca_summary:
        message += f"The current root-cause analysis is {incident.rca_summary}. "

    message += f"Please arrange this action: {incident.recommended_action}. "
    if incident.response_deadline:
        message += f"The response deadline is {incident.response_deadline}. "
    return message + "Can you take responsibility for this?"


def _get_call_id(message: dict[str, Any]) -> str | None:
    call = message.get("call")
    if isinstance(call, dict) and call.get("id"):
        return str(call["id"])
    value = message.get("callId") or message.get("call_id")
    return str(value) if value else None


def _new_call_record(call_id: str) -> dict[str, Any]:
    now = _now()
    return {
        "call_id": call_id,
        "status": "unknown",
        "events": [],
        "created_at": now,
        "updated_at": now,
        "outcome": {
            "acknowledgement": "unknown",
            "action_committed": None,
            "escalation_required": None,
            "resolution_verified": False,
        },
    }


def _handle_vapi_webhook(body: dict[str, Any]) -> dict[str, Any]:
    message = body.get("message")
    if not isinstance(message, dict):
        raise HTTPException(status_code=400, detail="Expected a 'message' object.")

    event_type = str(message.get("type", "unknown"))
    call_id = _get_call_id(message)
    if not call_id:
        # Some Vapi events may not be associated with a call.
        return {"received": True, "event_type": event_type, "stored": False}

    record = CALL_RESULTS.setdefault(call_id, _new_call_record(call_id))
    call = message.get("call")
    if isinstance(call, dict):
        record["vapi_call"] = call
        incoming_status = call.get("status")
        if incoming_status:
            # Do not let a later status event regress a completed call.
            if record.get("status") != "ended" or incoming_status == "ended":
                record["status"] = incoming_status

        customer = call.get("customer")
        if isinstance(customer, dict) and customer.get("number"):
            record["customer_number"] = customer["number"]

        duration = call.get("durationSeconds") or call.get("duration")
        if duration is not None:
            record["duration_seconds"] = duration

    if event_type == "status-update":
        incoming_status = message.get("status")
        if incoming_status and record.get("status") != "ended":
            record["status"] = incoming_status

    artifact = message.get("artifact")
    if isinstance(artifact, dict):
        record["artifact"] = artifact
        if "transcript" in artifact:
            record["transcript"] = artifact["transcript"]
        if "messages" in artifact:
            record["messages"] = artifact["messages"]
        if "recording" in artifact:
            record["recording"] = artifact["recording"]
        if "recordingUrl" in artifact:
            record["recording_url"] = artifact["recordingUrl"]

    analysis = message.get("analysis")
    if isinstance(analysis, dict):
        record["analysis"] = analysis

    if event_type == "transcript" and message.get("transcript"):
        record.setdefault("transcript_events", []).append(
            {
                "role": message.get("role"),
                "transcript_type": message.get("transcriptType"),
                "transcript": message["transcript"],
                "received_at": _now(),
            }
        )

    if event_type == "end-of-call-report":
        record["status"] = "ended"
        record["ended_reason"] = message.get("endedReason")
        record["completed_at"] = _now()

    record["last_event_type"] = event_type
    record["updated_at"] = _now()
    record.setdefault("events", []).append(
        {"type": event_type, "received_at": _now()}
    )

    return {
        "received": True,
        "event_type": event_type,
        "call_id": call_id,
        "stored": True,
        "status": record.get("status"),
    }


async def _create_call(incident: IncidentCallRequest) -> dict[str, Any]:
    _require_vapi_config()

    # Orchestration-only fields are kept out of assistant variable values.
    variables = incident.model_dump(exclude={"customer_number", "request_id"})
    payload = {
        "assistantId": VAPI_ASSISTANT_ID,
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": incident.customer_number,
            "name": incident.recipient_name,
        },
        "assistantOverrides": {
            "variableValues": variables,
            "firstMessage": _first_message(incident),
        },
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                f"{VAPI_API_URL}/call",
                headers={
                    "Authorization": f"Bearer {VAPI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail=(
                "Vapi request timed out. Check Vapi call logs before retrying; "
                "the call might already have been created."
            ),
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("Vapi API request failed")
        raise HTTPException(status_code=502, detail="Could not reach Vapi.") from exc

    try:
        data = response.json()
    except ValueError:
        data = {"response_text": response.text}

    if not response.is_success:
        logger.error("Vapi rejected call request with HTTP %s", response.status_code)
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Vapi rejected the call request.",
                "vapi_status_code": response.status_code,
                "vapi_response": data,
            },
        )

    call_id = data.get("id") if isinstance(data, dict) else None
    if not call_id:
        raise HTTPException(status_code=502, detail="Vapi returned no call ID.")
    call_id = str(call_id)

    # Merge instead of replacing: a webhook can arrive before this response is stored.
    existing = CALL_RESULTS.get(call_id, {})
    default_outcome = {
        "acknowledgement": "unknown",
        "action_committed": None,
        "escalation_required": None,
        "resolution_verified": False,
    }
    CALL_RESULTS[call_id] = {
        **existing,
        "call_id": call_id,
        "incident_id": incident.incident_id,
        "incident_title": incident.incident_title,
        "customer_number": existing.get("customer_number", incident.customer_number),
        "recipient_name": incident.recipient_name,
        # Preserve a terminal status received from a webhook.
        "status": (
            "ended"
            if existing.get("status") == "ended"
            else data.get("status", existing.get("status", "queued"))
        ),
        "created_at": existing.get("created_at", _now()),
        "updated_at": _now(),
        "request_id": incident.request_id,
        "vapi_call": {**existing.get("vapi_call", {}), **data},
        "transcript": existing.get("transcript"),
        "analysis": existing.get("analysis"),
        "events": existing.get("events", []),
        "outcome": existing.get("outcome", default_outcome),
    }

    if incident.request_id:
        IDEMPOTENCY_KEYS[incident.request_id] = call_id

    return {
        "accepted": True,
        "call_id": call_id,
        "status": CALL_RESULTS[call_id]["status"],
        "incident_id": incident.incident_id,
        "message": (
            "Vapi accepted the call request; this does not prove the recipient "
            "answered or agreed to the action."
        ),
        "result_url": f"/incident-calls/{call_id}",
    }


@router.post("", summary="Create an outbound incident call or receive a Vapi webhook")
async def incident_call_endpoint(
    request: Request,
    x_cortex_webhook_secret: str | None = Header(
        default=None, alias="X-Cortex-Webhook-Secret"
    ),
) -> dict[str, Any]:
    """Handle either a Vapi webhook or an outbound incident-call request."""
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Body must be valid JSON.") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object.")

    # Vapi callbacks have the shape {"message": {"type": ...}}.
    if "message" in body:
        if VAPI_WEBHOOK_SECRET and (
            not x_cortex_webhook_secret
            or not hmac.compare_digest(x_cortex_webhook_secret, VAPI_WEBHOOK_SECRET)
        ):
            raise HTTPException(status_code=401, detail="Invalid webhook secret.")
        return _handle_vapi_webhook(body)

    try:
        incident = IncidentCallRequest.model_validate(body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Development-only idempotency. Use atomic persistent storage in production.
    if incident.request_id and incident.request_id in IDEMPOTENCY_KEYS:
        existing_id = IDEMPOTENCY_KEYS[incident.request_id]
        existing = CALL_RESULTS.get(existing_id, {})
        return {
            "accepted": True,
            "duplicate_request": True,
            "call_id": existing_id,
            "status": existing.get("status", "unknown"),
            "incident_id": existing.get("incident_id"),
            "result_url": f"/incident-calls/{existing_id}",
        }

    return await _create_call(incident)


@router.get("/{call_id}", summary="Get call status, transcript, and analysis")
async def get_incident_call(
    call_id: str,
    include_raw: bool = Query(default=False),
) -> dict[str, Any]:
    record = CALL_RESULTS.get(call_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=(
                "Call not found in this process. The call may be unknown, or "
                "the development in-memory store may have restarted."
            ),
        )

    result = {
        "call_id": record.get("call_id"),
        "incident_id": record.get("incident_id"),
        "incident_title": record.get("incident_title"),
        "customer_number": record.get("customer_number"),
        "recipient_name": record.get("recipient_name"),
        "status": record.get("status"),
        "ended_reason": record.get("ended_reason"),
        "duration_seconds": record.get("duration_seconds"),
        "transcript": record.get("transcript"),
        "messages": record.get("messages"),
        "transcript_events": record.get("transcript_events", []),
        "analysis": record.get("analysis"),
        "outcome": record.get("outcome"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
        "completed_at": record.get("completed_at"),
        "last_event_type": record.get("last_event_type"),
        "events": record.get("events", []),
    }
    if include_raw:
        result["vapi_call"] = record.get("vapi_call")
        result["artifact"] = record.get("artifact")
    return result
