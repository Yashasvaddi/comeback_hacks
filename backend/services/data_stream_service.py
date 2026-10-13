import asyncio

import csv
import os
import time

import httpx

from datetime import datetime, timezone

from pathlib import Path

from typing import Any

from fastapi import WebSocket

from services.incident_service import IncidentService

import logging

logger = logging.getLogger(__name__)

DATASET_DIR = (

    Path(__file__).resolve().parent.parent

    / "datasets"

    / "streaming"

)

AVAILABLE_DATASETS = {

    "dataset_1": DATASET_DIR / "dataset_1.csv",

    "dataset_2": DATASET_DIR / "dataset_2.csv",

    "dataset_3": DATASET_DIR / "dataset_3.csv",

}

# Keep these aligned with the thresholds used by your frontend.

# high: abnormal when value > threshold; low: abnormal when value < threshold.

SENSOR_RULES: dict[str, dict[str, Any]] = {

    "vib_de": {"title": "Drive-end vibration high", "threshold": 4.5, "direction": "high", "unit": "mm/s", "asset": "P-101", "category": "Mechanical"},

    "bearing_temp": {"title": "Bearing temperature high", "threshold": 85.0, "direction": "high", "unit": "°C", "asset": "P-101", "category": "Mechanical"},

    "motor_current": {"title": "Motor current high", "threshold": 75.0, "direction": "high", "unit": "A", "asset": "P-101", "category": "Electrical"},

    "motor_winding_temp": {"title": "Motor winding temperature high", "threshold": 85.0, "direction": "high", "unit": "°C", "asset": "P-101", "category": "Electrical"},

    "discharge_pressure": {"title": "Discharge pressure high", "threshold": 10.0, "direction": "high", "unit": "bar", "asset": "P-101", "category": "Instrumentation"},

    "flow": {"title": "Flow below threshold", "threshold": 140.0, "direction": "low", "unit": "m³/h", "asset": "P-101", "category": "Instrumentation"},

    "suction_pressure": {"title": "Suction pressure low", "threshold": 2.0, "direction": "low", "unit": "bar", "asset": "P-101", "category": "Instrumentation"},

    "vib_nde": {"title": "Non-drive-end vibration high", "threshold": 4.5, "direction": "high", "unit": "mm/s", "asset": "P-101", "category": "Mechanical"},

    "pump_speed": {"title": "Pump speed low", "threshold": 2800.0, "direction": "low", "unit": "rpm", "asset": "P-101", "category": "Mechanical"},

    "seal_pot_level": {"title": "Seal pot level low", "threshold": 30.0, "direction": "low", "unit": "%", "asset": "P-101", "category": "Instrumentation"},

    "lube_oil_temp": {"title": "Lube oil temperature high", "threshold": 65.0, "direction": "high", "unit": "°C", "asset": "P-101", "category": "Mechanical"},

    "seal_pressure": {"title": "Seal pressure low", "threshold": 2.5, "direction": "low", "unit": "bar", "asset": "P-101", "category": "Instrumentation"},

}

ERROR_AFTER_SECONDS = 20

TASK_AFTER_SECONDS = 60

MAX_EVENTS = 200

MAX_TASKS = 100

def _number(value: Any) -> float | None:

    try:

        if value is None or value == "":

            return None

        return float(value)

    except (TypeError, ValueError):

        return None

def _now() -> datetime:

    return datetime.now(timezone.utc)

def _timestamp(value: datetime | None = None) -> str:

    return (value or _now()).isoformat()

def _clock(value: datetime | None = None) -> str:

    return (value or _now()).astimezone().strftime("%H:%M:%S")

class DataStreamService:

    def __init__(self) -> None:

        self.active_dataset = "dataset_1"

        self.records: list[dict[str, Any]] = []

        self.position = 0

        self.clients: set[WebSocket] = set()

        self._lock = asyncio.Lock()

        self._stream_task: asyncio.Task | None = None

        self._loaded = False

        # Incident events are emitted once per threshold transition. External
        # delivery is dispatched asynchronously so telemetry processing does
        # not wait for WhatsApp or Vapi responses.
        self._incident_service = IncidentService()
        self._notification_tasks: set[asyncio.Task] = set()
        # Per-pump/per-severity cooldowns prevent notification floods.
        self._last_notification_at: dict[tuple[str, str], float] = {}
        self._pending_notifications: set[tuple[str, str]] = set()

        # Incident/task state is driven by actual records from the active CSV.

        self._active_issues: dict[str, dict[str, Any]] = {}

        self._events: list[dict[str, Any]] = []

        self._tasks: list[dict[str, Any]] = []

        self._event_counter = 1000

        self._work_order_counter = 4400

        self._logged_switches: list[dict[str, Any]] = []

    def _read_csv(self, dataset: str) -> list[dict[str, Any]]:

        path = AVAILABLE_DATASETS.get(dataset)

        if path is None:

            raise ValueError(

                f"Unknown dataset '{dataset}'. "

                f"Choose from: {list(AVAILABLE_DATASETS)}"

            )

        if not path.is_file():

            raise FileNotFoundError(f"Dataset file not found: {path}")

        with path.open("r", encoding="utf-8-sig", newline="") as file:

            reader = csv.DictReader(file)

            if not reader.fieldnames:

                raise ValueError(f"CSV has no header: {path}")

            records = list(reader)

        if not records:

            raise ValueError(f"Dataset is empty: {path}")

        return records

    async def _ensure_loaded(self) -> None:

        async with self._lock:

            if not self._loaded:

                self.records = self._read_csv(self.active_dataset)

                self._loaded = True

    async def connect(self, websocket: WebSocket) -> None:

        await websocket.accept()

        await self._ensure_loaded()

        async with self._lock:

            self.clients.add(websocket)

            await websocket.send_json({

                "event": "stream_started",

                "dataset": self.active_dataset,

                "total_records": len(self.records),

                "position": self.position,

            })

            # Send a current incident/task snapshot as a second message.

            await websocket.send_json(self._cortex_update_locked())

            if self._stream_task is None or self._stream_task.done():

                self._stream_task = asyncio.create_task(self._run_stream())

    async def disconnect(self, websocket: WebSocket) -> None:

        async with self._lock:

            self.clients.discard(websocket)

    async def switch_dataset(self, dataset: str) -> dict[str, Any]:

        new_records = self._read_csv(dataset)

        async with self._lock:

            previous_dataset = self.active_dataset

            self.active_dataset = dataset

            self.records = new_records

            self.position = 0

            self._loaded = True

            event = {

                "event": "dataset_switched",

                "dataset": dataset,

                "previous_dataset": previous_dataset,

                "total_records": len(new_records),

                "position": 0,

            }

            self._add_event_locked(

                title="Dataset switched",

                message=f"Operator switched active telemetry from {previous_dataset} to {dataset}.",

                source="Operator",

                event_type="activity",

                severity="info",

                status="completed",

                details=f"{previous_dataset} → {dataset}",

                acknowledged=True,

            )

            await self._broadcast(event)

            await self._broadcast(self._cortex_update_locked())

            if self.clients and (

                self._stream_task is None or self._stream_task.done()

            ):

                self._stream_task = asyncio.create_task(self._run_stream())

            return event

    async def get_status(self) -> dict[str, Any]:

        await self._ensure_loaded()

        async with self._lock:

            return {

                "active_dataset": self.active_dataset,

                "position": self.position,

                "total_records": len(self.records),

                "remaining_records": max(0, len(self.records) - self.position),

                "connected_clients": len(self.clients),

                "streaming": self._stream_task is not None and not self._stream_task.done(),

                "active_issues": len(self._active_issues),

                "open_tasks": sum(t["status"] == "open" for t in self._tasks),

            }

    def _add_event_locked(

        self,

        *,

        title: str,

        message: str,

        source: str,

        event_type: str,

        severity: str,

        status: str,

        details: str = "",

        duration_seconds: int = 0,

        acknowledged: bool = False,

        issue_key: str | None = None,

    ) -> dict[str, Any]:

        # Reuse the existing event/title for the same active issue.

        if issue_key:

            for old in self._events:

                if old.get("issue_key") == issue_key and old.get("type") == event_type:

                    old.update({

                        "time": _clock(),

                        "timestamp": _timestamp(),

                        "message": message,

                        "details": details,

                        "status": status,

                        "duration_seconds": duration_seconds,

                    })

                    return old

        self._event_counter += 1

        event = {

            "event_id": f"EVT-{self._event_counter}",

            "time": _clock(),

            "timestamp": _timestamp(),

            "type": event_type,

            "severity": severity,

            "source": source,

            "title": title,

            "message": message,

            "details": details,

            "status": status,

            "duration_seconds": duration_seconds,

            "acknowledged": acknowledged,

        }

        if issue_key:

            event["issue_key"] = issue_key

        self._events.insert(0, event)

        del self._events[MAX_EVENTS:]

        return event

    def _cortex_update_locked(self) -> dict[str, Any]:

        local_today = _now().astimezone().date().isoformat()

        open_count = sum(t["status"] == "open" for t in self._tasks)

        progress_count = sum(t["status"] == "in_progress" for t in self._tasks)

        closed_today = sum(

            t["status"] == "closed" and str(t.get("closed_at", "")).startswith(local_today)

            for t in self._tasks

        )

        return {

            "event": "cortex_update",

            "timestamp": _timestamp(),

            "left_val": {

                "stream": "activity_error_log",

                "latest_event": self._events[0] if self._events else None,

                "events": list(self._events),

                "total_events": len(self._events),

            },

            "right_val": {

                "stream": "maintenance_tasks",

                "latest_task": self._tasks[0]["work_order_id"] if self._tasks else None,

                "tasks": list(self._tasks),

                "summary": {

                    "open": open_count,

                    "in_progress": progress_count,

                    "closed_today": closed_today,

                },

                "total_tasks": len(self._tasks),

            },

        }

    async def _broadcast(self, message: dict[str, Any]) -> None:

        disconnected = []

        for client in list(self.clients):

            try:

                await client.send_json(message)

            except Exception:

                disconnected.append(client)

        for client in disconnected:

            self.clients.discard(client)

    def _queue_incident_notification_locked(
        self,
        incident_event: dict[str, Any],
        *,
        delay_seconds: float,
        cooldown_seconds: float,
    ) -> None:
        """Queue a notification only when its per-pump cooldown has elapsed."""
        pump_id = str(incident_event.get("pump_id", "P-101"))
        severity = str(incident_event.get("severity", ""))
        key = (pump_id, severity)
        now = time.monotonic()

        if key in self._pending_notifications:
            return

        last_queued = self._last_notification_at.get(key)
        if last_queued is not None and now - last_queued < cooldown_seconds:
            return

        # Start cooldown at queue time so slow API requests cannot pile up.
        self._last_notification_at[key] = now
        self._pending_notifications.add(key)
        task = asyncio.create_task(
            self._dispatch_after_delay(incident_event, delay_seconds, key),
            name=f"cortex-notify-{pump_id}-{severity}",
        )
        self._notification_tasks.add(task)
        task.add_done_callback(self._notification_tasks.discard)

    async def _dispatch_after_delay(
        self,
        incident_event: dict[str, Any],
        delay_seconds: float,
        key: tuple[str, str],
    ) -> None:
        """Delay YELLOW and skip it if the pump becomes RED during the delay."""
        try:
            if delay_seconds:
                await asyncio.sleep(delay_seconds)

            current_state = self._incident_service.get_state(key[0])
            if current_state["severity"] != key[1]:
                logger.info(
                    "Skipping stale %s notification for %s; current severity is %s.",
                    key[1],
                    key[0],
                    current_state["severity"],
                )
                return

            await self._dispatch_incident_action(incident_event)
        finally:
            self._pending_notifications.discard(key)

    async def _dispatch_incident_action(self, incident_event: dict[str, Any]) -> None:
        """Deliver one incident notification through the existing API routers."""
        base_url = os.getenv("CORTEX_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        severity = incident_event.get("severity")
        pump_id = str(incident_event.get("pump_id", "P-101"))
        sensors = ", ".join(incident_event.get("abnormal_fields", [])) or "unknown sensors"
        detected_at = str(incident_event.get("timestamp", _timestamp()))
        request_id = f"cortex-{pump_id}-{severity}-{detected_at}"

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                if severity == "YELLOW":
                    recipient = os.getenv("CORTEX_WHATSAPP_RECIPIENT", "").strip()
                    if not recipient:
                        logger.error(
                            "YELLOW incident detected, but CORTEX_WHATSAPP_RECIPIENT is not configured; "
                            "WhatsApp alert was not sent."
                        )
                        return

                    body = (
                        f"CORTEX PUMP WARNING\n"
                        f"Pump: {pump_id}\n"
                        f"{incident_event.get('consecutive_abnormal', 14)} consecutive abnormal sensor readings detected.\n"
                        f"Abnormal sensors: {sensors}\n"
                        f"Detected at: {detected_at}\n"
                        "Please inspect the pump and acknowledge this alert."
                    )
                    response = await client.post(
                        f"{base_url}/api/whatsapp/send",
                        json={"to": recipient, "body": body},
                    )
                    response.raise_for_status()
                    logger.info(
                        "CORTEX WhatsApp alert accepted for pump %s (HTTP %s).",
                        pump_id,
                        response.status_code,
                    )

                elif severity == "RED":
                    recipient = os.getenv("CORTEX_TECHNICIAN_PHONE_NUMBER", "").strip()
                    if not recipient:
                        logger.error(
                            "RED incident detected, but CORTEX_TECHNICIAN_PHONE_NUMBER is not configured; "
                            "Vapi call was not initiated."
                        )
                        return

                    payload = {
                        "customer_number": recipient,
                        "recipient_name": os.getenv("CORTEX_TECHNICIAN_NAME", "Technician"),
                        "recipient_role": "Responsible maintenance technician",
                        "incident_id": request_id,
                        "incident_title": f"Critical pump incident on {pump_id}",
                        "detected_at": detected_at,
                        "asset": pump_id,
                        "affected_system": "Industrial pump monitoring",
                        "issue": f"More than 15 consecutive abnormal readings. Abnormal sensors: {sensors}.",
                        "severity": "Critical",
                        "incident_status": "Open",
                        "recommended_action": (
                            f"Urgently inspect {pump_id} and investigate abnormal readings from: {sensors}."
                        ),
                        "supporting_evidence": f"Consecutive abnormal readings: {incident_event.get('consecutive_abnormal')}; sensors: {sensors}.",
                        "call_objective": "Notify the technician of the critical pump incident and obtain acknowledgement.",
                        "required_acknowledgement": "Confirm receipt of the critical alert and whether you can take responsibility for the response.",
                        "request_id": request_id,
                    }
                    response = await client.post(
                        f"{base_url}/api/incident-calls",
                        json=payload,
                    )
                    response.raise_for_status()
                    result = response.json()
                    logger.info(
                        "CORTEX Vapi call request accepted for pump %s; call_id=%s.",
                        pump_id,
                        result.get("call_id"),
                    )

        except httpx.HTTPStatusError as exc:
            logger.error(
                "CORTEX %s delivery failed (HTTP %s): %s",
                severity,
                exc.response.status_code,
                exc.response.text[:1000],
            )
        except httpx.HTTPError:
            logger.exception("CORTEX %s delivery failed due to an HTTP/network error.", severity)
        except Exception:
            logger.exception("Unexpected error while dispatching CORTEX %s incident.", severity)

    def _process_record_locked(self, dataset: str, record: dict[str, Any]) -> bool:

        """Classify one actual CSV row and update active issues, events, and tasks."""

        now = _now()

        # Pump-level incident detection: a reading is abnormal when any
        # configured sensor violates its existing threshold.
        abnormal_fields: list[str] = []
        for sensor_name, sensor_rule in SENSOR_RULES.items():
            sensor_value = _number(record.get(sensor_name))
            if sensor_value is None:
                continue

            sensor_threshold = float(sensor_rule["threshold"])
            sensor_abnormal = (
                sensor_value > sensor_threshold
                if sensor_rule["direction"] == "high"
                else sensor_value < sensor_threshold
            )
            if sensor_abnormal:
                abnormal_fields.append(sensor_name)

        incident_event = self._incident_service.process_record(
            pump_id="P-101",
            record=record,
            abnormal_fields=abnormal_fields,
        )

        changed = False
        if incident_event:
            is_critical = incident_event["severity"] == "RED"
            intended_action = incident_event["intended_action"]
            sensor_list = ", ".join(incident_event["abnormal_fields"])
            self._add_event_locked(
                title="Critical pump incident" if is_critical else "Pump warning",
                message=(
                    "More than 15 consecutive abnormal readings detected; technician call escalation."
                    if is_critical
                    else "More than 13 consecutive abnormal readings detected; WhatsApp alert escalation."
                ),
                source="CORTEX Incident Engine",
                event_type="activity",
                severity="critical" if is_critical else "warning",
                status="notification_queued",
                details=(
                    f"Pump: {incident_event['pump_id']}; "
                    f"consecutive readings: {incident_event['consecutive_abnormal']}; "
                    f"abnormal sensors: {sensor_list}; "
                    f"intended action: {intended_action}."
                ),
                issue_key=f"incident:{dataset}:{incident_event['severity']}:{incident_event['timestamp']}",
            )
            changed = True

        # Check cadence on every row so a continuing incident can notify again
        # after its cooldown. YELLOW: wait 3s, then 60s between sends.
        # RED: call immediately, then 300s between call attempts.
        current_state = self._incident_service.get_state("P-101")
        consecutive = current_state["consecutive_abnormal"]
        severity = current_state["severity"]
        current_event = {
            "pump_id": "P-101",
            "severity": severity,
            "consecutive_abnormal": consecutive,
            "abnormal_fields": abnormal_fields,
            "timestamp": _timestamp(now),
            "record_timestamp": record.get("timestamp"),
            "intended_action": (
                "WHATSAPP_MESSAGE" if severity == "YELLOW"
                else "TECHNICIAN_CALL" if severity == "RED"
                else None
            ),
        }

        if severity == "YELLOW" and consecutive > 13:
            self._queue_incident_notification_locked(
                current_event,
                delay_seconds=3,
                cooldown_seconds=60,
            )
        elif severity == "RED" and consecutive > 15:
            self._queue_incident_notification_locked(
                current_event,
                delay_seconds=0,
                cooldown_seconds=300,
            )

        for sensor, rule in SENSOR_RULES.items():

            value = _number(record.get(sensor))

            if value is None:

                continue

            threshold = float(rule["threshold"])

            abnormal = value > threshold if rule["direction"] == "high" else value < threshold

            issue_key = f"{dataset}:{sensor}"

            if not abnormal:

                issue = self._active_issues.pop(issue_key, None)

                if issue:

                    elapsed = int((now - issue["started_at"]).total_seconds())

                    if issue["error_published"] or issue["task_created"]:

                        self._add_event_locked(

                            title=f"{rule['title']} resolved",

                            message="Reading returned within the configured threshold.",

                            source=rule["asset"],

                            event_type="activity",

                            severity="info",

                            status="resolved",

                            details=f"{sensor}: {value:g} {rule['unit']}; threshold: {threshold:g} {rule['unit']}",

                            duration_seconds=elapsed,

                            acknowledged=True,

                        )

                    changed = True

                continue

            issue = self._active_issues.get(issue_key)

            if issue is None:

                issue = {

                    "started_at": now,

                    "error_published": False,

                    "task_created": False,

                    "event_id": None,

                    "work_order_id": None,

                }

                self._active_issues[issue_key] = issue

                event = self._add_event_locked(

                    title=rule["title"],

                    message="Sensor reading crossed its configured threshold; monitoring persistence.",

                    source=rule["asset"],

                    event_type="activity",

                    severity="info",

                    status="monitoring",

                    details=f"{sensor}: {value:g} {rule['unit']}; threshold: {threshold:g} {rule['unit']}",

                    issue_key=issue_key,

                )

                issue["event_id"] = event["event_id"]

                changed = True

            elapsed = max(0, int((now - issue["started_at"]).total_seconds()))

            details = f"{sensor}: {value:g} {rule['unit']}; threshold: {threshold:g} {rule['unit']}"

            if elapsed >= ERROR_AFTER_SECONDS and not issue["error_published"]:

                event = self._add_event_locked(

                    title=rule["title"],

                    message=f"Error occurred: threshold violation persisted for {elapsed} seconds.",

                    source=rule["asset"],

                    event_type="error",

                    severity="warning",

                    status="error_occurred",

                    details=details,

                    duration_seconds=elapsed,

                    issue_key=issue_key,

                )

                issue["event_id"] = event["event_id"]

                issue["error_published"] = True

                changed = True

            if elapsed >= TASK_AFTER_SECONDS and not issue["task_created"]:

                self._work_order_counter += 1

                work_order_id = f"WO-{self._work_order_counter}"

                self._tasks.insert(0, {

                    "work_order_id": work_order_id,

                    "event_id": issue.get("event_id"),

                    "created_at": _clock(now),

                    "timestamp": _timestamp(now),

                    "title": f"Inspect {rule['asset']} — {rule['title']}",

                    "description": f"Investigate sustained {rule['title'].lower()}.",

                    "asset": rule["asset"],

                    "sensor": sensor,

                    "dataset": dataset,

                    "category": rule["category"],

                    "priority": "High",

                    "status": "open",

                    "trigger": "unresolved_error_60s",

                    "elapsed_seconds": elapsed,

                    "current_value": value,

                    "threshold": threshold,

                    "recommended_action": f"Inspect the asset and verify {rule['title'].lower()} readings.",

                })

                del self._tasks[MAX_TASKS:]

                issue["task_created"] = True

                issue["work_order_id"] = work_order_id

                self._add_event_locked(

                    title=f"Maintenance task {work_order_id} created",

                    message=f"{rule['asset']} issue escalated after {elapsed} seconds.",

                    source="System",

                    event_type="activity",

                    severity="critical",

                    status="task_created",

                    details=f"{rule['title']}; linked issue {issue.get('event_id')}",

                    duration_seconds=elapsed,

                    issue_key=f"{issue_key}:task",

                )

                changed = True

        return changed

    async def _run_stream(self) -> None:

        try:

            while self.clients:

                await asyncio.sleep(1)

                async with self._lock:

                    if not self.clients:

                        break

                    # Replay the active dataset from the beginning

                    # instead of stopping at the final row.

                    if self.position >= len(self.records):

                        self.position = 0

                    record = self.records[self.position]

                    row_number = self.position + 1

                    dataset = self.active_dataset

                    self.position += 1

                    # Preserve the existing telemetry event contract.

                    await self._broadcast({

                        "event": "data",

                        "dataset": dataset,

                        "row": row_number,

                        "total_records": len(self.records),

                        "data": record,

                    })

                    # Process the same row for incidents and tasks.

                    changed = self._process_record_locked(

                        dataset, record

                    )

                    if changed:

                        await self._broadcast(

                            self._cortex_update_locked()

                        )

        finally:

            async with self._lock:

                self._stream_task = None

data_stream_service = DataStreamService()
