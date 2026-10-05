"""Focused semantic retrieval tests using deterministic providers and repositories."""

from collections.abc import Sequence
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.domain.models import SemanticTicketResult
from app.services.semantic_retrieval import (
    EXPECTED_EMBEDDING_DIMENSION,
    InvalidSemanticQuery,
    SemanticRetrievalService,
)
from app.infrastructure.persistence.semantic_ticket_search_repository import (
    SQLAlchemySemanticTicketSearchRepository,
)


class FakeEmbeddingProvider:
    model_identifier = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    dimension = EXPECTED_EMBEDDING_DIMENSION

    def __init__(self, vector: Sequence[float] | None = None) -> None:
        self.vector = vector or [0.1] * self.dimension
        self.inputs: list[str] = []

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        self.inputs.extend(texts)
        return [self.vector for _ in texts]


class FakeSearchRepository:
    def __init__(self, results: Sequence[SemanticTicketResult]) -> None:
        self.results = list(results)
        self.call: dict[str, object] | None = None

    def search_by_embedding(
        self,
        *,
        embedding: Sequence[float],
        model_identifier: str,
        dimension: int,
        limit: int,
    ) -> Sequence[SemanticTicketResult]:
        self.call = {
            "embedding": embedding,
            "model_identifier": model_identifier,
            "dimension": dimension,
            "limit": limit,
        }
        return self.results[:limit]


def _result(ticket_id: int, similarity: float) -> SemanticTicketResult:
    return SemanticTicketResult(
        ticket_id=ticket_id,
        subject="Password reset email",
        body="Reset message did not arrive",
        answer="Check the email address and spam folder.",
        queue="Account",
        ticket_type="Incident",
        priority="normal",
        language="en",
        tags=("login", "email"),
        similarity=similarity,
        source_dataset="public/support-sample",
        source_split="train",
        source_record_id=str(ticket_id),
        source_revision="abc123",
    )


def test_retrieval_normalizes_query_and_requests_configured_top_k() -> None:
    provider = FakeEmbeddingProvider()
    repository = FakeSearchRepository([_result(1, 0.95), _result(2, 0.8)])

    response = SemanticRetrievalService(provider, repository).retrieve(
        "  cannot reset my password  ", top_k=2
    )

    assert response.query == "cannot reset my password"
    assert provider.inputs == ["cannot reset my password"]
    assert [item.ticket_id for item in response.results] == [1, 2]
    assert repository.call is not None
    assert repository.call["model_identifier"] == provider.model_identifier
    assert repository.call["dimension"] == 384
    assert repository.call["limit"] == 2


@pytest.mark.parametrize("query", ["", "   ", "\n\t"])
def test_retrieval_rejects_empty_query(query: str) -> None:
    service = SemanticRetrievalService(FakeEmbeddingProvider(), FakeSearchRepository([]))
    with pytest.raises(InvalidSemanticQuery):
        service.retrieve(query)


def test_retrieval_rejects_top_k_outside_configured_bounds() -> None:
    service = SemanticRetrievalService(FakeEmbeddingProvider(), FakeSearchRepository([]))
    with pytest.raises(InvalidSemanticQuery):
        service.retrieve("help", top_k=21)


def test_retrieval_rejects_non_384_model() -> None:
    provider = FakeEmbeddingProvider()
    provider.dimension = 3
    with pytest.raises(ValueError, match="384-dimensional"):
        SemanticRetrievalService(provider, FakeSearchRepository([]))


def test_repository_results_keep_answer_metadata_and_source_provenance() -> None:
    result = _result(7, 0.91)
    repository = FakeSearchRepository([result])
    response = SemanticRetrievalService(FakeEmbeddingProvider(), repository).retrieve("login")

    match = response.results[0]
    assert match.answer == "Check the email address and spam folder."
    assert (match.queue, match.ticket_type, match.priority, match.language) == (
        "Account",
        "Incident",
        "normal",
        "en",
    )
    assert match.tags == ("login", "email")
    assert (match.source_dataset, match.source_split, match.source_record_id) == (
        "public/support-sample",
        "train",
        "7",
    )


def test_sql_adapter_filters_model_and_dimension_orders_by_cosine_and_maps_source() -> None:
    ticket = SimpleNamespace(
        id=7,
        subject="Password reset email",
        body="Reset message did not arrive",
        answer="Check spam.",
        queue="Account",
        ticket_type="Incident",
        priority="normal",
        language="en",
        tags=[SimpleNamespace(position=2, value="email"), SimpleNamespace(position=1, value="login")],
        source_dataset="public/support-sample",
        source_split="train",
        source_record_id="7",
        source_revision="abc123",
    )

    class Result:
        def all(self):
            return [(ticket, 0.09)]

    class SessionDouble:
        def __init__(self) -> None:
            self.statement = None

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, statement):
            self.statement = statement
            return Result()

    session = SessionDouble()
    repository = SQLAlchemySemanticTicketSearchRepository(lambda: session)
    results = repository.search_by_embedding(
        embedding=[0.1] * 384,
        model_identifier=FakeEmbeddingProvider.model_identifier,
        dimension=384,
        limit=3,
    )
    compiled = str(session.statement.compile(dialect=postgresql.dialect()))

    assert "cosine_distance" in compiled
    assert "ORDER BY CAST(historical_ticket_embeddings.embedding AS VECTOR(384)) <=> " in compiled
    assert "historical_ticket_embeddings.model_identifier =" in compiled
    assert "historical_ticket_embeddings.embedding_dimension =" in compiled
    assert "LIMIT" in compiled
    assert results[0].similarity == pytest.approx(0.91)
    assert results[0].tags == ("login", "email")
    assert results[0].answer == "Check spam."
