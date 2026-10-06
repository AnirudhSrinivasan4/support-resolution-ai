"""SQLAlchemy mappings for the historical support corpus."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    """Base metadata shared by ORM models and Alembic migrations."""


class HistoricalTicketRecord(Base):
    """A historical ticket row with dataset provenance."""

    __tablename__ = "historical_tickets"
    __table_args__ = (
        UniqueConstraint(
            "source_dataset",
            "source_split",
            "source_record_id",
            name="uq_historical_ticket_source",
        ),
        Index("ix_historical_tickets_ticket_type", "ticket_type"),
        Index("ix_historical_tickets_queue", "queue"),
        Index("ix_historical_tickets_priority", "priority"),
        Index("ix_historical_tickets_language", "language"),
        Index(
            "ix_historical_tickets_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_dataset: Mapped[str] = mapped_column(String(255), nullable=False)
    source_split: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_revision: Mapped[str | None] = mapped_column(String(128))
    subject: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    # PostgreSQL uses a generated TSVECTOR; SQLite uses Text for portable fixtures.
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR().with_variant(Text(), "sqlite"), nullable=True
    )
    answer: Mapped[str | None] = mapped_column(Text)
    ticket_type: Mapped[str | None] = mapped_column(Text)
    queue: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    first_ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    tags: Mapped[list["HistoricalTicketTagRecord"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )


class HistoricalTicketTagRecord(Base):
    """A tag retaining its original tag_1 through tag_8 position."""

    __tablename__ = "historical_ticket_tags"
    __table_args__ = (
        CheckConstraint("position >= 1 AND position <= 8", name="ck_ticket_tag_position"),
        Index("ix_historical_ticket_tags_value", "value"),
    )

    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("historical_tickets.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    ticket: Mapped[HistoricalTicketRecord] = relationship(back_populates="tags")


class HistoricalTicketEmbeddingRecord(Base):
    """A model-version-specific vector for a historical ticket."""

    __tablename__ = "historical_ticket_embeddings"
    __table_args__ = (
        CheckConstraint("embedding_dimension > 0", name="ck_ticket_embedding_dimension"),
        UniqueConstraint(
            "ticket_id", "model_identifier", name="uq_ticket_embedding_model"
        ),
        Index("ix_ticket_embeddings_model", "model_identifier"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("historical_tickets.id", ondelete="CASCADE"), nullable=False
    )
    model_identifier: Mapped[str] = mapped_column(String(512), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    source_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector().with_variant(Text(), "sqlite"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class KnowledgeDocumentRecord(Base):
    """A versioned authoritative telecom troubleshooting article."""

    __tablename__ = "knowledge_documents"
    __table_args__ = (
        Index(
            "ix_knowledge_documents_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        Index("ix_knowledge_documents_category", "category"),
        Index("ix_knowledge_documents_product", "product"),
    )

    document_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    product: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False)
    escalation_conditions: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(128), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR().with_variant(Text(), "sqlite"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class KnowledgeDocumentEmbeddingRecord(Base):
    """Model-specific vector in the isolated telecom KB embedding collection."""

    __tablename__ = "knowledge_document_embeddings"
    __table_args__ = (
        CheckConstraint(
            "embedding_dimension > 0", name="ck_knowledge_embedding_dimension"
        ),
        UniqueConstraint(
            "document_id",
            "model_identifier",
            name="uq_knowledge_embedding_model",
        ),
        Index("ix_knowledge_embeddings_model", "model_identifier"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_documents.document_id", ondelete="CASCADE"),
        nullable=False,
    )
    model_identifier: Mapped[str] = mapped_column(String(512), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector().with_variant(Text(), "sqlite"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
