"""Interruptible CORTEX voice WebSocket. Ollama LLM + streamed sentence MP3 TTS."""
from __future__ import annotations
import asyncio, base64, json, os, re
from typing import Any
import httpx
from edge_tts import Communicate
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1").rstrip("/")
OLLAMA_NATIVE_URL = OLLAMA_BASE_URL[:-3] if OLLAMA_BASE_URL.endswith("/v1") else OLLAMA_BASE_URL
VOICE_MODEL = os.getenv("VOICE_ASSISTANT_MODEL", "gemma3:4b")
TTS_VOICE = os.getenv("VOICE_TTS_VOICE", "en-US-AriaNeural")
SYSTEM_PROMPT = os.getenv("VOICE_ASSISTANT_SYSTEM_PROMPT",
    "You are CORTEX, a concise industrial operations assistant. Explain equipment status clearly. "
    "Do not claim to control physical equipment or invent sensor readings.")

async def send(ws: WebSocket, data: dict[str, Any]) -> None:
    await ws.send_text(json.dumps(data, ensure_ascii=False))

def split_sentences(text: str) -> tuple[list[str], str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return (parts[:-1], parts[-1]) if len(parts) > 1 else ([], text)

async def speak_sentence(ws: WebSocket, sentence: str, turn_id: int, seq: int) -> int:
    audio = bytearray()
    async for chunk in Communicate(sentence, TTS_VOICE).stream():
        if chunk.get("type") == "audio":
            audio.extend(chunk["data"])
    if audio:
        await send(ws, {"type":"audio_chunk","turn_id":turn_id,"seq":seq,
                        "mime":"audio/mpeg","audio":base64.b64encode(audio).decode("ascii")})
        return seq + 1
    return seq

async def generate_turn(ws: WebSocket, prompt: str, turn_id: int) -> None:
    await send(ws, {"type":"status","status":"thinking","turn_id":turn_id})
    seq, buffer = 0, ""
    async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=10)) as client:
        async with client.stream("POST", f"{OLLAMA_NATIVE_URL}/api/chat",
            json={"model":VOICE_MODEL,"messages":[{"role":"system","content":SYSTEM_PROMPT},
                  {"role":"user","content":prompt}],"stream":True}) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line: continue
                packet = json.loads(line)
                piece = (packet.get("message") or {}).get("content", "")
                if piece:
                    buffer += piece
                    await send(ws, {"type":"assistant_text_delta","text":piece,"turn_id":turn_id})
                    ready, buffer = split_sentences(buffer)
                    for sentence in ready:
                        await send(ws, {"type":"status","status":"speaking","turn_id":turn_id})
                        seq = await speak_sentence(ws, sentence, turn_id, seq)
                if packet.get("done"): break
    if buffer.strip():
        seq = await speak_sentence(ws, buffer.strip(), turn_id, seq)
    await send(ws, {"type":"turn_done","turn_id":turn_id,"audio_chunks":seq})

@router.websocket("/ws/voice")
async def voice_socket(ws: WebSocket) -> None:
    await ws.accept()
    active: asyncio.Task | None = None
    active_id: int | None = None
    try:
        await send(ws, {"type":"ready","model":VOICE_MODEL,"tts_voice":TTS_VOICE})
        while True:
            try: message = json.loads(await ws.receive_text())
            except json.JSONDecodeError:
                await send(ws, {"type":"error","message":"Invalid JSON"}); continue
            kind = message.get("type")
            if kind == "cancel":
                requested = message.get("turn_id")
                if active and not active.done() and (requested is None or requested == active_id):
                    active.cancel()
                    try: await active
                    except (asyncio.CancelledError, Exception): pass
                    active = None
                    await send(ws, {"type":"cancelled","turn_id":active_id})
                continue
            if kind != "user_text":
                await send(ws, {"type":"error","message":"Expected user_text or cancel"}); continue
            prompt = str(message.get("text", "")).strip()
            if not prompt:
                await send(ws, {"type":"ignored","reason":"empty_transcript"}); continue
            if active and not active.done():
                active.cancel()
                try: await active
                except (asyncio.CancelledError, Exception): pass
            active_id = int(message.get("turn_id") or ((active_id or 0) + 1))
            active = asyncio.create_task(generate_turn(ws, prompt, active_id))
    except WebSocketDisconnect:
        pass
    finally:
        if active and not active.done():
            active.cancel()
            try: await active
            except (asyncio.CancelledError, Exception): pass
