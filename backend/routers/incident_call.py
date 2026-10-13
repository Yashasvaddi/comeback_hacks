"""CORTEX incident calling router: outbound Vapi calls and inbound Vapi webhooks.

Required environment variables:
    VAPI_API_KEY
    VAPI_ASSISTANT_ID
    VAPI_PHONE_NUMBER_ID

Optional:
    VAPI_API_URL             Defaults to https://api.vapi.ai
    VAPI_WEBHOOK_SECRET      Token configured in the Vapi dashboard webhook
                             credential. Accepts raw Authorization token,
                             Bearer token, or x-vapi-secret for compatibility.

Mount with:
    app.include_router(incident_call.router, prefix="/api")

Endpoints:
    POST /api/incident-calls          Create an outbound Vapi call (backend auth
                                      is provided by the internal API deployment).
    POST /api/incident-calls/webhook  Receive and authenticate Vapi webhooks.
    GET  /api/incident-calls/{call_id} Retrieve state held by this process.

CALL_RESULTS and IDEMPOTENCY_KEYS are in-memory development stores. Use persistent
storage and atomic idempotency handling in production.
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



# Vapi event types that require an explicit response body during the call.

# Returning a generic {"received": True} for these causes the assistant to stall.

_VAPI_SERVER_MESSAGE_TYPES = {

    "assistant-request",

    "function-call",

    "tool-calls",

    "transfer-destination-request",

}





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
    escalation_phone_number: str | None = None

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





def _advance_status(record: dict[str, Any], new_status: str | None) -> None:

    """Update call status only if the transition is a forward one."""

    if not new_status:

        return

    terminal = record.get("status") == "ended"

    if not terminal:

        record["status"] = new_status





def _handle_vapi_webhook(body: dict[str, Any]) -> dict[str, Any]:

    message = body.get("message")

    if not isinstance(message, dict):

        raise HTTPException(status_code=400, detail="Expected a 'message' object.")



    event_type = str(message.get("type", "unknown"))

    call_id = _get_call_id(message)



    # --- Server messages that need a response DURING the call ---

    # Return early with the required shape so the assistant is not left hanging.

    if event_type in _VAPI_SERVER_MESSAGE_TYPES:

        logger.info("Received Vapi server message type=%s call_id=%s", event_type, call_id)

        if event_type == "assistant-request":

            # Vapi wants us to nominate an assistantId to use.

            # Return the configured assistant; fall back to a no-op if unset.

            return {

                "assistantId": VAPI_ASSISTANT_ID or "",

            }

        if event_type in ("function-call", "tool-calls"):

            # We do not expose custom tools yet — acknowledge with empty results

            # so the assistant can continue rather than timing out.

            tool_call_list = message.get("toolCallList") or []

            results = [

                {

                    "toolCallId": tc.get("id", ""),

                    "result": "Tool not implemented on this server.",

                }

                for tc in tool_call_list

            ]

            return {"results": results}

        # transfer-destination-request and any future types

        return {"received": True, "event_type": event_type}



    # --- Persistent event types (status updates, transcripts, end-of-call) ---

    if not call_id:

        return {"received": True, "event_type": event_type, "stored": False}



    record = CALL_RESULTS.setdefault(call_id, _new_call_record(call_id))



    # Merge the nested call object if present.

    call_obj = message.get("call")

    if isinstance(call_obj, dict):

        record["vapi_call"] = call_obj

        _advance_status(record, call_obj.get("status"))



        customer = call_obj.get("customer")

        if isinstance(customer, dict) and customer.get("number"):

            record["customer_number"] = customer["number"]



        duration = call_obj.get("durationSeconds") or call_obj.get("duration")

        if duration is not None:

            record["duration_seconds"] = duration



    # Top-level status field (sent by status-update events).

    if event_type == "status-update":

        _advance_status(record, message.get("status"))



    # Artifact (transcript, messages, recording).

    artifact = message.get("artifact")

    if isinstance(artifact, dict):

        record["artifact"] = artifact

        for key, dest in (

            ("transcript", "transcript"),

            ("messages", "messages"),

            ("recordingUrl", "recording_url"),

            ("recording", "recording"),

        ):

            if key in artifact:

                record[dest] = artifact[key]



    # Analysis block.

    analysis = message.get("analysis")

    if isinstance(analysis, dict):

        record["analysis"] = analysis



    # Streaming transcript fragments.

    if event_type == "transcript" and message.get("transcript"):

        record.setdefault("transcript_events", []).append(

            {

                "role": message.get("role"),

                "transcript_type": message.get("transcriptType"),

                "transcript": message["transcript"],

                "received_at": _now(),

            }

        )



    # End-of-call report.

    if event_type == "end-of-call-report":

        record["status"] = "ended"

        record["ended_reason"] = message.get("endedReason")

        record["completed_at"] = _now()

        logger.info("Call ended call_id=%s reason=%s", call_id, record["ended_reason"])



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
        # Preserve the full request for the end-of-call escalation decision.
        "incident_payload": incident.model_dump(mode="json"),
        "escalation_level": incident.model_dump().get("escalation_level", "technician"),

        "vapi_call": {**existing.get("vapi_call", {}), **data},

        "transcript": existing.get("transcript"),

        "analysis": existing.get("analysis"),

        "events": existing.get("events", []),

        "outcome": existing.get("outcome", default_outcome),

    }



    if incident.request_id:

        IDEMPOTENCY_KEYS[incident.request_id] = call_id


    # Handle the rare case where the final webhook arrived before the create-call
    # response was stored, so the first escalation check had no incident payload.
    if CALL_RESULTS[call_id].get("status") == "ended":
        try:
            await _maybe_escalate_to_senior(call_id)
        except Exception:
            logger.exception("Deferred senior escalation failed for call_id=%s", call_id)



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





@router.post("", summary="Create an outbound incident call")
async def create_outbound_incident_call(
    incident: IncidentCallRequest,
) -> dict[str, Any]:
    """Create a Vapi call. This route is for internal CORTEX requests, not webhooks."""
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


def _valid_webhook_secret(
    authorization: str | None,
    x_vapi_secret: str | None,
) -> bool:
    """Accept the configured Vapi Authorization credential and legacy secret header."""
    expected = (VAPI_WEBHOOK_SECRET or "").strip().strip('"').strip("'")
    if not expected:
        logger.error("VAPI_WEBHOOK_SECRET is not configured; rejecting webhook.")
        return False

    candidates = []
    if authorization:
        raw = authorization.strip()
        candidates.append(raw)
        if raw.lower().startswith("bearer "):
            candidates.append(raw[7:].strip())
    if x_vapi_secret:
        candidates.append(x_vapi_secret.strip())

    return any(hmac.compare_digest(candidate, expected) for candidate in candidates)


@router.post("/webhook", summary="Receive an authenticated Vapi webhook")
async def vapi_webhook(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_vapi_secret: str | None = Header(default=None, alias="x-vapi-secret"),
) -> dict[str, Any]:
    """Authenticate and process Vapi server messages and call-event webhooks."""
    if not _valid_webhook_secret(authorization, x_vapi_secret):
        logger.warning(
            "Vapi webhook rejected: missing or incorrect Authorization/x-vapi-secret."
        )
        raise HTTPException(status_code=401, detail="Invalid webhook secret.")

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Body must be valid JSON.") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object.")

    result = _handle_vapi_webhook(body)

    # Only evaluate escalation after Vapi sends its final end-of-call report.
    message = body.get("message", {})
    if isinstance(message, dict) and message.get("type") == "end-of-call-report":
        call_id = _get_call_id(message)
        if call_id:
            try:
                escalation = await _maybe_escalate_to_senior(str(call_id))
                if escalation:
                    result["senior_escalation"] = escalation
            except Exception:
                # Never make Vapi retry the webhook indefinitely because the
                # follow-up call failed; log the failure for operator visibility.
                logger.exception("Senior escalation failed for call_id=%s", call_id)
                record = CALL_RESULTS.get(str(call_id))
                if record is not None:
                    record["senior_escalation_error"] = "Senior call could not be created; inspect backend logs."

    return result


def _transcript_text(record: dict[str, Any]) -> str:
    """Get the final transcript from the result record or Vapi message artifacts."""
    transcript = record.get("transcript")
    if isinstance(transcript, str) and transcript.strip():
        return transcript
    messages = record.get("messages")
    if isinstance(messages, list):
        return "\n".join(
            f"{item.get('role', '')}: {item.get('message', item.get('content', ''))}"
            for item in messages
            if isinstance(item, dict)
        )
    artifact = record.get("artifact")
    if isinstance(artifact, dict):
        value = artifact.get("transcript")
        if isinstance(value, str):
            return value
    return ""


def _technician_response_text(record: dict[str, Any]) -> str:
    """Extract only the human/technician speech, excluding the assistant's own words."""
    chunks: list[str] = []

    def add_message(item: Any) -> None:
        if not isinstance(item, dict):
            return
        role = str(item.get("role", item.get("speaker", ""))).strip().lower()
        if role not in {"user", "human", "customer", "technician", "caller"}:
            return
        value = item.get("message", item.get("content", item.get("transcript", "")))
        if isinstance(value, str) and value.strip():
            chunks.append(value.strip())

    messages = record.get("messages")
    if isinstance(messages, list):
        for item in messages:
            add_message(item)

    # Vapi may send human speech as transcript events rather than artifact.messages.
    transcript_events = record.get("transcript_events")
    if isinstance(transcript_events, list):
        for item in transcript_events:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip().lower()
            if role in {"user", "human", "customer", "technician", "caller"}:
                value = item.get("transcript", item.get("text", ""))
                if isinstance(value, str) and value.strip():
                    chunks.append(value.strip())

    # Some providers return a role-labelled plain transcript instead of structured messages.
    if not chunks:
        transcript = record.get("transcript")
        if not isinstance(transcript, str) or not transcript.strip():
            artifact = record.get("artifact")
            transcript = artifact.get("transcript", "") if isinstance(artifact, dict) else ""
        if isinstance(transcript, str):
            for line in transcript.splitlines():
                match = re.match(r"\s*(?:user|human|customer|technician|caller)\s*:\s*(.+)", line, re.I)
                if match and match.group(1).strip():
                    chunks.append(match.group(1).strip())

    # Avoid duplicate lines that can occur in both artifact.messages and transcript_events.
    return " ".join(dict.fromkeys(chunks)).strip()


def _technician_declined(record: dict[str, Any]) -> tuple[bool, str]:
    """Classify the technician response; silence or anything short of clear acceptance escalates."""
    text = _technician_response_text(record).lower().strip()
    if not text:
        return True, "technician_silent_no_response_escalate_to_senior"

    decline_patterns = (
        r"(?:^|[.!?]\s*)\s*(?:uh[, ]*)?no(?:[.!?,\s]|$)",
        r"\bcan(?:not|'t)\b", r"\bunable to\b", r"\bwon't\b",
        r"\bnot able to\b", r"\bcan't take responsibility\b",
        r"\bneed(?:s)? (?:a )?senior\b", r"\bescalat(?:e|ion)\b",
        r"\bcan't handle\b", r"\bnot my responsibility\b",
    )
    if any(re.search(pattern, text) for pattern in decline_patterns):
        return True, "technician_declined_or_requested_escalation"

    # Only an explicit affirmative commitment prevents escalation. An ambiguous reply
    # is not treated as acceptance for a critical incident.
    acceptance_patterns = (
        r"\b(i|we)\s+(will|can|shall|am able to)\s+(take|handle|arrange|address|inspect|respond|do|own)\b",
        r"\b(i|we)\s+(accept|agree to)\s+(responsibility|take responsibility|handle this)\b",
        r"\byes[,! ]+(i'?ll|i will|i can)\b",
        r"\bi'?ll take responsibility\b",
        r"\bi can take responsibility\b",
        r"\bi will handle (it|this|the issue)\b",
        r"\bi will inspect\b",
        r"\bconfirmed[,! ]+(i'?ll|i will|i can)\b",
    )
    if any(re.search(pattern, text) for pattern in acceptance_patterns):
        return False, "technician_explicitly_accepted_responsibility"

    return True, "technician_response_unclear_or_no_explicit_commitment_escalate_to_senior"


async def _maybe_escalate_to_senior(call_id: str) -> dict[str, Any] | None:
    """Create one senior call if the technician declines, is silent, or fails to commit."""
    record = CALL_RESULTS.get(call_id)
    if not record or record.get("status") != "ended":
        return None
    if record.get("escalation_level") == "senior":
        return None
    if record.get("senior_escalation"):
        return record["senior_escalation"]
    if record.get("senior_escalation_pending"):
        return {"triggered": False, "reason": "senior_escalation_already_in_progress"}

    incident_data = record.get("incident_payload")
    if not isinstance(incident_data, dict):
        logger.warning("Cannot evaluate senior escalation: no incident payload for %s", call_id)
        return None

    escalation_required, reason = _technician_declined(record)
    response_text = _technician_response_text(record)
    outcome = record.get("outcome") or {}
    record["outcome"] = {
        **outcome,
        "acknowledgement": (
            "declined" if "declined" in reason else
            "no_response" if "silent" in reason else
            "unconfirmed" if escalation_required else "accepted"
        ),
        "escalation_required": escalation_required,
        "technician_response_received": bool(response_text),
        "technician_response": response_text or None,
    }
    record["escalation_decision"] = reason
    if not escalation_required:
        record["senior_escalation"] = {"triggered": False, "reason": reason}
        logger.info("Senior escalation not required for call_id=%s: %s", call_id, reason)
        return record["senior_escalation"]

    senior_number = (
        incident_data.get("escalation_phone_number")
        or os.getenv("CORTEX_SENIOR_PHONE_NUMBER", "").strip()
        or "+918999189384"
    )
    if not senior_number:
        record["senior_escalation"] = {
            "triggered": False,
            "reason": "technician_response_requires_escalation_but_senior_phone_not_configured",
        }
        logger.error("Senior escalation required but no senior phone configured; call_id=%s", call_id)
        return record["senior_escalation"]

    senior_payload = dict(incident_data)
    senior_payload["customer_number"] = senior_number
    senior_payload["recipient_name"] = incident_data.get("escalation_contact") or os.getenv(
        "CORTEX_SENIOR_NAME", "Senior Maintenance Engineer"
    )
    senior_payload["recipient_role"] = "Senior responsible maintenance contact"
    senior_payload["escalation_level"] = "senior"
    senior_payload["request_id"] = f"senior-escalation:{call_id}"
    extra = senior_payload.get("additional_instructions") or ""
    senior_payload["additional_instructions"] = (
        f"Senior escalation required because the technician did not confirm responsibility. "
        f"Reason: {reason}. Original call ID: {call_id}. "
        f"Technician response: {response_text or '[no response received]'}. " + extra
    ).strip()

    senior_incident = IncidentCallRequest.model_validate(senior_payload)
    # Mark pending before creating the call to prevent duplicate webhook deliveries.
    record["senior_escalation_pending"] = True
    try:
        created = await _create_call(senior_incident)
    except Exception:
        record.pop("senior_escalation_pending", None)
        logger.exception("Failed to create senior escalation call for original call_id=%s", call_id)
        raise
    record.pop("senior_escalation_pending", None)
    escalation_result = {
        "triggered": True,
        "reason": reason,
        "original_call_id": call_id,
        "senior_call_id": created.get("call_id"),
        "senior_phone_number": senior_number,
        "status": created.get("status"),
    }
    record["senior_escalation"] = escalation_result
    logger.info(
        "Senior escalation call created: original=%s senior_call=%s reason=%s",
        call_id, created.get("call_id"), reason,
    )
    return escalation_result


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

        "escalation_decision": record.get("escalation_decision"),

        "senior_escalation": record.get("senior_escalation"),

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