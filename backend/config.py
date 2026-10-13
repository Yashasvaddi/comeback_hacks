"""Central application settings, loaded from environment / .env.

All configuration flows through the `settings` singleton. Nothing reads
os.environ directly elsewhere in the codebase.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root is the parent of backend/ — resolve .env there so settings load
# regardless of the current working directory (host runs from backend/, etc.).
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── LLM: Ollama cloud models via local proxy (free, OpenAI-compatible) ──
    # Default points at the local Ollama daemon, which proxies `*-cloud`
    # models to Ollama's servers (no local GPU, no API key in this app).
    # To call ollama.com directly instead, set OLLAMA_BASE_URL=https://ollama.com/v1
    # and OLLAMA_API_KEY=<key>, and drop the `-cloud` suffix from the model names.
    ollama_api_key: str = "ollama"  # any non-empty value; local proxy ignores it
    ollama_base_url: str = "http://localhost:11434/v1"
    llm_model_fast: str = "gpt-oss:20b-cloud"
    llm_model_smart: str = "gpt-oss:120b-cloud"

    # ── Embeddings (local) ──
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── PostgreSQL ──
    postgres_url: str = (
        "postgresql+asyncpg://ikb:change_me_postgres@localhost:55432/industrial_kb"
    )

    # ── Neo4j ──
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_password"

    # ── Qdrant ──
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "industrial_chunks"

    # ── MinIO ──
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "industrial-docs"
    minio_secure: bool = False

    # ── App ──
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"
    max_upload_mb: int = 100

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
