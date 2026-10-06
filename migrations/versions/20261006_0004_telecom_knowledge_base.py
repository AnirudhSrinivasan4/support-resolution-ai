"""Create isolated telecom knowledge documents and embeddings.

Revision ID: 20261006_0004
Revises: 20261005_0003
Create Date: 2026-10-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision: str = "20261006_0004"
down_revision: Union[str, None] = "20261005_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("document_id", sa.String(length=160), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("product", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False),
        sa.Column("escalation_conditions", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=128), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('simple'::regconfig, "
                "coalesce(title, ''::text) || ' '::text || "
                "coalesce(content, ''::text) || ' '::text || "
                "coalesce(category, ''::text) || ' '::text || "
                "coalesce(product, ''::text) || ' '::text || "
                "coalesce(escalation_conditions, ''::text))",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_index(
        "ix_knowledge_documents_search_vector",
        "knowledge_documents",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_knowledge_documents_category", "knowledge_documents", ["category"]
    )
    op.create_index(
        "ix_knowledge_documents_product", "knowledge_documents", ["product"]
    )
    op.create_table(
        "knowledge_document_embeddings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.String(length=160), nullable=False),
        sa.Column("model_identifier", sa.String(length=512), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "embedding_dimension > 0", name="ck_knowledge_embedding_dimension"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["knowledge_documents.document_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "model_identifier",
            name="uq_knowledge_embedding_model",
        ),
    )
    op.create_index(
        "ix_knowledge_embeddings_model",
        "knowledge_document_embeddings",
        ["model_identifier"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_knowledge_embeddings_model", table_name="knowledge_document_embeddings"
    )
    op.drop_table("knowledge_document_embeddings")
    op.drop_index("ix_knowledge_documents_product", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_category", table_name="knowledge_documents")
    op.drop_index(
        "ix_knowledge_documents_search_vector", table_name="knowledge_documents"
    )
    op.drop_table("knowledge_documents")
