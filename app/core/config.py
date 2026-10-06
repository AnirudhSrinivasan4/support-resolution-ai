"""Small environment-backed application settings."""

import os
from dataclasses import dataclass

from app.domain.models import ComplaintTaxonomy
from app.domain.taxonomy import DEFAULT_COMPLAINT_TAXONOMY


def _csv_setting(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return default
    return tuple(item.strip().lower() for item in value.split(",") if item.strip())


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
    knowledge_semantic_candidate_limit: int = int(
        os.getenv("KNOWLEDGE_SEMANTIC_CANDIDATE_LIMIT", "20")
    )
    knowledge_lexical_candidate_limit: int = int(
        os.getenv("KNOWLEDGE_LEXICAL_CANDIDATE_LIMIT", "20")
    )
    llm_provider: str = os.getenv("LLM_PROVIDER", "disabled").strip().lower()
    llm_api_key: str | None = os.getenv("LLM_API_KEY") or None
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "")
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
    resolution_knowledge_evidence_limit: int = int(
        os.getenv("RESOLUTION_KNOWLEDGE_EVIDENCE_LIMIT", "5")
    )
    resolution_historical_evidence_limit: int = int(
        os.getenv("RESOLUTION_HISTORICAL_EVIDENCE_LIMIT", "4")
    )
    resolution_min_knowledge_similarity: float = float(
        os.getenv("RESOLUTION_MIN_KNOWLEDGE_SIMILARITY", "0.40")
    )
    resolution_min_knowledge_lexical_score: float = float(
        os.getenv("RESOLUTION_MIN_KNOWLEDGE_LEXICAL_SCORE", "0.50")
    )
    complaint_intents: tuple[str, ...] = _csv_setting(
        "COMPLAINT_INTENTS", DEFAULT_COMPLAINT_TAXONOMY.intents
    )
    complaint_categories: tuple[str, ...] = _csv_setting(
        "COMPLAINT_CATEGORIES", DEFAULT_COMPLAINT_TAXONOMY.categories
    )
    complaint_products: tuple[str, ...] = _csv_setting(
        "COMPLAINT_PRODUCTS", DEFAULT_COMPLAINT_TAXONOMY.products
    )

    @property
    def complaint_taxonomy(self) -> ComplaintTaxonomy:
        return ComplaintTaxonomy(
            intents=self.complaint_intents,
            categories=self.complaint_categories,
            products=self.complaint_products,
        )


settings = Settings()
