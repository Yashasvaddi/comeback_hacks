import os
import json
import httpx
from dotenv import load_dotenv

VAPI_API_URL = "https://api.vapi.ai/call"

load_dotenv()

# Set these environment variables before running.
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID")

# The person Cortex will call.
TEST_PHONE_NUMBER = "+919702120202"

incident = {
    # Incident identification
    "incident_id": "INC-2026-1042",
    "incident_title": "Cooling Water Pump Abnormal Vibration",
    "detected_at": "2026-10-13T10:00:00+05:30",
    "incident_status": "Open",

    # Recipient
    "recipient_name": "Rajesh",
    "recipient_role": "Maintenance Manager",

    # Location and equipment
    "facility_name": "Mumbai Manufacturing Plant",
    "asset": "Cooling Water Pump P-204",
    "affected_system": "Cooling Water Circulation System",

    # Incident details
    "issue": (
        "Pump P-204 is experiencing vibration levels above "
        "the normal operating threshold."
    ),
    "severity": "High",

    # Root cause analysis
    "rca_summary": (
        "The vibration anomaly may be associated with a "
        "bearing lubrication problem. Physical inspection "
        "is required to confirm the cause."
    ),
    "root_cause": (
        "Suspected bearing lubrication failure; "
        "not yet physically verified."
    ),
    "supporting_evidence": (
        "Simulated vibration readings exceed the configured "
        "operating threshold."
    ),
    "telemetry": (
        "Test data only: vibration 8.2 mm/s; configured "
        "alert threshold 7.1 mm/s."
    ),

    # Business and operational impact
    "impact": (
        "Continued operation may increase the risk of "
        "bearing damage and cooling system disruption."
    ),

    # Required corrective action
    "recommended_action": (
        "Arrange an immediate pump inspection and verify "
        "bearing lubrication. Follow plant safety and "
        "shutdown procedures if required."
    ),
    "response_deadline": "Within 30 minutes",

    # Acknowledgement and escalation
    "call_objective": (
        "Communicate the incident, explain the suspected cause, "
        "and obtain a clear commitment to corrective action."
    ),
    "required_acknowledgement": (
        "Confirm whether you will take responsibility for "
        "arranging the inspection within 30 minutes."
    ),
    "escalation_criteria": (
        "Escalate if the recipient declines, cannot commit "
        "to the deadline, or does not provide a clear response."
    ),
    "escalation_contact": "Maintenance Supervisor",

    # Voice-agent behavior
    "additional_instructions": (
        "This is a simulated incident for testing. "
        "State that the root cause is suspected, not confirmed. "
        "Deliver the alert immediately, ask one direct question, "
        "and keep the initial message under 60 words. "
        "Do not claim that corrective action has started "
        "or that the issue is resolved without verification."
    ),
}

def main():
    if not all([
        VAPI_API_KEY,
        VAPI_ASSISTANT_ID,
        VAPI_PHONE_NUMBER_ID,
    ]):
        raise SystemExit(
            "Set VAPI_API_KEY, VAPI_ASSISTANT_ID, and "
            "VAPI_PHONE_NUMBER_ID before running."
        )

    # Explicit confirmation helps prevent accidental real calls.
    confirmation = input(
        f"This will initiate a real call to {TEST_PHONE_NUMBER}. "
        "Type CALL to continue: "
    )
    if confirmation != "CALL":
        print("Cancelled.")
        return

    payload = {
        "assistantId": VAPI_ASSISTANT_ID,
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": TEST_PHONE_NUMBER,
            "name": incident["recipient_name"],
        },
        "assistantOverrides": {
            "variableValues": incident,
        },
    }

    print("Sending call request directly to Vapi...")

    try:
        response = httpx.post(
            VAPI_API_URL,
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45.0,
        )

        print(f"HTTP status: {response.status_code}")

        try:
            result = response.json()
        except ValueError:
            print(response.text)
            return

        if response.is_success:
            print("Vapi accepted the call request.")
            print("Call ID:", result.get("id", "Not returned"))
            print("Call status:", result.get("status", "Unknown"))
            print(json.dumps(result, indent=2))
        else:
            print("Vapi returned an error:")
            print(json.dumps(result, indent=2))

    except httpx.TimeoutException:
        print(
            "Request timed out. Check Vapi call logs before retrying; "
            "the call may already have been created."
        )
    except httpx.HTTPError as exc:
        print(f"Request failed: {exc}")


if __name__ == "__main__":
    main()