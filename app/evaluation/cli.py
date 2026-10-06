"""Run the curated baseline suites using existing application service factories."""

import argparse
import json
import os
from pathlib import Path
from typing import Any

from app.evaluation.abstention import evaluate_abstention
from app.evaluation.complaint_understanding import evaluate_complaints
from app.evaluation.models import (
    EvaluationDatasetError,
    load_abstention_dataset,
    load_complaint_dataset,
    load_retrieval_dataset,
)
from app.evaluation.reporting import build_report, write_reports
from app.evaluation.retrieval import evaluate_retrieval

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "evaluation" / "datasets"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "evaluation" / "reports"
KB_SEED_PATH = PROJECT_ROOT / "knowledge_base" / "seeds" / "v1" / "documents.json"


def _known_knowledge_ids() -> set[str]:
    try:
        source = json.loads(KB_SEED_PATH.read_text(encoding="utf-8"))
        documents = source["documents"]
        ids = {item["document_id"] for item in documents}
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise EvaluationDatasetError(f"cannot validate source IDs against current KB seed: {error}") from error
    if not ids:
        raise EvaluationDatasetError("current KB seed contains no source IDs")
    return ids


def _configuration(settings: Any) -> dict[str, Any]:
    return {
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model or None,
        "llm_base_url": settings.llm_base_url,
        "llm_timeout_seconds": settings.llm_timeout_seconds,
        "embedding_model": settings.embedding_model,
        "embedding_model_revision": settings.embedding_model_revision,
        "embedding_dimension": 384,
        "rrf_constant": settings.rrf_constant,
        "knowledge_semantic_candidate_limit": settings.knowledge_semantic_candidate_limit,
        "knowledge_lexical_candidate_limit": settings.knowledge_lexical_candidate_limit,
        "semantic_candidate_limit": settings.semantic_candidate_limit,
        "lexical_candidate_limit": settings.lexical_candidate_limit,
        "resolution_knowledge_evidence_limit": settings.resolution_knowledge_evidence_limit,
        "resolution_historical_evidence_limit": settings.resolution_historical_evidence_limit,
        "resolution_min_knowledge_similarity": settings.resolution_min_knowledge_similarity,
        "resolution_min_knowledge_lexical_score": settings.resolution_min_knowledge_lexical_score,
        "taxonomy_intents": list(settings.complaint_taxonomy.intents),
        "taxonomy_categories": list(settings.complaint_taxonomy.categories),
        "taxonomy_products": list(settings.complaint_taxonomy.products),
    }


def _load_env_file(path: Path | None) -> None:
    """Load simple KEY=VALUE settings without overriding the shell environment."""
    if path is None or not path.is_file():
        return
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not key or not key.replace("_", "").isalnum():
            raise ValueError(f"invalid environment assignment in {path} at line {line_number}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run curated support-assistant evaluation suites")
    parser.add_argument("--suite", choices=("all", "complaint_understanding", "retrieval", "abstention"), default="all")
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_ROOT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--env-file", type=Path, default=PROJECT_ROOT / ".env")
    args = parser.parse_args()
    selected = (
        {"complaint_understanding", "retrieval", "abstention"}
        if args.suite == "all" else {args.suite}
    )
    try:
        _load_env_file(args.env_file)
        from app.core.config import settings

        complaint_data = load_complaint_dataset(args.dataset_dir / "complaint_understanding.json") if "complaint_understanding" in selected else None
        retrieval_data = load_retrieval_dataset(
            args.dataset_dir / "retrieval.json", known_source_ids=_known_knowledge_ids()
        ) if "retrieval" in selected else None
        abstention_data = load_abstention_dataset(args.dataset_dir / "abstention.json") if "abstention" in selected else None
        suites: dict[str, Any] = {}
        sizes: dict[str, int] = {}
        if complaint_data is not None:
            from app.api.routes.complaints import _get_service

            suites["complaint_understanding"] = evaluate_complaints(complaint_data, _get_service())
            sizes["complaint_understanding"] = len(complaint_data.examples)
        if retrieval_data is not None:
            from app.api.routes.knowledge import _get_service

            suites["retrieval"] = evaluate_retrieval(retrieval_data, _get_service())
            sizes["retrieval"] = len(retrieval_data.examples)
        if abstention_data is not None:
            from app.api.routes.resolutions import _get_resolution_service

            suites["abstention"] = evaluate_abstention(abstention_data, _get_resolution_service())
            sizes["abstention"] = len(abstention_data.examples)
        report = build_report(suites=suites, configuration=_configuration(settings), dataset_sizes=sizes)
        json_path, markdown_path = write_reports(report, args.report_dir)
    except Exception as error:
        parser.exit(2, f"Evaluation failed; no report written: {error}\n")
    print(json.dumps({"status": "complete", "reports": [str(json_path), str(markdown_path)], "dataset_sizes": sizes}, indent=2))


if __name__ == "__main__":
    main()
