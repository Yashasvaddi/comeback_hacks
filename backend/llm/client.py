"""LLM client for Ollama Cloud (free, hosted, OpenAI-compatible).

We deliberately use the OpenAI SDK pointed at Ollama Cloud's
OpenAI-compatible endpoint (https://ollama.com/v1) rather than the
Anthropic SDK — the project runs entirely on free hosted open models.

Two tiers keep us under the free-tier request caps:
  * FAST  (gpt-oss:20b)  — bulk ops: entity extraction, classification, summaries
  * SMART (gpt-oss:120b) — reasoning: copilot, RCA, compliance, lessons

Swap `OLLAMA_BASE_URL` / `OLLAMA_API_KEY` in the environment to fail over
to a local Ollama (`http://localhost:11434/v1`) or any other
OpenAI-compatible provider without touching this code.
"""
from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from config import settings


class Tier(str, Enum):
    """Which model tier to route a call to."""

    FAST = "fast"   # gpt-oss:20b
    SMART = "smart"  # gpt-oss:120b


_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Lazily build the shared async client."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.ollama_api_key or "ollama",  # cloud needs a key; local accepts any
            base_url=settings.ollama_base_url,
        )
    return _client


def _model_for(tier: Tier) -> str:
    return settings.llm_model_smart if tier == Tier.SMART else settings.llm_model_fast


async def complete(
    *,
    messages: list[dict],
    tier: Tier = Tier.FAST,
    temperature: float = 0.2,
    max_tokens: int | None = None,
    response_format: dict | None = None,
) -> str:
    """Single-shot completion. Returns the assistant text content.

    Pass `response_format={"type": "json_object"}` to coerce JSON output
    (used by the entity-extraction and structured-RCA prompts).
    """
    client = get_client()
    kwargs: dict = {
        "model": _model_for(tier),
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if response_format is not None:
        kwargs["response_format"] = response_format

    resp = await client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


async def stream(
    *,
    messages: list[dict],
    tier: Tier = Tier.SMART,
    temperature: float = 0.3,
    max_tokens: int | None = None,
) -> AsyncIterator[str]:
    """Streaming completion. Yields text deltas as they arrive.

    Used by the copilot chat SSE endpoint so the UI renders tokens live.
    """
    client = get_client()
    kwargs: dict = {
        "model": _model_for(tier),
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    async for chunk in await client.chat.completions.create(**kwargs):
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json(text: str) -> Any:
    """Parse JSON from a model response, tolerating markdown code fences.

    gpt-oss often wraps JSON-mode output in ```json ... ``` fences even with
    response_format set, so we strip them before parsing. Falls back to the
    first {...} or [...] span if the whole string isn't valid JSON.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    m = _FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Last resort: grab the outermost JSON object/array span.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not extract JSON from model response: {text[:200]!r}")


async def complete_json(
    *,
    messages: list[dict],
    tier: Tier = Tier.FAST,
    temperature: float = 0.1,
    max_tokens: int | None = None,
) -> Any:
    """Completion that returns parsed JSON (fence-tolerant)."""
    raw = await complete(
        messages=messages,
        tier=tier,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    return extract_json(raw)
