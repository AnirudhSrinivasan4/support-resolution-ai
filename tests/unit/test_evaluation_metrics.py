"""Pure metric tests; these do not load model or database providers."""

import json

import pytest

from app.core.config import settings
from app.evaluation.metrics import (
    abstention_metrics,
    accuracy,
    confusion_matrix,
    macro_f1,
    retrieval_metrics,
)
from app.evaluation.models import (
    ComplaintExample,
    EvaluationDataset,
    EvaluationDatasetError,
    load_abstention_dataset,
    load_complaint_dataset,
    load_retrieval_dataset,
)
from app.services.complaint_understanding import ComplaintUnderstandingError
from app.evaluation.complaint_understanding import evaluate_complaints
from app.evaluation.abstention import evaluate_abstention
from app.evaluation.models import AbstentionExample


def test_accuracy_and_macro_f1() -> None:
    expected = ["a", "a", "b", "b"]
    predicted = ["a", "b", "b", "b"]
    assert accuracy(expected, predicted) == 0.75
    assert macro_f1(expected, predicted) == pytest.approx((2 / 3 + 0.8) / 2)
    assert confusion_matrix(expected, predicted) == {
        "a": {"a": 1, "b": 1},
        "b": {"a": 0, "b": 2},
    }


def test_recall_at_k_and_mrr_use_first_relevant_rank() -> None:
    metrics = retrieval_metrics(
        [["x", "b", "a"], ["d", "e"], ["z"]],
        [{"a", "b"}, {"f"}, {"z"}],
        cutoffs=(1, 2, 5),
    )
    assert metrics["recall_at_1"] == pytest.approx(1 / 3)
    assert metrics["recall_at_2"] == pytest.approx(2 / 3)
    assert metrics["recall_at_5"] == pytest.approx(2 / 3)
    assert metrics["mrr"] == pytest.approx((1 / 2 + 0 + 1) / 3)


def test_abstention_metrics_count_both_error_directions() -> None:
    metrics = abstention_metrics([False, False, True, True], [True, False, False, True])
    assert metrics == {
        "accuracy": 0.5,
        "false_abstention_count": 1,
        "missed_abstention_count": 1,
    }


def test_malformed_evaluation_records_fail_clearly(tmp_path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"dataset_version": "1", "examples": [{"id": "x"}]}))
    with pytest.raises(EvaluationDatasetError, match="complaint"):
        load_complaint_dataset(path)
    with pytest.raises(EvaluationDatasetError, match="expected_abstained"):
        load_abstention_dataset(path)
    with pytest.raises(EvaluationDatasetError, match="relevant_knowledge_source_ids"):
        load_retrieval_dataset(path)


def test_retrieval_loader_rejects_ids_not_in_the_current_kb(tmp_path) -> None:
    path = tmp_path / "retrieval.json"
    path.write_text(json.dumps({
        "dataset_version": "1",
        "examples": [{
            "id": "r1", "query": "eSIM", "relevant_knowledge_source_ids": ["invented.id"]
        }],
    }))
    with pytest.raises(EvaluationDatasetError, match="unknown KB source IDs"):
        load_retrieval_dataset(path, known_source_ids={"telecom-v1.esim.activation"})


def test_metric_inputs_must_be_non_empty_and_aligned() -> None:
    with pytest.raises(ValueError):
        accuracy(["a"], [])
    with pytest.raises(ValueError):
        macro_f1([], [])
    with pytest.raises(ValueError):
        retrieval_metrics([["a"]], [])
    with pytest.raises(ValueError):
        abstention_metrics([True], [False, True])


def test_committed_curated_datasets_are_well_formed_and_use_real_kb_ids() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    docs = json.loads((root / "knowledge_base/seeds/v1/documents.json").read_text())[
        "documents"
    ]
    source_ids = {document["document_id"] for document in docs}
    complaint_data = load_complaint_dataset(
        root / "evaluation/datasets/complaint_understanding.json"
    )
    retrieval_data = load_retrieval_dataset(
        root / "evaluation/datasets/retrieval.json", known_source_ids=source_ids
    )
    abstention_data = load_abstention_dataset(root / "evaluation/datasets/abstention.json")
    assert len(complaint_data.examples) == 36
    assert len(retrieval_data.examples) == 18
    assert len(abstention_data.examples) == 10
    taxonomy = settings.complaint_taxonomy
    for example in complaint_data.examples:
        assert example.expected_intent in taxonomy.intents
        assert example.expected_category in taxonomy.categories
        assert example.expected_product in taxonomy.products
        assert example.expected_severity in taxonomy.severities
        assert example.expected_sentiment in taxonomy.sentiments


def test_complaint_evaluation_counts_invalid_model_output_instead_of_skipping() -> None:
    dataset = EvaluationDataset("test", (
        ComplaintExample("c1", "Example complaint", "connectivity_issue", "network",
                         "mobile_data", "medium", "frustrated"),
    ))

    class InvalidOutputService:
        def understand(self, _complaint):
            raise ComplaintUnderstandingError("complaint output has unsupported intent")

    result = evaluate_complaints(dataset, InvalidOutputService())
    assert result["example_count"] == 1
    assert result["invalid_model_output_count"] == 1
    assert result["metrics"]["intent_accuracy"] == 0.0
    assert result["examples"][0]["status"] == "invalid_model_output"


def test_complaint_evaluation_aborts_when_provider_is_unavailable() -> None:
    dataset = EvaluationDataset("test", (
        ComplaintExample("c1", "Example complaint", "unknown", "unknown", "unknown",
                         "unknown", "unknown"),
    ))

    class UnavailableService:
        def understand(self, _complaint):
            error = ComplaintUnderstandingError("complaint understanding provider failed")
            error.__cause__ = TimeoutError("offline")
            raise error

    with pytest.raises(RuntimeError, match="could not call the service for c1"):
        evaluate_complaints(dataset, UnavailableService())


def test_abstention_evaluator_reports_invalid_model_output_without_claiming_a_decision() -> None:
    dataset = EvaluationDataset("test", (
        AbstentionExample("a1", "Irrelevant complaint", True),
        AbstentionExample("a2", "Supported complaint", False),
    ))

    class MixedService:
        def resolve(self, complaint):
            if complaint == "Irrelevant complaint":
                raise ComplaintUnderstandingError("complaint output has unsupported product")
            return type("Result", (), {"abstained": False})()

    result = evaluate_abstention(dataset, MixedService())
    assert result["example_count"] == 2
    assert result["successful_response_count"] == 1
    assert result["invalid_model_output_count"] == 1
    assert result["metrics"]["accuracy"] == 1.0
    assert result["examples"][0]["predicted_abstained"] is None
