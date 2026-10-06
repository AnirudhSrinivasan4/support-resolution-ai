"""Evaluate abstention decisions using the existing end-to-end resolution service."""

from typing import Any

from app.evaluation.metrics import abstention_metrics
from app.evaluation.models import AbstentionExample, EvaluationDataset
from app.services.complaint_understanding import ComplaintUnderstandingError
from app.services.resolution import ResolutionGenerationError


def evaluate_abstention(dataset: EvaluationDataset, service: Any) -> dict[str, Any]:
    expected: list[bool] = []
    predicted: list[bool] = []
    records: list[dict[str, Any]] = []
    failed_count = 0
    for example in dataset.examples:
        assert isinstance(example, AbstentionExample)
        try:
            result = service.resolve(example.complaint)
        except Exception as error:
            invalid_output = (
                isinstance(error, (ComplaintUnderstandingError, ResolutionGenerationError))
                and error.__cause__ is None
            )
            if not invalid_output:
                raise RuntimeError(
                    f"abstention evaluation could not call the service for {example.id}: {error}"
                ) from error
            failed_count += 1
            records.append({
                "id": example.id,
                "status": "invalid_model_output",
                "expected_abstained": example.expected_abstained,
                "predicted_abstained": None,
                "error": str(error),
            })
            continue
        expected.append(example.expected_abstained)
        predicted.append(result.abstained)
        records.append({
            "id": example.id,
            "expected_abstained": example.expected_abstained,
            "predicted_abstained": result.abstained,
        })
    return {
        "dataset_version": dataset.version,
        "example_count": len(dataset.examples),
        "successful_response_count": len(expected),
        "invalid_model_output_count": failed_count,
        "metrics": abstention_metrics(expected, predicted) if expected else {
            "accuracy": None,
            "false_abstention_count": None,
            "missed_abstention_count": None,
        },
        "examples": records,
    }
