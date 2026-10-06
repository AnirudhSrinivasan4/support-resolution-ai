"""Evaluate complaint labels through the existing complaint-understanding service."""

from collections.abc import Callable
from typing import Any

from app.evaluation.metrics import accuracy, confusion_matrix, macro_f1
from app.evaluation.models import ComplaintExample, EvaluationDataset
from app.services.complaint_understanding import ComplaintUnderstandingError


def evaluate_complaints(
    dataset: EvaluationDataset, service: Any
) -> dict[str, Any]:
    examples = dataset.examples
    fields = {
        "intent": "expected_intent",
        "category": "expected_category",
        "product": "expected_product",
        "severity": "expected_severity",
        "sentiment": "expected_sentiment",
    }
    expected_by_field: dict[str, list[str]] = {name: [] for name in fields}
    predicted_by_field: dict[str, list[str]] = {name: [] for name in fields}
    records: list[dict[str, Any]] = []
    failed_count = 0
    for example in examples:
        assert isinstance(example, ComplaintExample)
        try:
            result = service.understand(example.complaint)
        except Exception as error:
            # Invalid structured labels are application-visible failures, not a reason to
            # drop a labelled example. Count every field as incorrect and expose the error.
            # A wrapped provider error indicates the service is unavailable and aborts.
            if not isinstance(error, ComplaintUnderstandingError) or error.__cause__ is not None:
                raise RuntimeError(
                    f"complaint evaluation could not call the service for {example.id}: {error}"
                ) from error
            failed_count += 1
            record = {"id": example.id, "status": "invalid_model_output", "error": str(error)}
            for predicted_field, expected_field in fields.items():
                expected = getattr(example, expected_field)
                expected_by_field[predicted_field].append(expected)
                predicted_by_field[predicted_field].append("__invalid_model_output__")
                record[f"expected_{predicted_field}"] = expected
                record[f"predicted_{predicted_field}"] = None
            records.append(record)
            continue
        record: dict[str, Any] = {"id": example.id}
        for predicted_field, expected_field in fields.items():
            expected = getattr(example, expected_field)
            predicted = getattr(result, predicted_field)
            expected_by_field[predicted_field].append(expected)
            predicted_by_field[predicted_field].append(predicted)
            record[f"expected_{predicted_field}"] = expected
            record[f"predicted_{predicted_field}"] = predicted
        records.append(record)
    metrics = {
        f"{field}_accuracy": accuracy(expected_by_field[field], predicted_by_field[field])
        for field in fields
    }
    metrics["intent_macro_f1"] = macro_f1(
        expected_by_field["intent"], predicted_by_field["intent"]
    )
    labels_with_support = sorted(set(expected_by_field["intent"]))
    metrics["intent_macro_f1_labels"] = labels_with_support
    metrics["intent_confusion_matrix"] = confusion_matrix(
        expected_by_field["intent"], predicted_by_field["intent"]
    )
    return {
        "dataset_version": dataset.version,
        "example_count": len(examples),
        "successful_response_count": len(examples) - failed_count,
        "invalid_model_output_count": failed_count,
        "metrics": metrics,
        "examples": records,
    }
