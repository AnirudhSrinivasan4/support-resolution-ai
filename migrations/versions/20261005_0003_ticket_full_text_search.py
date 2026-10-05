"""Add a generated PostgreSQL full-text search vector for historical tickets.

Revision ID: 20261005_0003
Revises: 20261005_0002
Create Date: 2026-10-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261005_0003"
down_revision: Union[str, None] = "20261005_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "historical_tickets",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('simple'::regconfig, "
                "coalesce(subject, ''::text) || ' '::text || coalesce(body, ''::text))",
                persisted=True,
            ),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_historical_tickets_search_vector",
        "historical_tickets",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_historical_tickets_search_vector", table_name="historical_tickets"
    )
    op.drop_column("historical_tickets", "search_vector")
