"""Ingestion tests use a synthetic saved DatasetDict and local SQLite."""

import json
from pathlib import Path
from typing import Any

import pytest
from datasets import Dataset, DatasetDict
from sqlalchemy import func, select

from app.domain.models import IngestionBatchResult
from app.ingestion.normalize import DatasetSchemaError
from app.ingestion.service import ingest_train_snapshot
from app.infrastructure.datasets.huggingface_saved_dataset import (
    HuggingFaceSavedDatasetLoader,
)
from app.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.persistence.historical_ticket_repository import (
    SQLAlchemyHistoricalTicketRepository,
)
from app.infrastructure.persistence.models import Base, HistoricalTicketRecord

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "synthetic_historical_tickets.json"


def _fixture_records() -> list[dict[str, Any]]:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def _saved_dataset(
    directory: Path, records: list[dict[str, Any]] | None = None
) -> Path:
    path = directory / "saved_support_dataset"
    DatasetDict({"train": Dataset.from_list(records or _fixture_records())}).save_to_disk(
        str(path)
    )
    return path


def _repository() -> tuple[Any, Any, SQLAlchemyHistoricalTicketRepository]:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    return engine, session_factory, SQLAlchemyHistoricalTicketRepository(
        session_factory, engine
    )


def _ingest(path: Path, repository: SQLAlchemyHistoricalTicketRepository):
    snapshot = HuggingFaceSavedDatasetLoader().load_train(path)
    return ingest_train_snapshot(
        snapshot,
        repository,
        source_dataset="synthetic/support-ticket-fixture",
    )


def _ticket_count(session_factory: Any) -> int:
    with session_factory() as session:
        return int(session.scalar(select(func.count()).select_from(HistoricalTicketRecord)) or 0)


def test_successful_ingestion_imports_all_ten_fixture_records(tmp_path: Path) -> None:
    dataset_path = _saved_dataset(tmp_path)
    engine, session_factory, repository = _repository()
    try:
        result = _ingest(dataset_path, repository)

        assert result == IngestionBatchResult(processed=10, inserted=10)
        assert _ticket_count(session_factory) == 10
    finally:
        engine.dispose()


def test_missing_optional_values_become_null_and_empty_tags_are_omitted(
    tmp_path: Path,
) -> None:
    dataset_path = _saved_dataset(tmp_path)
    engine, session_factory, repository = _repository()
    try:
        _ingest(dataset_path, repository)
        with session_factory() as session:
            ticket = session.scalar(
                select(HistoricalTicketRecord).where(
                    HistoricalTicketRecord.source_record_id == "1"
                )
            )

            assert ticket is not None
            assert ticket.answer is None
            assert ticket.queue is None
            assert ticket.version is None
            assert [(tag.position, tag.value) for tag in ticket.tags] == [
                (1, "account"),
                (2, "password"),
            ]
    finally:
        engine.dispose()


def test_repeated_ingestion_is_idempotent(tmp_path: Path) -> None:
    dataset_path = _saved_dataset(tmp_path)
    engine, session_factory, repository = _repository()
    try:
        first = _ingest(dataset_path, repository)
        second = _ingest(dataset_path, repository)

        assert first.inserted == 10
        assert second == IngestionBatchResult(processed=10, unchanged=10)
        assert _ticket_count(session_factory) == 10
    finally:
        engine.dispose()


def test_original_ticket_text_and_source_provenance_are_preserved(
    tmp_path: Path,
) -> None:
    dataset_path = _saved_dataset(tmp_path)
    snapshot = HuggingFaceSavedDatasetLoader().load_train(dataset_path)
    engine, session_factory, repository = _repository()
    try:
        _ingest(dataset_path, repository)
        with session_factory() as session:
            ticket = session.scalar(
                select(HistoricalTicketRecord).where(
                    HistoricalTicketRecord.source_record_id == "0"
                )
            )

            assert ticket is not None
            assert ticket.subject == "  Package marked delivered  "
            assert ticket.body == (
                "  My order is still marked as delivered.\n"
                "I checked the porch and mailroom.  "
            )
            assert ticket.answer == (
                "Please confirm the delivery address.\n\n"
                "If it is correct, allow one business day and contact us again."
            )
            assert ticket.source_dataset == "synthetic/support-ticket-fixture"
            assert ticket.source_split == "train"
            assert ticket.source_record_id == "0"
            assert ticket.source_revision == snapshot.revision
            assert ticket.source_revision
    finally:
        engine.dispose()


@pytest.mark.parametrize("missing_column", ["body", "queue"])
def test_missing_required_columns_fail_before_persistence(
    tmp_path: Path, missing_column: str
) -> None:
    records = _fixture_records()
    for record in records:
        record.pop(missing_column)
    dataset_path = _saved_dataset(tmp_path, records)
    engine, session_factory, repository = _repository()
    try:
        snapshot = HuggingFaceSavedDatasetLoader().load_train(dataset_path)

        with pytest.raises(DatasetSchemaError, match=missing_column):
            ingest_train_snapshot(snapshot, repository)
        assert _ticket_count(session_factory) == 0
    finally:
        engine.dispose()
