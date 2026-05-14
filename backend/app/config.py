"""
E-MPGT-IA — Centralized Configuration
All settings loaded from environment variables via Pydantic Settings.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration loaded from .env"""

    # ── Application ────────────────────────────────────────────
    app_env: str = Field(default="production")
    app_log_level: str = Field(default="INFO")
    cors_origins: str = Field(default="*")

    # ── Google AI / LLM ────────────────────────────────────────
    google_api_key: str = Field(default="")
    # LLM Settings
    llm_model: str = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")
    llm_temperature: float = 0.25 # Optimal for technical precision

    # ── Embedding ──────────────────────────────────────────────
    embedding_model: str = Field(default="gemini-embedding-001")
    embedding_dimensions: int = Field(default=768)

    # ── Qdrant ─────────────────────────────────────────────────
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)

    # ── Neo4j ──────────────────────────────────────────────────
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="empgt_neo4j_2026")

    # ── PostgreSQL ─────────────────────────────────────────────
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5433)
    postgres_db: str = Field(default="empgt")
    postgres_user: str = Field(default="empgt_user")
    postgres_password: str = Field(default="empgt_pass_2026")

    # ── MinIO ──────────────────────────────────────────────────
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default="empgt_admin")
    minio_secret_key: str = Field(default="empgt_minio_2026")
    minio_bucket: str = Field(default="empgt-documents")
    minio_secure: bool = Field(default=False)

    # ── Chunking ───────────────────────────────────────────────
    chunk_size: int = Field(default=1800)
    chunk_overlap: int = Field(default=350)

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
