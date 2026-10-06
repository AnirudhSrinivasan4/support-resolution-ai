"""Loader for the committed, versioned synthetic telecom knowledge seed."""

import json
from pathlib import Path
from typing import Any

from app.domain.models import TelecomKnowledgeDocument

REQUIRED_FIELDS = (
    "document_id",
    "title",
    "content",
    "category",
    "product",
    "severity",
    "escalation_conditions",
    "source",
    "version",
)


def load_knowledge_seed(path: Path) -> tuple[TelecomKnowledgeDocument, ...]:
    """Load and validate a JSON seed without downloading or inferring anything."""
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read knowledge seed at {path}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("documents"), list):
        raise ValueError("knowledge seed must be an object containing a documents list")
    if payload.get("schema_version") != "1.0":
        raise ValueError("unsupported knowledge seed schema_version")

    documents: list[TelecomKnowledgeDocument] = []
    seen_ids: set[str] = set()
    for index, raw_document in enumerate(payload["documents"]):
        if not isinstance(raw_document, dict):
            raise ValueError(f"document at index {index} must be an object")
        missing = [field for field in REQUIRED_FIELDS if field not in raw_document]
        if missing:
            raise ValueError(
                f"document at index {index} is missing required fields: {', '.join(missing)}"
            )
        values = {field: raw_document[field] for field in REQUIRED_FIELDS}
        if any(not isinstance(value, str) for value in values.values()):
            raise ValueError(f"all document fields at index {index} must be strings")
        for field in ("document_id", "title", "content", "category", "product", "source", "version"):
            if not values[field].strip():
                raise ValueError(f"document at index {index} has empty {field}")
        document_id = values["document_id"]
        if document_id in seen_ids:
            raise ValueError(f"duplicate document_id in seed: {document_id}")
        seen_ids.add(document_id)
        documents.append(TelecomKnowledgeDocument(**values))
    if not documents:
        raise ValueError("knowledge seed must contain at least one document")
    return tuple(documents)
