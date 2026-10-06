"""Protocols that isolate the domain from provider and storage choices."""

from typing import Any, Protocol, Sequence
from collections.abc import Mapping

from app.domain.models import (
    HistoricalTicket,
    ComplaintAnalysis,
    KnowledgeDocumentEmbedding,
    KnowledgeEmbeddingCandidate,
    KnowledgeIngestionResult,
    KnowledgeLexicalHit,
    KnowledgeSemanticHit,
    TelecomKnowledgeDocument,
    LexicalTicketResult,
    IngestionBatchResult,
    SearchHit,
    SearchQuery,
    SourceDocument,
    SemanticTicketResult,
    TicketEmbedding,
    TicketEmbeddingCandidate,
)

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


class SemanticTicketSearchRepository(Protocol):
    """Search historical tickets by vectors for one specific model."""

    def search_by_embedding(
        self,
        *,
        embedding: Sequence[float],
        model_identifier: str,
        dimension: int,
        limit: int,
    ) -> Sequence[SemanticTicketResult]: ...


class LexicalTicketSearchRepository(Protocol):
    """Search historical ticket subject/body using PostgreSQL full-text search."""

    def search_by_text(self, *, query: str, limit: int) -> Sequence[LexicalTicketResult]: ...


class LLMProvider(Protocol):
    """Return provider-independent JSON-shaped output for a supplied schema."""

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


class ComplaintAnalyzer(Protocol):
    """Parse complaint text into the validated support taxonomy."""

    def understand(self, complaint: str) -> ComplaintAnalysis: ...


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


class TelecomKnowledgeRepository(Protocol):
    """Persist curated telecom knowledge documents idempotently."""

    def upsert_many(
        self, documents: Sequence[TelecomKnowledgeDocument]
    ) -> KnowledgeIngestionResult: ...

    def search_by_text(self, *, query: str, limit: int) -> Sequence[KnowledgeLexicalHit]: ...


class KnowledgeEmbeddingRepository(Protocol):
    """Persist and retrieve vectors belonging only to telecom KB documents."""

    def load_batch(
        self, *, after_document_id: str, limit: int, model_identifier: str
    ) -> Sequence[KnowledgeEmbeddingCandidate]: ...

    def upsert_many(self, embeddings: Sequence[KnowledgeDocumentEmbedding]) -> None: ...

    def search_by_embedding(
        self,
        *,
        embedding: Sequence[float],
        model_identifier: str,
        dimension: int,
        limit: int,
    ) -> Sequence[KnowledgeSemanticHit]: ...

    def ensure_vector_index(self, model_identifier: str, dimension: int) -> None: ...
