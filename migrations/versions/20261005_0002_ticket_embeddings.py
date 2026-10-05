"""Add model-versioned pgvector embeddings for historical tickets.

Revision ID: 20261005_0002
Revises: 20261004_0001
Create Date: 2026-10-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "20261005_0002"
down_revision: Union[str, None] = "20261004_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "historical_ticket_embeddings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("model_identifier", sa.String(length=512), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("source_text_hash", sa.String(length=64), nullable=False),
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
        sa.CheckConstraint("embedding_dimension > 0", name="ck_ticket_embedding_dimension"),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["historical_tickets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ticket_id", "model_identifier", name="uq_ticket_embedding_model"
        ),
    )
    op.create_index(
        "ix_ticket_embeddings_model",
        "historical_ticket_embeddings",
        ["model_identifier"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ticket_embeddings_model", table_name="historical_ticket_embeddings"
    )
    op.drop_table("historical_ticket_embeddings")
