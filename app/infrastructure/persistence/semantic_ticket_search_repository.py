"""PostgreSQL/pgvector adapter for semantic historical ticket retrieval."""

from collections.abc import Sequence

from pgvector.sqlalchemy import Vector
from sqlalchemy import cast, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.domain.models import SemanticTicketResult
from app.infrastructure.persistence.models import (
    HistoricalTicketEmbeddingRecord,
    HistoricalTicketRecord,
)


class SQLAlchemySemanticTicketSearchRepository:
    """Run bounded nearest-neighbor searches in PostgreSQL."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def search_by_embedding(
        self,
        *,
        embedding: Sequence[float],
        model_identifier: str,
        dimension: int,
        limit: int,
    ) -> Sequence[SemanticTicketResult]:
        if dimension != len(embedding):
            raise ValueError("query embedding length does not match dimension")
        if limit < 1:
            raise ValueError("limit must be positive")

        # This cast matches the model/dimension-specific HNSW expression index.
        typed_vector = cast(HistoricalTicketEmbeddingRecord.embedding, Vector(dimension))
        distance = typed_vector.cosine_distance(list(embedding))
        statement = (
            select(HistoricalTicketRecord, distance.label("cosine_distance"))
            .join(
                HistoricalTicketEmbeddingRecord,
                HistoricalTicketEmbeddingRecord.ticket_id == HistoricalTicketRecord.id,
            )
            .options(selectinload(HistoricalTicketRecord.tags))
            .where(
                HistoricalTicketEmbeddingRecord.model_identifier == model_identifier,
                HistoricalTicketEmbeddingRecord.embedding_dimension == dimension,
            )
            .order_by(distance)
            .limit(limit)
        )
        with self._session_factory() as session:
            rows = session.execute(statement).all()

        return tuple(
            SemanticTicketResult(
                ticket_id=ticket.id,
                subject=ticket.subject,
                body=ticket.body,
                answer=ticket.answer,
                queue=ticket.queue,
                ticket_type=ticket.ticket_type,
                priority=ticket.priority,
                language=ticket.language,
                tags=tuple(tag.value for tag in sorted(ticket.tags, key=lambda item: item.position)),
                similarity=1.0 - float(cosine_distance),
                source_dataset=ticket.source_dataset,
                source_split=ticket.source_split,
                source_record_id=ticket.source_record_id,
                source_revision=ticket.source_revision,
            )
            for ticket, cosine_distance in rows
        )
