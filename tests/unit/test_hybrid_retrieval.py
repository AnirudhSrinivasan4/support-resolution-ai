"""Unit tests for PostgreSQL lexical search and RRF fusion."""

from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.domain.models import LexicalTicketResult, SemanticTicketResult
from app.infrastructure.persistence.lexical_ticket_search_repository import (
    SQLAlchemyLexicalTicketSearchRepository,
    build_lexical_query,
)
from app.services.hybrid_retrieval import (
    HybridRetrievalService,
    fuse_rankings,
)
from app.services.semantic_retrieval import SemanticRetrievalResponse


MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def _semantic(ticket_id: int, score: float) -> SemanticTicketResult:
    return SemanticTicketResult(
        ticket_id=ticket_id,
        subject=f"ticket {ticket_id}",
        body="support issue",
        answer="historical answer",
        queue="Support",
        ticket_type="Incident",
        priority="normal",
        language="en",
        tags=("sample",),
        similarity=score,
        source_dataset="public/support-sample",
        source_split="train",
        source_record_id=str(ticket_id),
        source_revision=None,
    )


def _lexical(ticket_id: int, score: float) -> LexicalTicketResult:
    semantic = _semantic(ticket_id, 0.0)
    return LexicalTicketResult(
        ticket_id=semantic.ticket_id,
        subject=semantic.subject,
        body=semantic.body,
        answer=semantic.answer,
        queue=semantic.queue,
        ticket_type=semantic.ticket_type,
        priority=semantic.priority,
        language=semantic.language,
        tags=semantic.tags,
        lexical_score=score,
        source_dataset=semantic.source_dataset,
        source_split=semantic.source_split,
        source_record_id=semantic.source_record_id,
        source_revision=semantic.source_revision,
    )


def test_lexical_query_uses_subject_body_vector_websearch_tsquery_and_rank_order() -> None:
    first = SimpleNamespace(
        id=1, subject="E4037 activation", body=None, answer="answer", queue="Q",
        ticket_type="Incident", priority="high", language="en",
        tags=[SimpleNamespace(position=1, value="esim")],
        source_dataset="public/test", source_split="train",
        source_record_id="1", source_revision="r1",
    )
    second = SimpleNamespace(
        id=2, subject=None, body="activation code error", answer="reply", queue="Q",
        ticket_type="Question", priority="normal", language="de", tags=[],
        source_dataset="public/test", source_split="train",
        source_record_id="2", source_revision=None,
    )

    class Result:
        def all(self):
            return [(first, 0.75), (second, 0.5)]

    class SessionDouble:
        statement = None

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, statement):
            self.statement = statement
            return Result()

    session = SessionDouble()
    repository = SQLAlchemyLexicalTicketSearchRepository(lambda: session)
    results = repository.search_by_text(query="  E4037 eSIM activation  ", limit=2)
    compiled = str(session.statement.compile(dialect=postgresql.dialect()))
    parameters = session.statement.compile(dialect=postgresql.dialect()).params

    assert "websearch_to_tsquery" in compiled
    assert "::REGCONFIG" in compiled
    assert "CAST(" in compiled and " AS TEXT)" in compiled
    assert "ts_rank_cd" in compiled
    assert "historical_tickets.search_vector @@" in compiled
    assert "ORDER BY ts_rank_cd" in compiled
    assert "LIMIT %(param_3)s::INTEGER" in compiled
    assert '"E4037" OR "eSIM" OR "activation"' in parameters.values()
    assert len(results) == 2
    assert [result.lexical_score for result in results] == [0.75, 0.5]
    assert results[0].tags == ("esim",)
    assert results[1].subject is None


def test_generated_lexical_vector_handles_missing_fields_and_excludes_answer() -> None:
    migration = (
        Path(__file__).parents[2]
        / "migrations"
        / "versions"
        / "20261005_0003_ticket_full_text_search.py"
    ).read_text(encoding="utf-8")
    expression = migration.split("sa.Computed(", 1)[1].split("persisted=True", 1)[0]
    assert "coalesce(subject" in expression
    assert "coalesce(body" in expression
    assert "answer" not in expression
    assert "'simple'::regconfig" in expression
    assert 'postgresql_using="gin"' in migration


def test_rrf_adds_both_rank_contributions_and_keeps_single_list_candidates() -> None:
    semantic = [_semantic(1, 0.95), _semantic(2, 0.9)]
    lexical = [_lexical(2, 0.2), _lexical(3, 0.1)]

    fused = fuse_rankings(semantic, lexical, rrf_constant=60, limit=10)

    assert [item.ticket.ticket_id for item in fused] == [2, 1, 3]
    assert fused[0].fused_score == pytest.approx(1 / 62 + 1 / 61)
    assert fused[0].semantic_rank == 2
    assert fused[0].lexical_rank == 1
    assert fused[0].semantic_score == 0.9
    assert fused[0].lexical_score == 0.2
    assert fused[1].fused_score == pytest.approx(1 / 61)
    assert fused[1].lexical_rank is None
    assert fused[2].fused_score == pytest.approx(1 / 62)
    assert fused[2].semantic_rank is None


def test_rrf_respects_final_top_k() -> None:
    fused = fuse_rankings(
        [_semantic(1, 0.9), _semantic(2, 0.8), _semantic(3, 0.7)],
        [],
        rrf_constant=60,
        limit=2,
    )
    assert [item.ticket.ticket_id for item in fused] == [1, 2]


def test_hybrid_service_uses_configured_candidate_sizes_and_returns_top_k() -> None:
    class SemanticDouble:
        model_identifier = MODEL

        def __init__(self) -> None:
            self.requested: tuple[str, int] | None = None

        def retrieve(self, query: str, *, top_k: int) -> SemanticRetrievalResponse:
            self.requested = (query, top_k)
            return SemanticRetrievalResponse(
                query=query,
                model_identifier=MODEL,
                results=(_semantic(1, 0.9), _semantic(2, 0.8)),
            )

    class LexicalDouble:
        def __init__(self) -> None:
            self.requested: tuple[str, int] | None = None

        def search_by_text(
            self, *, query: str, limit: int
        ) -> Sequence[LexicalTicketResult]:
            self.requested = (query, limit)
            return (_lexical(2, 0.7), _lexical(3, 0.6))

    semantic = SemanticDouble()
    lexical = LexicalDouble()
    service = HybridRetrievalService(
        semantic,
        lexical,
        semantic_candidate_limit=12,
        lexical_candidate_limit=14,
        rrf_constant=55,
    )

    response = service.retrieve("  billing problem ", top_k=2)

    assert response.query == "billing problem"
    assert semantic.requested == ("billing problem", 12)
    assert lexical.requested == ("billing problem", 14)
    assert len(response.results) == 2
    assert response.results[0].ticket.ticket_id == 2


def test_lexical_repository_returns_no_results_for_empty_query_without_database_call() -> None:
    class NoCall:
        def __call__(self):
            raise AssertionError("empty lexical query should not open a database session")

    assert SQLAlchemyLexicalTicketSearchRepository(NoCall()).search_by_text(
        query="   ", limit=5
    ) == ()


def test_lexical_query_builder_tokenizes_complaints_and_removes_search_operators() -> None:
    assert build_lexical_query("error E4037 while activating eSIM") == (
        '"error" OR "E4037" OR "activating" OR "eSIM"'
    )
    assert build_lexical_query("OR AND NOT") == ""
