"""Focused embedding service/provider and persistence tests without model downloads."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, select

from app.domain.models import TicketEmbedding, TicketEmbeddingCandidate
from app.embeddings.service import (
    build_embedding_text,
    embed_historical_tickets,
    source_text_hash,
)
from app.infrastructure.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)
from app.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.persistence.models import (
    Base,
    HistoricalTicketEmbeddingRecord,
    HistoricalTicketRecord,
)
from app.infrastructure.persistence.ticket_embedding_repository import (
    SQLAlchemyTicketEmbeddingRepository,
)


class DeterministicModel:
    def get_sentence_embedding_dimension(self) -> int:
        return 3

    def encode(
        self,
        texts: list[str],
        *,
        batch_size: int,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> Any:
        assert convert_to_numpy is True
        assert show_progress_bar is False
        return [[float(len(text)), 2.0, 3.0] for text in texts]


class FakeRepository:
    def __init__(self, candidates: Sequence[TicketEmbeddingCandidate]) -> None:
        self.candidates = list(candidates)
        self.rows: dict[tuple[int, str], TicketEmbedding] = {}
        self.index: tuple[str, int] | None = None
        self.deleted: list[int] = []

    def ensure_vector_index(self, model_identifier: str, dimension: int) -> None:
        self.index = (model_identifier, dimension)

    def load_batch(
        self, *, after_ticket_id: int, limit: int, model_identifier: str
    ) -> Sequence[TicketEmbeddingCandidate]:
        results: list[TicketEmbeddingCandidate] = []
        for candidate in self.candidates:
            if candidate.ticket_id <= after_ticket_id:
                continue
            stored = self.rows.get((candidate.ticket_id, model_identifier))
            if stored:
                candidate = TicketEmbeddingCandidate(
                    ticket_id=candidate.ticket_id,
                    subject=candidate.subject,
                    body=candidate.body,
                    existing_source_text_hash=stored.source_text_hash,
                    existing_dimension=stored.dimension,
                )
            results.append(candidate)
            if len(results) == limit:
                break
        return results

    def upsert_many(self, embeddings: Sequence[TicketEmbedding]) -> None:
        for embedding in embeddings:
            self.rows[(embedding.ticket_id, embedding.model_identifier)] = embedding

    def delete_for_tickets(
        self, ticket_ids: Sequence[int], model_identifier: str
    ) -> None:
        self.deleted.extend(ticket_ids)
        for ticket_id in ticket_ids:
            self.rows.pop((ticket_id, model_identifier), None)


def _provider() -> SentenceTransformerEmbeddingProvider:
    return SentenceTransformerEmbeddingProvider(
        "test/deterministic", batch_size=2, model_factory=lambda *_args, **_kwargs: DeterministicModel()
    )


def test_embedding_text_uses_only_subject_and_body_and_handles_missing_parts() -> None:
    assert build_embedding_text("  Router drops  ", "  Every evening  ") == (
        "Subject: Router drops\nBody: Every evening"
    )
    assert build_embedding_text(None, "Body only") == "Body: Body only"
    assert build_embedding_text("Subject only", None) == "Subject: Subject only"
    assert build_embedding_text("  ", None) is None
    assert build_embedding_text(None, None) is None


def test_fake_model_adapter_reports_derived_dimension_and_encodes() -> None:
    provider = _provider()
    assert provider.model_identifier == "test/deterministic"
    assert provider.dimension == 3
    assert provider.embed(["one", "two"]) == [[3.0, 2.0, 3.0], [3.0, 2.0, 3.0]]


def test_pipeline_persists_embedding_and_reuses_unchanged_source() -> None:
    candidate = TicketEmbeddingCandidate(1, "Router", "drops nightly")
    repository = FakeRepository([candidate])
    provider = _provider()

    first = embed_historical_tickets(repository, provider, batch_size=1)
    second = embed_historical_tickets(repository, provider, batch_size=1)

    assert first.embedded == 1
    assert first.reused == 0
    assert second.embedded == 0
    assert second.reused == 1
    row = repository.rows[(1, provider.model_identifier)]
    assert row.dimension == 3
    assert row.source_text_hash == source_text_hash("Router", "drops nightly")
    assert row.vector == (float(len("Subject: Router\nBody: drops nightly")), 2.0, 3.0)
    assert repository.index == (provider.model_identifier, 3)


def test_pipeline_regenerates_when_source_changes_and_skips_empty_text() -> None:
    repository = FakeRepository(
        [TicketEmbeddingCandidate(1, "Router", "old"), TicketEmbeddingCandidate(2, None, "  ")]
    )
    provider = _provider()
    embed_historical_tickets(repository, provider, batch_size=2)
    repository.candidates[0] = TicketEmbeddingCandidate(1, None, "  ")

    result = embed_historical_tickets(repository, provider, batch_size=2)

    assert result.embedded == 0
    assert result.skipped_no_text == 2
    assert (1, provider.model_identifier) not in repository.rows
    assert repository.deleted == [1]


def test_sqlite_persistence_round_trip_and_schema_constraints() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    repository = SQLAlchemyTicketEmbeddingRepository(session_factory, engine)
    try:
        with session_factory() as session:
            ticket = HistoricalTicketRecord(
                source_dataset="synthetic/test",
                source_split="train",
                source_record_id="0",
                content_hash="a" * 64,
                subject="Router",
                body="drops nightly",
            )
            session.add(ticket)
            session.commit()
            ticket_id = ticket.id

        source_hash = source_text_hash("Router", "drops nightly")
        repository.upsert_many(
            [
                TicketEmbedding(
                    ticket_id=ticket_id,
                    model_identifier="test/deterministic",
                    dimension=3,
                    source_text_hash=source_hash,
                    vector=(1.0, 2.0, 3.0),
                )
            ]
        )
        with session_factory() as session:
            stored = session.scalar(select(HistoricalTicketEmbeddingRecord))
            assert stored is not None
            assert stored.embedding_dimension == 3
            assert stored.model_identifier == "test/deterministic"
            assert json.loads(stored.embedding) == [1.0, 2.0, 3.0]

        columns = {column["name"] for column in inspect(engine).get_columns(
            "historical_ticket_embeddings"
        )}
        assert {
            "ticket_id",
            "model_identifier",
            "embedding_dimension",
            "source_text_hash",
            "embedding",
            "created_at",
            "updated_at",
        } <= columns
        assert inspect(engine).get_unique_constraints(
            "historical_ticket_embeddings"
        )[0]["name"] == "uq_ticket_embedding_model"
    finally:
        engine.dispose()


def test_embedding_migration_is_chained_after_historical_ticket_migration() -> None:
    migration = Path(__file__).parents[2] / "migrations" / "versions" / (
        "20261005_0002_ticket_embeddings.py"
    )
    source = migration.read_text(encoding="utf-8")
    assert 'revision: str = "20261005_0002"' in source
    assert 'down_revision: Union[str, None] = "20261004_0001"' in source
    assert 'op.execute("CREATE EXTENSION IF NOT EXISTS vector")' in source
    assert '"embedding", Vector()' in source
