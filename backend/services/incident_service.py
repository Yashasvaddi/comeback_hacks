import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PumpIncidentState:
    consecutive_abnormal: int = 0
    severity: str = "GREEN"
    warning_emitted: bool = False
    critical_emitted: bool = False


class IncidentService:
    """
    Tracks consecutive sensor-threshold violations for each pump.

    This service emits backend events only:
    - YELLOW after more than 13 consecutive abnormal readings: intended WhatsApp alert.
    - RED after more than 15 consecutive abnormal readings: intended technician call.

    It does not send WhatsApp messages or place calls. Those integrations
    must remain separate and are not invoked by this service.
    """

    WARNING_THRESHOLD = 14
    CRITICAL_THRESHOLD = 16

    def __init__(self) -> None:
        self._states: dict[str, PumpIncidentState] = {}
        self._lock = Lock()

    def process_record(
        self,
        pump_id: str,
        record: dict[str, Any],
        abnormal_fields: list[str],
    ) -> dict[str, Any] | None:
        """
        Process one sensor reading.

        `abnormal_fields` lists the sensors that violated their configured
        thresholds in this reading.

        Emits one event when WARNING or CRITICAL is first reached. It does
        not emit repeated events on subsequent abnormal readings. A normal
        reading resets the incident state, allowing future incidents to
        trigger events again.
        """
        with self._lock:
            state = self._states.setdefault(pump_id, PumpIncidentState())

            if not abnormal_fields:
                state.consecutive_abnormal = 0
                state.severity = "GREEN"
                state.warning_emitted = False
                state.critical_emitted = False
                return None

            state.consecutive_abnormal += 1
            event: dict[str, Any] | None = None

            if (
                state.consecutive_abnormal >= self.CRITICAL_THRESHOLD
                and not state.critical_emitted
            ):
                state.severity = "RED"
                state.critical_emitted = True
                event = {
                    "event_type": "CRITICAL_TRIGGERED",
                    "intended_action": "TECHNICIAN_CALL",
                    "pump_id": pump_id,
                    "severity": state.severity,
                    "consecutive_abnormal": state.consecutive_abnormal,
                    "abnormal_fields": list(abnormal_fields),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "record_timestamp": record.get("timestamp"),
                }

            elif (
                state.consecutive_abnormal >= self.WARNING_THRESHOLD
                and not state.warning_emitted
            ):
                state.severity = "YELLOW"
                state.warning_emitted = True
                event = {
                    "event_type": "WARNING_TRIGGERED",
                    "intended_action": "WHATSAPP_MESSAGE",
                    "pump_id": pump_id,
                    "severity": state.severity,
                    "consecutive_abnormal": state.consecutive_abnormal,
                    "abnormal_fields": list(abnormal_fields),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "record_timestamp": record.get("timestamp"),
                }

            if event:
                logger.warning("CORTEX INCIDENT: %s", event)

            return event

    def get_state(self, pump_id: str) -> dict[str, Any]:
        """Return the current backend incident state for a pump."""
        with self._lock:
            state = self._states.get(pump_id, PumpIncidentState())
            return {
                "pump_id": pump_id,
                "severity": state.severity,
                "consecutive_abnormal": state.consecutive_abnormal,
                "warning_emitted": state.warning_emitted,
                "critical_emitted": state.critical_emitted,
            }

    def reset_pump(self, pump_id: str) -> None:
        """Reset incident state for a pump, e.g. during testing or maintenance."""
        with self._lock:
            self._states.pop(pump_id, None)
