"""Small environment-backed application settings."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    service_name: str = "Support Resolution Assistant"
    version: str = "0.1.0"
    environment: str = os.getenv("APP_ENV", "development")
    database_url: str | None = os.getenv("DATABASE_URL")
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    embedding_model_revision: str | None = os.getenv("EMBEDDING_MODEL_REVISION") or None
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))
    semantic_candidate_limit: int = int(os.getenv("SEMANTIC_CANDIDATE_LIMIT", "20"))
    lexical_candidate_limit: int = int(os.getenv("LEXICAL_CANDIDATE_LIMIT", "20"))
    rrf_constant: int = int(os.getenv("RRF_CONSTANT", "60"))


settings = Settings()
