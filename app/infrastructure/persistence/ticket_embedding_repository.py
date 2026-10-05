"""Persistence adapter for versioned historical ticket embeddings."""

import hashlib
import json
from datetime import datetime, timezone
from collections.abc import Sequence
from typing import Any

from sqlalchemy import and_, delete, select, text
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import TicketEmbedding, TicketEmbeddingCandidate
from app.infrastructure.persistence.models import (
    HistoricalTicketEmbeddingRecord,
    HistoricalTicketRecord,
)


class SQLAlchemyTicketEmbeddingRepository:
    """Load ticket pages and upsert model-specific vectors transactionally."""

    def __init__(self, session_factory: sessionmaker[Session], engine: Engine) -> None:
        self._session_factory = session_factory
        self._engine = engine
        self._dialect_name = engine.dialect.name

    def load_batch(
        self, *, after_ticket_id: int, limit: int, model_identifier: str
    ) -> Sequence[TicketEmbeddingCandidate]:
        existing = HistoricalTicketEmbeddingRecord
        with self._session_factory() as session:
            rows = session.execute(
                select(
                    HistoricalTicketRecord.id,
                    HistoricalTicketRecord.subject,
                    HistoricalTicketRecord.body,
                    existing.source_text_hash,
                    existing.embedding_dimension,
                )
                .outerjoin(
                    existing,
                    and_(
                        existing.ticket_id == HistoricalTicketRecord.id,
                        existing.model_identifier == model_identifier,
                    ),
                )
                .where(HistoricalTicketRecord.id > after_ticket_id)
                .order_by(HistoricalTicketRecord.id)
                .limit(limit)
            ).all()
        return tuple(
            TicketEmbeddingCandidate(
                ticket_id=row.id,
                subject=row.subject,
                body=row.body,
                existing_source_text_hash=row.source_text_hash,
                existing_dimension=row.embedding_dimension,
            )
            for row in rows
        )

    def upsert_many(self, embeddings: Sequence[TicketEmbedding]) -> None:
        if not embeddings:
            return
        if self._dialect_name not in {"postgresql", "sqlite"}:
            raise ValueError(
                "Ticket embedding upserts support PostgreSQL and SQLite; "
                f"got {self._dialect_name!r}."
            )
        now = datetime.now(timezone.utc)
        rows: list[dict[str, Any]] = []
        for embedding in embeddings:
            vector_value: Any = list(embedding.vector)
            if self._dialect_name == "sqlite":
                vector_value = json.dumps(vector_value)
            rows.append(
                {
                    "ticket_id": embedding.ticket_id,
                    "model_identifier": embedding.model_identifier,
                    "embedding_dimension": embedding.dimension,
                    "source_text_hash": embedding.source_text_hash,
                    "embedding": vector_value,
                    "created_at": now,
                    "updated_at": now,
                }
            )

        with self._session_factory() as session:
            if self._dialect_name == "postgresql":
                statement = postgres_insert(HistoricalTicketEmbeddingRecord).values(rows)
            else:
                statement = sqlite_insert(HistoricalTicketEmbeddingRecord).values(rows)
            excluded = statement.excluded
            statement = statement.on_conflict_do_update(
                index_elements=["ticket_id", "model_identifier"],
                set_={
                    "embedding_dimension": excluded.embedding_dimension,
                    "source_text_hash": excluded.source_text_hash,
                    "embedding": excluded.embedding,
                    "updated_at": excluded.updated_at,
                },
            )
            session.execute(statement)
            session.commit()

    def delete_for_tickets(
        self, ticket_ids: Sequence[int], model_identifier: str
    ) -> None:
        if not ticket_ids:
            return
        with self._session_factory() as session:
            session.execute(
                delete(HistoricalTicketEmbeddingRecord).where(
                    HistoricalTicketEmbeddingRecord.ticket_id.in_(ticket_ids),
                    HistoricalTicketEmbeddingRecord.model_identifier == model_identifier,
                )
            )
            session.commit()

    def ensure_vector_index(self, model_identifier: str, dimension: int) -> None:
        """Create a dimension/model-specific cosine HNSW index if absent."""
        if self._dialect_name != "postgresql":
            return
        if dimension < 1 or dimension > 2000:
            raise ValueError("pgvector HNSW vector index supports dimensions 1 through 2000")
        index_suffix = hashlib.sha256(
            f"{model_identifier}:{dimension}".encode("utf-8")
        ).hexdigest()[:16]
        index_name = f"ix_ticket_embeddings_hnsw_{index_suffix}"
        escaped_model = model_identifier.replace("'", "''")
        statement = f"""
            CREATE INDEX IF NOT EXISTS \"{index_name}\"
            ON historical_ticket_embeddings
            USING hnsw ((embedding::vector({dimension})) vector_cosine_ops)
            WHERE model_identifier = '{escaped_model}'
              AND embedding_dimension = {dimension}
        """
        with self._engine.begin() as connection:
            connection.execute(text(statement))
