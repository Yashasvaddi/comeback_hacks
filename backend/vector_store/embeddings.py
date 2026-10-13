"""Local embedding model (sentence-transformers all-MiniLM-L6-v2).

Runs entirely on-device — zero API cost, zero network. The model is loaded
once into a module-level singleton. Output dim is 384.
"""
from __future__ import annotations

from config import settings

EMBED_DIM = 384

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts → list of float vectors."""
    if not texts:
        return []
    model = get_model()
    vectors = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,  # cosine-ready
    )
    return [v.tolist() for v in vectors]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
