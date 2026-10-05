"""Application service for validating and importing a saved train split."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.domain.models import HistoricalTicket, IngestionBatchResult
from app.domain.ports import HistoricalTicketRepository
from app.ingestion.normalize import DATASET_ID, ticket_from_row, validate_columns


@dataclass(frozen=True, slots=True)
class DatasetSnapshot:
    """Train rows and their source schema/fingerprint from a dataset adapter."""

    columns: Sequence[str]
    rows: Iterable[Mapping[str, Any]]
    revision: str | None


def ingest_train_snapshot(
    snapshot: DatasetSnapshot,
    repository: HistoricalTicketRepository,
    *,
    source_dataset: str = DATASET_ID,
    source_split: str = "train",
    limit: int | None = None,
    batch_size: int = 500,
) -> IngestionBatchResult:
    """Validate and idempotently persist a train split in bounded batches."""
    validate_columns(snapshot.columns)
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1 when provided")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    total = IngestionBatchResult()
    batch: list[HistoricalTicket] = []
    for row_index, row in enumerate(snapshot.rows):
        if limit is not None and row_index >= limit:
            break
        batch.append(
            ticket_from_row(
                row,
                source_dataset=source_dataset,
                source_split=source_split,
                source_record_id=str(row_index),
                source_revision=snapshot.revision,
            )
        )
        if len(batch) >= batch_size:
            total += repository.upsert_many(batch)
            batch.clear()

    if batch:
        total += repository.upsert_many(batch)
    return total
