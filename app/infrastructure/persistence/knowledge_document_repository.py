"""Persistence and lexical search for curated telecom knowledge documents."""

from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import Text, cast, func, literal, select
from sqlalchemy.dialects.postgresql import REGCONFIG, insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.domain.models import (
    KnowledgeIngestionResult,
    KnowledgeLexicalHit,
    TelecomKnowledgeDocument,
    telecom_knowledge_content_hash,
)
from app.infrastructure.persistence.lexical_ticket_search_repository import (
    build_lexical_query,
)
from app.infrastructure.persistence.models import KnowledgeDocumentRecord


class SQLAlchemyKnowledgeDocumentRepository:
    """Upsert curated documents and return ranked PostgreSQL full-text matches."""

    def __init__(self, session_factory: sessionmaker[Session], dialect_name: str) -> None:
        self._session_factory = session_factory
        self._dialect_name = dialect_name

    def upsert_many(
        self, documents: Sequence[TelecomKnowledgeDocument]
    ) -> KnowledgeIngestionResult:
        if not documents:
            return KnowledgeIngestionResult()
        if self._dialect_name not in {"postgresql", "sqlite"}:
            raise ValueError(f"unsupported knowledge repository dialect: {self._dialect_name}")
        ids = [document.document_id for document in documents]
        if len(ids) != len(set(ids)):
            raise ValueError("a knowledge ingestion batch contains duplicate document IDs")

        hashes = {
            document.document_id: telecom_knowledge_content_hash(document)
            for document in documents
        }
        with self._session_factory() as session:
            existing = dict(
                session.execute(
                    select(
                        KnowledgeDocumentRecord.document_id,
                        KnowledgeDocumentRecord.content_hash,
                    ).where(KnowledgeDocumentRecord.document_id.in_(ids))
                ).all()
            )
            inserts: list[TelecomKnowledgeDocument] = []
            updates: list[TelecomKnowledgeDocument] = []
            unchanged = 0
            for document in documents:
                previous_hash = existing.get(document.document_id)
                if previous_hash is None:
                    inserts.append(document)
                elif previous_hash == hashes[document.document_id]:
                    unchanged += 1
                else:
                    updates.append(document)

            changed = [*inserts, *updates]
            if changed:
                now = datetime.now(timezone.utc)
                rows = [
                    {
                        "document_id": document.document_id,
                        "title": document.title,
                        "content": document.content,
                        "category": document.category,
                        "product": document.product,
                        "severity": document.severity,
                        "escalation_conditions": document.escalation_conditions,
                        "source": document.source,
                        "version": document.version,
                        "content_hash": hashes[document.document_id],
                        "created_at": now,
                        "updated_at": now,
                    }
                    for document in changed
                ]
                if self._dialect_name == "postgresql":
                    statement = postgres_insert(KnowledgeDocumentRecord).values(rows)
                else:
                    statement = sqlite_insert(KnowledgeDocumentRecord).values(rows)
                excluded = statement.excluded
                statement = statement.on_conflict_do_update(
                    index_elements=["document_id"],
                    set_={
                        "title": excluded.title,
                        "content": excluded.content,
                        "category": excluded.category,
                        "product": excluded.product,
                        "severity": excluded.severity,
                        "escalation_conditions": excluded.escalation_conditions,
                        "source": excluded.source,
                        "version": excluded.version,
                        "content_hash": excluded.content_hash,
                        "updated_at": excluded.updated_at,
                    },
                )
                session.execute(statement)
                session.commit()
        return KnowledgeIngestionResult(
            processed=len(documents),
            inserted=len(inserts),
            updated=len(updates),
            unchanged=unchanged,
        )

    def search_by_text(self, *, query: str, limit: int) -> Sequence[KnowledgeLexicalHit]:
        normalized_query = query.strip()
        if not normalized_query:
            return ()
        if limit < 1:
            raise ValueError("limit must be positive")
        lexical_query = build_lexical_query(normalized_query)
        if not lexical_query:
            return ()
        text_query = func.websearch_to_tsquery(
            literal("simple", type_=REGCONFIG()),
            cast(literal(lexical_query), Text()),
        )
        rank = func.ts_rank_cd(KnowledgeDocumentRecord.search_vector, text_query)
        statement = (
            select(KnowledgeDocumentRecord, rank.label("lexical_score"))
            .where(KnowledgeDocumentRecord.search_vector.op("@@")(text_query))
            .order_by(rank.desc(), KnowledgeDocumentRecord.document_id)
            .limit(limit)
        )
        with self._session_factory() as session:
            rows = session.execute(statement).all()
        return tuple(
            KnowledgeLexicalHit(
                document=TelecomKnowledgeDocument(
                    document_id=document.document_id,
                    title=document.title,
                    content=document.content,
                    category=document.category,
                    product=document.product,
                    severity=document.severity,
                    escalation_conditions=document.escalation_conditions,
                    source=document.source,
                    version=document.version,
                ),
                lexical_score=float(score),
            )
            for document, score in rows
        )
