"""Validation and normalization for historical support dataset rows."""

import math
from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any

from app.domain.models import HistoricalTicket, HistoricalTicketTag

DATASET_ID = "Tobi-Bueck/customer-support-tickets"
REQUIRED_COLUMNS = (
    "subject",
    "body",
    "answer",
    "type",
    "queue",
    "priority",
    "language",
    "version",
)
TAG_COLUMNS = tuple(f"tag_{position}" for position in range(1, 9))


class DatasetSchemaError(ValueError):
    """Raised when the saved dataset does not have its required columns."""


def validate_columns(columns: Sequence[str]) -> None:
    """Require core source columns; tag columns may be absent or null."""
    missing = sorted(set(REQUIRED_COLUMNS).difference(columns))
    if missing:
        raise DatasetSchemaError(
            "Saved dataset is missing required columns: " + ", ".join(missing)
        )


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, Real) and not isinstance(value, bool):
        try:
            return math.isnan(value)
        except TypeError:
            return False
    return False


def _optional_text(value: Any) -> str | None:
    if _is_missing(value):
        return None
    if isinstance(value, str):
        return value
    return str(value)


def ticket_from_row(
    row: Mapping[str, Any],
    *,
    source_dataset: str,
    source_split: str,
    source_record_id: str,
    source_revision: str | None,
) -> HistoricalTicket:
    """Map source values without trimming or rewriting ticket text."""
    tags = tuple(
        HistoricalTicketTag(position=position, value=text)
        for position, column in enumerate(TAG_COLUMNS, start=1)
        if not _is_missing(row.get(column))
        if (text := _optional_text(row.get(column))) is not None and text != ""
    )
    return HistoricalTicket(
        source_dataset=source_dataset,
        source_split=source_split,
        source_record_id=source_record_id,
        source_revision=source_revision,
        subject=_optional_text(row.get("subject")),
        body=_optional_text(row.get("body")),
        answer=_optional_text(row.get("answer")),
        ticket_type=_optional_text(row.get("type")),
        queue=_optional_text(row.get("queue")),
        priority=_optional_text(row.get("priority")),
        language=_optional_text(row.get("language")),
        version=_optional_text(row.get("version")),
        tags=tags,
    )
