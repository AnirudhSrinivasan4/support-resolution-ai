"""Shared application embedding provider factory."""

from functools import lru_cache

from app.core.config import settings
from app.infrastructure.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)
from app.services.semantic_retrieval import EXPECTED_EMBEDDING_DIMENSION


@lru_cache(maxsize=1)
def get_embedding_provider() -> SentenceTransformerEmbeddingProvider:
    """Load the configured multilingual model once per process for all corpora."""
    provider = SentenceTransformerEmbeddingProvider(
        settings.embedding_model,
        revision=settings.embedding_model_revision,
        batch_size=settings.embedding_batch_size,
    )
    if provider.dimension != EXPECTED_EMBEDDING_DIMENSION:
        raise RuntimeError("configured retrieval model must output 384 dimensions")
    return provider
