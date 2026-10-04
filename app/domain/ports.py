"""Protocols that isolate the domain from provider and storage choices."""

from typing import Protocol, Sequence, TypeVar

from app.domain.models import SearchHit, SearchQuery, SourceDocument

T = TypeVar("T")


class EmbeddingProvider(Protocol):
    """Convert text into vectors using a replaceable embedding model."""

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


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
