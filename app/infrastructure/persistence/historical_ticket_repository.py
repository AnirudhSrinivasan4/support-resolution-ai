"""PostgreSQL/SQLite upsert adapter for historical ticket batches."""

import hashlib
import json
from datetime import datetime, timezone
from collections.abc import Sequence
from typing import Any

from sqlalchemy import and_, delete, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import HistoricalTicket, IngestionBatchResult
from app.infrastructure.persistence.models import (
    HistoricalTicketRecord,
    HistoricalTicketTagRecord,
)


def _content_hash(ticket: HistoricalTicket) -> str:
    values = {
        "source_revision": ticket.source_revision,
        "subject": ticket.subject,
        "body": ticket.body,
        "answer": ticket.answer,
        "ticket_type": ticket.ticket_type,
        "queue": ticket.queue,
        "priority": ticket.priority,
        "language": ticket.language,
        "version": ticket.version,
        "tags": [(tag.position, tag.value) for tag in ticket.tags],
    }
    encoded = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class SQLAlchemyHistoricalTicketRepository:
    """Persist source-keyed records without duplicating repeat imports."""

    def __init__(self, session_factory: sessionmaker[Session], engine: Engine) -> None:
        self._session_factory = session_factory
        self._dialect_name = engine.dialect.name

    def upsert_many(self, tickets: Sequence[HistoricalTicket]) -> IngestionBatchResult:
        if not tickets:
            return IngestionBatchResult()
        tickets = list(tickets)
        if self._dialect_name not in {"postgresql", "sqlite"}:
            raise ValueError(
                "Historical ticket upserts support PostgreSQL and SQLite; "
                f"got {self._dialect_name!r}."
            )

        source_keys = {
            (ticket.source_dataset, ticket.source_split) for ticket in tickets
        }
        if len(source_keys) != 1:
            raise ValueError("Each upsert batch must contain one dataset split.")
        source_dataset, source_split = next(iter(source_keys))
        record_ids = [ticket.source_record_id for ticket in tickets]
        hashes = {ticket.source_record_id: _content_hash(ticket) for ticket in tickets}
        now = datetime.now(timezone.utc)

        with self._session_factory() as session:
            existing = self._existing_hashes(
                session, source_dataset, source_split, record_ids
            )
            inserted = sum(record_id not in existing for record_id in record_ids)
            updated = sum(
                record_id in existing and existing[record_id] != hashes[record_id]
                for record_id in record_ids
            )
            unchanged = len(tickets) - inserted - updated

            rows = [
                {
                    "source_dataset": ticket.source_dataset,
                    "source_split": ticket.source_split,
                    "source_record_id": ticket.source_record_id,
                    "source_revision": ticket.source_revision,
                    "subject": ticket.subject,
                    "body": ticket.body,
                    "answer": ticket.answer,
                    "ticket_type": ticket.ticket_type,
                    "queue": ticket.queue,
                    "priority": ticket.priority,
                    "language": ticket.language,
                    "version": ticket.version,
                    "content_hash": hashes[ticket.source_record_id],
                    "first_ingested_at": now,
                    "last_seen_at": now,
                }
                for ticket in tickets
            ]
            self._upsert_records(session, rows)
            session.flush()

            id_by_record = dict(
                session.execute(
                    select(
                        HistoricalTicketRecord.source_record_id,
                        HistoricalTicketRecord.id,
                    ).where(
                        and_(
                            HistoricalTicketRecord.source_dataset == source_dataset,
                            HistoricalTicketRecord.source_split == source_split,
                            HistoricalTicketRecord.source_record_id.in_(record_ids),
                        )
                    )
                ).all()
            )
            ticket_ids = list(id_by_record.values())
            if ticket_ids:
                session.execute(
                    delete(HistoricalTicketTagRecord).where(
                        HistoricalTicketTagRecord.ticket_id.in_(ticket_ids)
                    )
                )
                tag_rows = [
                    {
                        "ticket_id": id_by_record[ticket.source_record_id],
                        "position": tag.position,
                        "value": tag.value,
                    }
                    for ticket in tickets
                    for tag in ticket.tags
                ]
                if tag_rows:
                    session.add_all(
                        HistoricalTicketTagRecord(**row) for row in tag_rows
                    )
            session.commit()

        return IngestionBatchResult(
            processed=len(tickets),
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
        )

    @staticmethod
    def _existing_hashes(
        session: Session,
        source_dataset: str,
        source_split: str,
        record_ids: list[str],
    ) -> dict[str, str]:
        rows = session.execute(
            select(
                HistoricalTicketRecord.source_record_id,
                HistoricalTicketRecord.content_hash,
            ).where(
                and_(
                    HistoricalTicketRecord.source_dataset == source_dataset,
                    HistoricalTicketRecord.source_split == source_split,
                    HistoricalTicketRecord.source_record_id.in_(record_ids),
                )
            )
        ).all()
        return dict(rows)

    def _upsert_records(self, session: Session, rows: list[dict[str, Any]]) -> None:
        if self._dialect_name == "postgresql":
            statement = postgres_insert(HistoricalTicketRecord).values(rows)
        else:
            statement = sqlite_insert(HistoricalTicketRecord).values(rows)
        excluded = statement.excluded
        update_values = {
            field: getattr(excluded, field)
            for field in (
                "source_revision",
                "subject",
                "body",
                "answer",
                "ticket_type",
                "queue",
                "priority",
                "language",
                "version",
                "content_hash",
                "last_seen_at",
            )
        }
        if self._dialect_name == "postgresql":
            statement = statement.on_conflict_do_update(
                constraint="uq_historical_ticket_source", set_=update_values
            )
        else:
            statement = statement.on_conflict_do_update(
                index_elements=[
                    "source_dataset",
                    "source_split",
                    "source_record_id",
                ],
                set_=update_values,
            )
        session.execute(statement)
