"""Evaluate KB retrieval against manually curated relevant source IDs."""

from collections.abc import Callable
from typing import Any

from app.evaluation.metrics import retrieval_metrics
from app.evaluation.models import EvaluationDataset, RetrievalExample


def evaluate_retrieval(dataset: EvaluationDataset, service: Any) -> dict[str, Any]:
    rankings: list[list[str]] = []
    relevant: list[set[str]] = []
    records: list[dict[str, Any]] = []
    for example in dataset.examples:
        assert isinstance(example, RetrievalExample)
        try:
            response = service.search(example.query, top_k=10)
        except Exception as error:
            raise RuntimeError(f"retrieval evaluation failed for {example.id}: {error}") from error
        ranked_ids = [hit.document.document_id for hit in response.results]
        rankings.append(ranked_ids)
        relevant_ids = set(example.relevant_knowledge_source_ids)
        relevant.append(relevant_ids)
        records.append({
            "id": example.id,
            "relevant_source_ids": sorted(relevant_ids),
            "ranked_source_ids": ranked_ids,
            "first_relevant_rank": next(
                (rank for rank, source_id in enumerate(ranked_ids, 1) if source_id in relevant_ids),
                None,
            ),
        })
    return {
        "dataset_version": dataset.version,
        "example_count": len(dataset.examples),
        "metrics": retrieval_metrics(rankings, relevant, cutoffs=(5, 10)),
        "hit_definition": "A query is a hit at K if at least one expected relevant KB source ID appears in the top K results.",
        "mrr_definition": "Mean reciprocal rank of the first expected relevant source; zero when none is returned.",
        "examples": records,
    }
