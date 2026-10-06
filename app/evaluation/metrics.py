"""Dependency-free metric calculations for small curated evaluation sets."""

from collections import Counter
from collections.abc import Sequence


def accuracy(expected: Sequence[str | bool], predicted: Sequence[str | bool]) -> float:
    if not expected or len(expected) != len(predicted):
        raise ValueError("accuracy requires equally sized, non-empty sequences")
    return sum(left == right for left, right in zip(expected, predicted, strict=True)) / len(expected)


def macro_f1(expected: Sequence[str], predicted: Sequence[str]) -> float:
    if not expected or len(expected) != len(predicted):
        raise ValueError("macro F1 requires equally sized, non-empty sequences")
    labels = sorted(set(expected))
    scores: list[float] = []
    for label in labels:
        true_positive = sum(a == label and b == label for a, b in zip(expected, predicted, strict=True))
        false_positive = sum(a != label and b == label for a, b in zip(expected, predicted, strict=True))
        false_negative = sum(a == label and b != label for a, b in zip(expected, predicted, strict=True))
        denominator = 2 * true_positive + false_positive + false_negative
        scores.append(2 * true_positive / denominator if denominator else 0.0)
    return sum(scores) / len(scores)


def confusion_matrix(expected: Sequence[str], predicted: Sequence[str]) -> dict[str, dict[str, int]]:
    if not expected or len(expected) != len(predicted):
        raise ValueError("confusion matrix requires equally sized, non-empty sequences")
    labels = sorted(set(expected) | set(predicted))
    counts = Counter(zip(expected, predicted, strict=True))
    return {actual: {guess: counts[(actual, guess)] for guess in labels} for actual in labels}


def retrieval_metrics(
    ranked_source_ids: Sequence[Sequence[str]],
    relevant_source_ids: Sequence[set[str]],
    *,
    cutoffs: Sequence[int] = (5, 10),
) -> dict[str, float]:
    if not ranked_source_ids or len(ranked_source_ids) != len(relevant_source_ids):
        raise ValueError("retrieval metrics require equally sized, non-empty sequences")
    if not cutoffs or any(k < 1 for k in cutoffs):
        raise ValueError("retrieval cutoffs must be positive")
    if any(not relevant for relevant in relevant_source_ids):
        raise ValueError("each retrieval example needs at least one relevant source")
    output: dict[str, float] = {}
    for cutoff in cutoffs:
        hits = [bool(set(ranking[:cutoff]) & relevant) for ranking, relevant in zip(ranked_source_ids, relevant_source_ids, strict=True)]
        output[f"recall_at_{cutoff}"] = sum(hits) / len(hits)
    reciprocal_ranks: list[float] = []
    for ranking, relevant in zip(ranked_source_ids, relevant_source_ids, strict=True):
        reciprocal_ranks.append(
            next((1 / rank for rank, source_id in enumerate(ranking, start=1) if source_id in relevant), 0.0)
        )
    output["mrr"] = sum(reciprocal_ranks) / len(reciprocal_ranks)
    return output


def abstention_metrics(expected: Sequence[bool], predicted: Sequence[bool]) -> dict[str, int | float]:
    if not expected or len(expected) != len(predicted):
        raise ValueError("abstention metrics require equally sized, non-empty sequences")
    false_abstentions = sum(not target and guess for target, guess in zip(expected, predicted, strict=True))
    missed_abstentions = sum(target and not guess for target, guess in zip(expected, predicted, strict=True))
    return {
        "accuracy": accuracy(expected, predicted),
        "false_abstention_count": false_abstentions,
        "missed_abstention_count": missed_abstentions,
    }
