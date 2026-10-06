"""Typed evaluation records and strict JSON dataset loading."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class EvaluationDatasetError(ValueError):
    """An evaluation dataset is malformed or inconsistent with the current KB."""


@dataclass(frozen=True, slots=True)
class ComplaintExample:
    id: str
    complaint: str
    expected_intent: str
    expected_category: str
    expected_product: str
    expected_severity: str
    expected_sentiment: str


@dataclass(frozen=True, slots=True)
class RetrievalExample:
    id: str
    query: str
    relevant_knowledge_source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AbstentionExample:
    id: str
    complaint: str
    expected_abstained: bool


@dataclass(frozen=True, slots=True)
class EvaluationDataset:
    version: str
    examples: tuple[Any, ...]


def _read_dataset(path: Path) -> tuple[str, list[dict[str, Any]]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvaluationDatasetError(f"cannot read evaluation dataset {path}: {error}") from error
    if not isinstance(payload, dict):
        raise EvaluationDatasetError(f"{path}: dataset root must be an object")
    version = payload.get("dataset_version")
    records = payload.get("examples")
    if not isinstance(version, str) or not version.strip():
        raise EvaluationDatasetError(f"{path}: dataset_version must be a non-empty string")
    if not isinstance(records, list) or not records:
        raise EvaluationDatasetError(f"{path}: examples must be a non-empty array")
    if any(not isinstance(record, dict) for record in records):
        raise EvaluationDatasetError(f"{path}: each example must be an object")
    return version, records


def _required_string(record: dict[str, Any], field: str, path: Path, index: int) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise EvaluationDatasetError(
            f"{path}: example {index} field {field!r} must be a non-empty string"
        )
    return value.strip()


def _validate_unique_ids(records: list[Any], path: Path) -> None:
    identifiers = [record.id for record in records]
    if len(identifiers) != len(set(identifiers)):
        raise EvaluationDatasetError(f"{path}: example IDs must be unique")


def load_complaint_dataset(path: Path) -> EvaluationDataset:
    version, rows = _read_dataset(path)
    examples = tuple(
        ComplaintExample(
            id=_required_string(row, "id", path, index),
            complaint=_required_string(row, "complaint", path, index),
            expected_intent=_required_string(row, "expected_intent", path, index),
            expected_category=_required_string(row, "expected_category", path, index),
            expected_product=_required_string(row, "expected_product", path, index),
            expected_severity=_required_string(row, "expected_severity", path, index),
            expected_sentiment=_required_string(row, "expected_sentiment", path, index),
        )
        for index, row in enumerate(rows)
    )
    _validate_unique_ids(examples, path)
    return EvaluationDataset(version, examples)


def load_retrieval_dataset(
    path: Path, *, known_source_ids: set[str] | None = None
) -> EvaluationDataset:
    version, rows = _read_dataset(path)
    examples: list[RetrievalExample] = []
    for index, row in enumerate(rows):
        raw_ids = row.get("relevant_knowledge_source_ids")
        if (
            not isinstance(raw_ids, list)
            or not raw_ids
            or any(not isinstance(value, str) or not value.strip() for value in raw_ids)
        ):
            raise EvaluationDatasetError(
                f"{path}: example {index} relevant_knowledge_source_ids must be a non-empty string array"
            )
        ids = tuple(value.strip() for value in raw_ids)
        if len(ids) != len(set(ids)):
            raise EvaluationDatasetError(f"{path}: example {index} has duplicate relevant source IDs")
        if known_source_ids is not None:
            unknown = sorted(set(ids) - known_source_ids)
            if unknown:
                raise EvaluationDatasetError(
                    f"{path}: example {index} references unknown KB source IDs: {', '.join(unknown)}"
                )
        examples.append(
            RetrievalExample(
                id=_required_string(row, "id", path, index),
                query=_required_string(row, "query", path, index),
                relevant_knowledge_source_ids=ids,
            )
        )
    result = tuple(examples)
    _validate_unique_ids(result, path)
    return EvaluationDataset(version, result)


def load_abstention_dataset(path: Path) -> EvaluationDataset:
    version, rows = _read_dataset(path)
    examples: list[AbstentionExample] = []
    for index, row in enumerate(rows):
        expected = row.get("expected_abstained")
        if not isinstance(expected, bool):
            raise EvaluationDatasetError(
                f"{path}: example {index} expected_abstained must be a boolean"
            )
        examples.append(
            AbstentionExample(
                id=_required_string(row, "id", path, index),
                complaint=_required_string(row, "complaint", path, index),
                expected_abstained=expected,
            )
        )
    result = tuple(examples)
    _validate_unique_ids(result, path)
    return EvaluationDataset(version, result)
