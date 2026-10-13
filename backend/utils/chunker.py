"""Sliding-window text chunker.

Splits document text into overlapping chunks sized for embedding. We chunk
on a token estimate (via tiktoken when available, else a char heuristic) and
prefer to break on paragraph / sentence boundaries so chunks stay coherent.

Defaults: 512-token windows with 50-token overlap (per ARCHITECTURE.md).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover - tiktoken optional at runtime
    _ENC = None


def _count_tokens(text: str) -> int:
    if _ENC is not None:
        return len(_ENC.encode(text))
    # Rough heuristic: ~4 chars per token.
    return max(1, len(text) // 4)


@dataclass
class Chunk:
    index: int
    text: str
    token_count: int


# Split on paragraph breaks first, then sentence enders, keeping the delimiter.
_PARA_RE = re.compile(r"\n\s*\n")
_SENT_RE = re.compile(r"(?<=[.!?])\s+")


def _hard_split(text: str, max_tokens: int) -> list[str]:
    """Split a too-long unit into <= max_tokens pieces on word boundaries."""
    words = text.split()
    pieces: list[str] = []
    cur: list[str] = []
    cur_tokens = 0
    for w in words:
        t = _count_tokens(w + " ")
        if cur_tokens + t > max_tokens and cur:
            pieces.append(" ".join(cur))
            cur, cur_tokens = [], 0
        cur.append(w)
        cur_tokens += t
    if cur:
        pieces.append(" ".join(cur))
    return pieces


def _split_units(text: str, max_tokens: int) -> list[str]:
    """Break text into units no larger than max_tokens (paras → sentences → words)."""
    units: list[str] = []
    for para in _PARA_RE.split(text):
        para = para.strip()
        if not para:
            continue
        if _count_tokens(para) <= max_tokens:
            units.append(para)
            continue
        # Paragraph too big → split into sentences.
        for sent in _SENT_RE.split(para):
            sent = sent.strip()
            if not sent:
                continue
            if _count_tokens(sent) <= max_tokens:
                units.append(sent)
            else:
                # Sentence still too big (e.g. dense table row) → hard word split.
                units.extend(_hard_split(sent, max_tokens))
    return units


def chunk_text(
    text: str,
    *,
    max_tokens: int = 512,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """Chunk text into overlapping windows on unit boundaries.

    Greedily packs units into a window up to `max_tokens`, then starts the next
    window with a tail of the previous one (~`overlap_tokens`) for continuity.
    """
    text = (text or "").strip()
    if not text:
        return []

    units = _split_units(text, max_tokens)
    chunks: list[Chunk] = []
    current: list[str] = []
    current_tokens = 0
    idx = 0

    def flush() -> list[str]:
        nonlocal current, current_tokens, idx
        if not current:
            return []
        body = " ".join(current).strip()
        chunks.append(Chunk(index=idx, text=body, token_count=current_tokens))
        idx += 1
        # Build overlap tail from the end of the current window.
        tail: list[str] = []
        tail_tokens = 0
        for unit in reversed(current):
            t = _count_tokens(unit)
            if tail_tokens + t > overlap_tokens:
                break
            tail.insert(0, unit)
            tail_tokens += t
        return tail

    for unit in units:
        t = _count_tokens(unit)
        if current_tokens + t > max_tokens and current:
            tail = flush()
            current = list(tail)
            current_tokens = sum(_count_tokens(u) for u in current)
        current.append(unit)
        current_tokens += t

    if current:
        body = " ".join(current).strip()
        chunks.append(Chunk(index=idx, text=body, token_count=current_tokens))

    return chunks
