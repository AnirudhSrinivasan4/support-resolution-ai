"""Batch orchestration for reusable historical ticket embeddings."""

import hashlib
import json
import logging
import math
from collections.abc import Sequence

from app.domain.models import (
    EmbeddingBatchResult,
    TicketEmbedding,
    TicketEmbeddingCandidate,
)
from app.domain.ports import EmbeddingProvider, TicketEmbeddingRepository

logger = logging.getLogger(__name__)


def build_embedding_text(subject: str | None, body: str | None) -> str | None:
    """Build a compact model input; historical answers are intentionally excluded."""
    parts: list[str] = []
    if subject and subject.strip():
        parts.append(f"Subject: {subject.strip()}")
    if body and body.strip():
        parts.append(f"Body: {body.strip()}")
    return "\n".join(parts) or None


def source_text_hash(subject: str | None, body: str | None) -> str:
    """Hash the exact stored subject/body values for change detection."""
    encoded = json.dumps(
        [subject, body], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def embed_historical_tickets(
    repository: TicketEmbeddingRepository,
    provider: EmbeddingProvider,
    *,
    batch_size: int = 64,
) -> EmbeddingBatchResult:
    """Page, embed, and commit bounded batches; safe to resume after interruption."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    if provider.dimension < 1:
        raise ValueError("embedding provider dimension must be positive")

    repository.ensure_vector_index(provider.model_identifier, provider.dimension)
    totals = EmbeddingBatchResult()
    cursor = 0
    while True:
        candidates = repository.load_batch(
            after_ticket_id=cursor,
            limit=batch_size,
            model_identifier=provider.model_identifier,
        )
        if not candidates:
            break

        texts: list[str] = []
        pending: list[tuple[TicketEmbeddingCandidate, str]] = []
        empty_ticket_ids: list[int] = []
        skipped_no_text = 0
        reused = 0
        for candidate in candidates:
            cursor = candidate.ticket_id
            text = build_embedding_text(candidate.subject, candidate.body)
            if text is None:
                skipped_no_text += 1
                if candidate.existing_source_text_hash is not None:
                    empty_ticket_ids.append(candidate.ticket_id)
                continue
            digest = source_text_hash(candidate.subject, candidate.body)
            if (
                candidate.existing_source_text_hash == digest
                and candidate.existing_dimension == provider.dimension
            ):
                reused += 1
                continue
            texts.append(text)
            pending.append((candidate, digest))

        if empty_ticket_ids:
            repository.delete_for_tickets(empty_ticket_ids, provider.model_identifier)

        vectors = provider.embed(texts) if texts else ()
        if len(vectors) != len(pending):
            raise ValueError(
                "embedding provider returned a different number of vectors than inputs"
            )

        rows: list[TicketEmbedding] = []
        for (candidate, digest), raw_vector in zip(pending, vectors, strict=True):
            vector = tuple(float(value) for value in raw_vector)
            if len(vector) != provider.dimension:
                raise ValueError(
                    f"embedding dimension mismatch for ticket {candidate.ticket_id}: "
                    f"expected {provider.dimension}, got {len(vector)}"
                )
            if not all(math.isfinite(value) for value in vector):
                raise ValueError(
                    f"embedding contains non-finite values for ticket {candidate.ticket_id}"
                )
            rows.append(
                TicketEmbedding(
                    ticket_id=candidate.ticket_id,
                    model_identifier=provider.model_identifier,
                    dimension=provider.dimension,
                    source_text_hash=digest,
                    vector=vector,
                )
            )
        if rows:
            repository.upsert_many(rows)

        current = EmbeddingBatchResult(
            processed=len(candidates),
            embedded=len(rows),
            reused=reused,
            skipped_no_text=skipped_no_text,
        )
        totals += current
        if totals.processed % (batch_size * 20) == 0 or len(candidates) < batch_size:
            logger.info(
                "ticket_embedding_progress model=%s processed=%d embedded=%d "
                "reused=%d skipped_no_text=%d last_ticket_id=%d",
                provider.model_identifier,
                totals.processed,
                totals.embedded,
                totals.reused,
                totals.skipped_no_text,
                cursor,
            )
    return totals
