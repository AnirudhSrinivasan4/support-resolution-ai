"""Orchestration for semantic retrieval over historical support tickets."""

from dataclasses import dataclass

from app.domain.models import SemanticTicketResult
from app.domain.ports import EmbeddingProvider, SemanticTicketSearchRepository

EXPECTED_EMBEDDING_DIMENSION = 384
MAX_TOP_K = 20


class InvalidSemanticQuery(ValueError):
    """Raised when a query cannot be embedded or its size is invalid."""


@dataclass(frozen=True, slots=True)
class SemanticRetrievalResponse:
    query: str
    model_identifier: str
    results: tuple[SemanticTicketResult, ...]


class SemanticRetrievalService:
    """Embed one complaint and retrieve the nearest matching historical tickets."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        repository: SemanticTicketSearchRepository,
        *,
        max_top_k: int = MAX_TOP_K,
    ) -> None:
        if max_top_k < 1:
            raise ValueError("max_top_k must be positive")
        if embedding_provider.dimension != EXPECTED_EMBEDDING_DIMENSION:
            raise ValueError("semantic retrieval requires a 384-dimensional embedding model")
        self._embedding_provider = embedding_provider
        self._repository = repository
        self._max_top_k = max_top_k

    def retrieve(self, query: str, *, top_k: int = 5) -> SemanticRetrievalResponse:
        normalized_query = query.strip() if isinstance(query, str) else ""
        if not normalized_query:
            raise InvalidSemanticQuery("query must contain non-whitespace text")
        if top_k < 1 or top_k > self._max_top_k:
            raise InvalidSemanticQuery(f"top_k must be between 1 and {self._max_top_k}")

        vectors = self._embedding_provider.embed([normalized_query])
        if len(vectors) != 1 or len(vectors[0]) != EXPECTED_EMBEDDING_DIMENSION:
            raise RuntimeError("embedding provider returned an invalid query vector")
        results = self._repository.search_by_embedding(
            embedding=vectors[0],
            model_identifier=self._embedding_provider.model_identifier,
            dimension=EXPECTED_EMBEDDING_DIMENSION,
            limit=top_k,
        )
        return SemanticRetrievalResponse(
            query=normalized_query,
            model_identifier=self._embedding_provider.model_identifier,
            results=tuple(results),
        )
