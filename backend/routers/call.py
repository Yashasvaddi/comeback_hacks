
"""Low-latency CORTEX voice WebSocket using Ollama and Edge TTS."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
from typing import Any

import httpx
from edge_tts import Communicate
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://host.docker.internal:11434/v1",
).rstrip("/")

OLLAMA_NATIVE_URL = (
    OLLAMA_BASE_URL[:-3]
    if OLLAMA_BASE_URL.endswith("/v1")
    else OLLAMA_BASE_URL
)

VOICE_MODEL = os.getenv("VOICE_ASSISTANT_MODEL", "gemma3:4b")
TTS_VOICE = os.getenv("VOICE_TTS_VOICE", "en-US-AriaNeural")

SYSTEM_PROMPT = os.getenv(
    "VOICE_ASSISTANT_SYSTEM_PROMPT",
    """
You are CORTEX, a real-time industrial operations copilot.

CONVERSATION:
- Speak naturally, like a sharp, calm, helpful colleague.
- Lead with the answer. Never begin with a greeting or filler.
- Use concise, spoken English. Usually start with one or two sentences.
- Explain the next useful action instead of giving generic advice.
- Ask one focused question when essential information is missing.
- Avoid markdown, headings, lists, and unnecessary repetition in spoken answers.
- Never narrate your reasoning or repeat the user's question.

INDUSTRIAL ACCURACY:
- Never invent sensor readings, equipment states, alarms, or events.
- Clearly distinguish supplied facts from assumptions.
- Never claim to have controlled equipment or executed an operation.
- For faults, suggest safe diagnostic checks in a practical order.
- Never suggest bypassing safety interlocks or protective systems.
- If live telemetry is unavailable, say so briefly.
- Keep responses concise unless the user requests detail.
""".strip(),
)

HTTP_TIMEOUT = httpx.Timeout(120.0, connect=5.0)


async def send(ws: WebSocket, data: dict[str, Any]) -> None:
    """Send a JSON event to the connected frontend."""
    await ws.send_text(json.dumps(data, ensure_ascii=False))


def take_ready_phrase(
    buffer: str,
    final: bool = False,
) -> tuple[str | None, str]:
    """Extract a speakable phrase without waiting for the full answer."""
    text = buffer.lstrip()

    if not text:
        return None, ""

    # Prefer complete sentence boundaries.
    match = re.search(r"""[.!?]["')\]]*\s+""", text)
    if match:
        phrase = text[:match.end()].strip()
        remainder = text[match.end():].lstrip()
        return phrase, remainder

    # Speak a complete clause if the sentence is getting long.
    if len(text) >= 100:
        match = re.search(r"""[,;:]["')\]]*\s+""", text)
        if match and match.start() >= 35:
            phrase = text[:match.end()].strip()
            remainder = text[match.end():].lstrip()
            return phrase, remainder

        # Fallback: split at a word boundary, not in the middle of a word.
        split_at = text.rfind(" ", 60, min(len(text), 90))
        if split_at > 0:
            return text[:split_at].strip(), text[split_at:].lstrip()

    if final:
        return text, ""

    return None, text


async def speak_phrase(
    ws: WebSocket,
    phrase: str,
    turn_id: int,
    seq: int,
) -> int:
    """Synthesize a short phrase and send it as an MP3 event."""
    phrase = phrase.strip()
    if not phrase:
        return seq

    audio = bytearray()

    async for chunk in Communicate(
        phrase,
        TTS_VOICE,
    ).stream():
        if chunk.get("type") == "audio":
            audio.extend(chunk["data"])

    if not audio:
        return seq

    await send(
        ws,
        {
            "type": "audio_chunk",
            "turn_id": turn_id,
            "seq": seq,
            "mime": "audio/mpeg",
            "text": phrase,
            "audio": base64.b64encode(audio).decode("ascii"),
        },
    )

    return seq + 1


async def generate_turn(
    ws: WebSocket,
    client: httpx.AsyncClient,
    prompt: str,
    turn_id: int,
) -> None:
    """Stream Ollama text and synthesize phrases as they become available."""
    seq = 0
    buffer = ""
    full_text = ""

    await send(
        ws,
        {"type": "status", "status": "thinking", "turn_id": turn_id},
    )

    try:
        async with client.stream(
            "POST",
            f"{OLLAMA_NATIVE_URL}/api/chat",
            json={
                "model": VOICE_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": True,
                "options": {
                    "temperature": 0.35,
                    "num_predict": 220,
                },
            },
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line:
                    continue

                packet = json.loads(line)
                piece = (packet.get("message") or {}).get("content", "")

                if piece:
                    full_text += piece
                    buffer += piece

                    await send(
                        ws,
                        {
                            "type": "assistant_text_delta",
                            "text": piece,
                            "turn_id": turn_id,
                        },
                    )

                    # Send each phrase as soon as it is ready.
                    while True:
                        phrase, buffer = take_ready_phrase(buffer)

                        if phrase is None:
                            break

                        await send(
                            ws,
                            {
                                "type": "status",
                                "status": "speaking",
                                "turn_id": turn_id,
                            },
                        )

                        seq = await speak_phrase(
                            ws, phrase, turn_id, seq
                        )

                if packet.get("done"):
                    break

        # Flush the final sentence, even without terminal punctuation.
        phrase, buffer = take_ready_phrase(buffer, final=True)

        if phrase:
            seq = await speak_phrase(ws, phrase, turn_id, seq)

        await send(
            ws,
            {
                "type": "turn_done",
                "turn_id": turn_id,
                "audio_chunks": seq,
                "text": full_text.strip(),
            },
        )

    except asyncio.CancelledError:
        # Allow cancellation to stop ongoing LLM/TTS work.
        raise

    except httpx.HTTPStatusError as exc:
        logger.exception("Ollama HTTP error")

        await send(
            ws,
            {
                "type": "error",
                "turn_id": turn_id,
                "message": (
                    f"LLM request failed "
                    f"(HTTP {exc.response.status_code})."
                ),
            },
        )

    except Exception:
        logger.exception("Voice generation failed")

        await send(
            ws,
            {
                "type": "error",
                "turn_id": turn_id,
                "message": "Voice response failed. Please try again.",
            },
        )


async def cancel_active_turn(
    ws: WebSocket,
    active: asyncio.Task | None,
    active_id: int | None,
) -> None:
    """Cancel an active generation and notify the frontend."""
    if active is None:
        return

    if not active.done():
        active.cancel()

    try:
        await active
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.debug("Cancelled task finished with an exception", exc_info=True)

    await send(
        ws,
        {"type": "cancelled", "turn_id": active_id},
    )


@router.websocket("/ws/voice")
async def voice_socket(ws: WebSocket) -> None:
    """Maintain one active response per WebSocket connection."""
    await ws.accept()

    active: asyncio.Task | None = None
    active_id: int | None = None
    next_turn_id = 0

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            await send(
                ws,
                {
                    "type": "ready",
                    "model": VOICE_MODEL,
                    "tts_voice": TTS_VOICE,
                },
            )

            while True:
                try:
                    message = json.loads(await ws.receive_text())
                except json.JSONDecodeError:
                    await send(
                        ws,
                        {"type": "error", "message": "Invalid JSON"},
                    )
                    continue

                kind = message.get("type")

                if kind == "cancel":
                    requested_id = message.get("turn_id")

                    if (
                        active is not None
                        and not active.done()
                        and (
                            requested_id is None
                            or requested_id == active_id
                        )
                    ):
                        cancelled_id = active_id
                        await cancel_active_turn(
                            ws, active, cancelled_id
                        )
                        active = None
                        active_id = None

                    continue

                if kind != "user_text":
                    await send(
                        ws,
                        {
                            "type": "error",
                            "message": "Expected user_text or cancel",
                        },
                    )
                    continue

                prompt = str(message.get("text", "")).strip()

                if not prompt:
                    await send(
                        ws,
                        {
                            "type": "ignored",
                            "reason": "empty_transcript",
                        },
                    )
                    continue

                # New user input supersedes the previous response.
                if active is not None:
                    if not active.done():
                        old_id = active_id
                        await cancel_active_turn(ws, active, old_id)

                    active = None
                    active_id = None

                supplied_id = message.get("turn_id")

                if supplied_id is not None:
                    try:
                        active_id = int(supplied_id)
                    except (TypeError, ValueError):
                        next_turn_id += 1
                        active_id = next_turn_id
                else:
                    next_turn_id += 1
                    active_id = next_turn_id

                active = asyncio.create_task(
                    generate_turn(
                        ws,
                        client,
                        prompt,
                        active_id,
                    )
                )

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")

    except asyncio.CancelledError:
        raise

    except Exception:
        logger.exception("Voice WebSocket failed")

    finally:
        if active is not None and not active.done():
            active.cancel()

            try:
                await active
            except (asyncio.CancelledError, Exception):
                pass
