"""Protocols that isolate the domain from provider and storage choices."""

from typing import Protocol, Sequence, TypeVar

from app.domain.models import (
    HistoricalTicket,
    IngestionBatchResult,
    SearchHit,
    SearchQuery,
    SourceDocument,
    TicketEmbedding,
    TicketEmbeddingCandidate,
)

T = TypeVar("T")


class EmbeddingProvider(Protocol):
    """Convert text into vectors using a replaceable embedding model."""

    @property
    def model_identifier(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


class TicketEmbeddingRepository(Protocol):
    """Read source tickets and persist embeddings in bounded batches."""

    def load_batch(
        self, *, after_ticket_id: int, limit: int, model_identifier: str
    ) -> Sequence[TicketEmbeddingCandidate]: ...

    def upsert_many(self, embeddings: Sequence[TicketEmbedding]) -> None: ...

    def delete_for_tickets(self, ticket_ids: Sequence[int], model_identifier: str) -> None: ...

    def ensure_vector_index(self, model_identifier: str, dimension: int) -> None: ...


class LLMProvider(Protocol):
    """Produce a typed result through a replaceable language model."""

    def generate_structured(
        self, *, system_prompt: str, user_prompt: str, response_type: type[T]
    ) -> T: ...


class SearchProvider(Protocol):
    """Retrieve candidate sources using a replaceable search implementation."""

    def search(self, query: SearchQuery) -> Sequence[SearchHit]: ...


class Reranker(Protocol):
    """Reorder retrieved candidates for a complaint or query."""

    def rerank(
        self, query: str, candidates: Sequence[SearchHit], limit: int
    ) -> Sequence[SearchHit]: ...


class SourceRepository(Protocol):
    """Persist and load source records without prescribing a database schema."""

    def upsert(self, documents: Sequence[SourceDocument]) -> None: ...

    def get(self, source_id: str) -> SourceDocument | None: ...


class HistoricalTicketRepository(Protocol):
    """Idempotently persist a batch from one historical dataset split."""

    def upsert_many(
        self, tickets: Sequence[HistoricalTicket]
    ) -> IngestionBatchResult: ...
