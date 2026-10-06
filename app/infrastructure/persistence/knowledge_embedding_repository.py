"""Isolated pgvector persistence and search for telecom knowledge documents."""

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import and_, cast, select, text
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import (
    KnowledgeDocumentEmbedding,
    KnowledgeEmbeddingCandidate,
    KnowledgeSemanticHit,
    TelecomKnowledgeDocument,
    telecom_knowledge_content_hash,
)
from app.infrastructure.persistence.models import (
    KnowledgeDocumentEmbeddingRecord,
    KnowledgeDocumentRecord,
)


def _to_domain_document(record: KnowledgeDocumentRecord) -> TelecomKnowledgeDocument:
    return TelecomKnowledgeDocument(
        document_id=record.document_id,
        title=record.title,
        content=record.content,
        category=record.category,
        product=record.product,
        severity=record.severity,
        escalation_conditions=record.escalation_conditions,
        source=record.source,
        version=record.version,
    )


class SQLAlchemyKnowledgeEmbeddingRepository:
    """Read and write KB vectors without touching historical ticket embeddings."""

    def __init__(self, session_factory: sessionmaker[Session], engine: Engine) -> None:
        self._session_factory = session_factory
        self._engine = engine
        self._dialect_name = engine.dialect.name

    def load_batch(
        self, *, after_document_id: str, limit: int, model_identifier: str
    ) -> Sequence[KnowledgeEmbeddingCandidate]:
        existing = KnowledgeDocumentEmbeddingRecord
        statement = (
            select(
                KnowledgeDocumentRecord,
                existing.content_hash,
                existing.embedding_dimension,
            )
            .outerjoin(
                existing,
                and_(
                    existing.document_id == KnowledgeDocumentRecord.document_id,
                    existing.model_identifier == model_identifier,
                ),
            )
            .where(KnowledgeDocumentRecord.document_id > after_document_id)
            .order_by(KnowledgeDocumentRecord.document_id)
            .limit(limit)
        )
        with self._session_factory() as session:
            rows = session.execute(statement).all()
        return tuple(
            KnowledgeEmbeddingCandidate(
                document=_to_domain_document(row[0]),
                content_hash=row[0].content_hash,
                existing_content_hash=row[1],
                existing_dimension=row[2],
            )
            for row in rows
        )

    def upsert_many(
        self, embeddings: Sequence[KnowledgeDocumentEmbedding]
    ) -> None:
        if not embeddings:
            return
        if self._dialect_name not in {"postgresql", "sqlite"}:
            raise ValueError(f"unsupported knowledge embedding dialect: {self._dialect_name}")
        now = datetime.now(timezone.utc)
        rows: list[dict[str, Any]] = []
        for embedding in embeddings:
            vector_value: Any = list(embedding.vector)
            if self._dialect_name == "sqlite":
                vector_value = json.dumps(vector_value)
            rows.append(
                {
                    "document_id": embedding.document_id,
                    "model_identifier": embedding.model_identifier,
                    "embedding_dimension": embedding.dimension,
                    "content_hash": embedding.content_hash,
                    "embedding": vector_value,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        with self._session_factory() as session:
            if self._dialect_name == "postgresql":
                statement = postgres_insert(KnowledgeDocumentEmbeddingRecord).values(rows)
            else:
                statement = sqlite_insert(KnowledgeDocumentEmbeddingRecord).values(rows)
            excluded = statement.excluded
            statement = statement.on_conflict_do_update(
                index_elements=["document_id", "model_identifier"],
                set_={
                    "embedding_dimension": excluded.embedding_dimension,
                    "content_hash": excluded.content_hash,
                    "embedding": excluded.embedding,
                    "updated_at": excluded.updated_at,
                },
            )
            session.execute(statement)
            session.commit()

    def search_by_embedding(
        self,
        *,
        embedding: Sequence[float],
        model_identifier: str,
        dimension: int,
        limit: int,
    ) -> Sequence[KnowledgeSemanticHit]:
        if dimension != len(embedding):
            raise ValueError("query embedding length does not match dimension")
        if limit < 1:
            raise ValueError("limit must be positive")
        typed_vector = cast(KnowledgeDocumentEmbeddingRecord.embedding, Vector(dimension))
        distance = typed_vector.cosine_distance(list(embedding))
        statement = (
            select(KnowledgeDocumentRecord, distance.label("cosine_distance"))
            .join(
                KnowledgeDocumentEmbeddingRecord,
                KnowledgeDocumentEmbeddingRecord.document_id
                == KnowledgeDocumentRecord.document_id,
            )
            .where(
                KnowledgeDocumentEmbeddingRecord.model_identifier == model_identifier,
                KnowledgeDocumentEmbeddingRecord.embedding_dimension == dimension,
                KnowledgeDocumentEmbeddingRecord.content_hash
                == KnowledgeDocumentRecord.content_hash,
            )
            .order_by(distance)
            .limit(limit)
        )
        with self._session_factory() as session:
            rows = session.execute(statement).all()
        return tuple(
            KnowledgeSemanticHit(
                document=_to_domain_document(document),
                similarity=1.0 - float(distance_value),
            )
            for document, distance_value in rows
        )

    def ensure_vector_index(self, model_identifier: str, dimension: int) -> None:
        if self._engine.dialect.name != "postgresql":
            return
        if not 1 <= dimension <= 2000:
            raise ValueError("pgvector HNSW index supports dimensions 1 through 2000")
        suffix = hashlib.sha256(
            f"{model_identifier}:{dimension}".encode("utf-8")
        ).hexdigest()[:16]
        index_name = f"ix_knowledge_embeddings_hnsw_{suffix}"
        escaped_model = model_identifier.replace("'", "''")
        statement = f"""
            CREATE INDEX IF NOT EXISTS "{index_name}"
            ON knowledge_document_embeddings
            USING hnsw ((embedding::vector({dimension})) vector_cosine_ops)
            WHERE model_identifier = '{escaped_model}'
              AND embedding_dimension = {dimension}
        """
        with self._engine.begin() as connection:
            connection.execute(text(statement))

