"""Idempotent telecom knowledge seed ingestion and separate KB embedding."""

import math
from dataclasses import replace
from collections.abc import Sequence
from pathlib import Path

from app.domain.models import (
    KnowledgeDocumentEmbedding,
    KnowledgeEmbeddingCandidate,
    KnowledgeIngestionResult,
    TelecomKnowledgeDocument,
    telecom_knowledge_content_hash,
)
from app.domain.ports import (
    EmbeddingProvider,
    KnowledgeEmbeddingRepository,
    TelecomKnowledgeRepository,
)
from app.infrastructure.datasets.knowledge_seed_json import load_knowledge_seed

EXPECTED_KNOWLEDGE_DIMENSION = 384


def build_knowledge_embedding_text(document: TelecomKnowledgeDocument) -> str:
    """Embed the guidance and its routing metadata, never historical ticket text."""
    parts = (
        f"Title: {document.title.strip()}",
        f"Category: {document.category}",
        f"Product: {document.product}",
        f"Severity: {document.severity}",
        f"Escalation conditions: {document.escalation_conditions}",
        f"Procedure: {document.content.strip()}",
    )
    if not document.title.strip() or not document.content.strip():
        raise ValueError(f"knowledge document {document.document_id!r} has empty content")
    return "\n".join(parts)


def ingest_knowledge_documents(
    documents: Sequence[TelecomKnowledgeDocument],
    document_repository: TelecomKnowledgeRepository,
    embedding_repository: KnowledgeEmbeddingRepository,
    embedding_provider: EmbeddingProvider,
    *,
    batch_size: int = 64,
) -> KnowledgeIngestionResult:
    """Upsert content, then idempotently embed only new or changed KB documents."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    if embedding_provider.dimension != EXPECTED_KNOWLEDGE_DIMENSION:
        raise ValueError("knowledge embeddings require the configured 384-dimensional model")
    if not documents:
        return KnowledgeIngestionResult()
    for document in documents:
        build_knowledge_embedding_text(document)

    document_result = document_repository.upsert_many(documents)
    embedding_repository.ensure_vector_index(
        embedding_provider.model_identifier, embedding_provider.dimension
    )
    embedded = 0
    reused = 0
    cursor = ""
    while True:
        candidates = embedding_repository.load_batch(
            after_document_id=cursor,
            limit=batch_size,
            model_identifier=embedding_provider.model_identifier,
        )
        if not candidates:
            break
        pending: list[tuple[KnowledgeEmbeddingCandidate, str]] = []
        texts: list[str] = []
        for candidate in candidates:
            cursor = candidate.document.document_id
            current_hash = telecom_knowledge_content_hash(candidate.document)
            if current_hash != candidate.content_hash:
                raise ValueError(
                    f"stored content hash does not match document {candidate.document.document_id}"
                )
            if (
                candidate.existing_content_hash == candidate.content_hash
                and candidate.existing_dimension == embedding_provider.dimension
            ):
                reused += 1
                continue
            pending.append((candidate, candidate.content_hash))
            texts.append(build_knowledge_embedding_text(candidate.document))

        vectors = embedding_provider.embed(texts) if texts else ()
        if len(vectors) != len(pending):
            raise ValueError("embedding provider returned a different number of vectors than inputs")
        rows: list[KnowledgeDocumentEmbedding] = []
        for (candidate, content_hash), raw_vector in zip(pending, vectors, strict=True):
            vector = tuple(float(value) for value in raw_vector)
            if len(vector) != embedding_provider.dimension:
                raise ValueError(
                    f"embedding dimension mismatch for {candidate.document.document_id}: "
                    f"expected {embedding_provider.dimension}, got {len(vector)}"
                )
            if not all(math.isfinite(value) for value in vector):
                raise ValueError("knowledge embedding contains non-finite values")
            rows.append(
                KnowledgeDocumentEmbedding(
                    document_id=candidate.document.document_id,
                    model_identifier=embedding_provider.model_identifier,
                    dimension=embedding_provider.dimension,
                    content_hash=content_hash,
                    vector=vector,
                )
            )
        if rows:
            embedding_repository.upsert_many(rows)
            embedded += len(rows)
        if len(candidates) < batch_size:
            break
    return replace(document_result, embedded=embedded, reused=reused)


def ingest_knowledge_seed(
    seed_path: str | Path,
    document_repository: TelecomKnowledgeRepository,
    embedding_repository: KnowledgeEmbeddingRepository,
    embedding_provider: EmbeddingProvider,
    *,
    batch_size: int = 64,
) -> KnowledgeIngestionResult:
    """Load the committed JSON seed and ingest its documents and vectors."""
    documents = load_knowledge_seed(Path(seed_path))
    return ingest_knowledge_documents(
        documents,
        document_repository,
        embedding_repository,
        embedding_provider,
        batch_size=batch_size,
    )
