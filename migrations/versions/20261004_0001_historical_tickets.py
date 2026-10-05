"""Create normalized historical ticket and tag tables.

Revision ID: 20261004_0001
Revises:
Create Date: 2026-10-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261004_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "historical_tickets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_dataset", sa.String(length=255), nullable=False),
        sa.Column("source_split", sa.String(length=64), nullable=False),
        sa.Column("source_record_id", sa.String(length=128), nullable=False),
        sa.Column("source_revision", sa.String(length=128), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("ticket_type", sa.Text(), nullable=True),
        sa.Column("queue", sa.Text(), nullable=True),
        sa.Column("priority", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "first_ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_dataset",
            "source_split",
            "source_record_id",
            name="uq_historical_ticket_source",
        ),
    )
    op.create_index(
        "ix_historical_tickets_ticket_type",
        "historical_tickets",
        ["ticket_type"],
    )
    op.create_index("ix_historical_tickets_queue", "historical_tickets", ["queue"])
    op.create_index(
        "ix_historical_tickets_priority", "historical_tickets", ["priority"]
    )
    op.create_index(
        "ix_historical_tickets_language", "historical_tickets", ["language"]
    )
    op.create_table(
        "historical_ticket_tags",
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 1 AND position <= 8", name="ck_ticket_tag_position"
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["historical_tickets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("ticket_id", "position"),
    )
    op.create_index(
        "ix_historical_ticket_tags_value", "historical_ticket_tags", ["value"]
    )


def downgrade() -> None:
    op.drop_index("ix_historical_ticket_tags_value", table_name="historical_ticket_tags")
    op.drop_table("historical_ticket_tags")
    op.drop_index("ix_historical_tickets_language", table_name="historical_tickets")
    op.drop_index("ix_historical_tickets_priority", table_name="historical_tickets")
    op.drop_index("ix_historical_tickets_queue", table_name="historical_tickets")
    op.drop_index(
        "ix_historical_tickets_ticket_type", table_name="historical_tickets"
    )
    op.drop_table("historical_tickets")
