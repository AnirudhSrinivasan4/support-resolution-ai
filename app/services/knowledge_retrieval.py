"""Semantic and lexical retrieval over the separate telecom knowledge base."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.models import (
    KnowledgeLexicalHit,
    KnowledgeSearchHit,
    KnowledgeSemanticHit,
    TelecomKnowledgeDocument,
)
from app.domain.ports import EmbeddingProvider, KnowledgeEmbeddingRepository, TelecomKnowledgeRepository
from app.services.semantic_retrieval import InvalidSemanticQuery, MAX_TOP_K

EXPECTED_DIMENSION = 384
MAX_CANDIDATES = 100


@dataclass(frozen=True, slots=True)
class KnowledgeSearchResponse:
    query: str
    model_identifier: str
    rrf_constant: int
    semantic_candidate_limit: int
    lexical_candidate_limit: int
    results: tuple[KnowledgeSearchHit, ...]


def fuse_knowledge_rankings(
    semantic_hits: Sequence[KnowledgeSemanticHit],
    lexical_hits: Sequence[KnowledgeLexicalHit],
    *,
    rrf_constant: int,
    limit: int,
) -> tuple[KnowledgeSearchHit, ...]:
    """Fuse KB rankings by document ID using one-based Reciprocal Rank Fusion."""
    if rrf_constant < 1 or limit < 1:
        raise ValueError("RRF constant and result limit must be positive")
    semantic_by_id: dict[str, tuple[int, KnowledgeSemanticHit]] = {}
    lexical_by_id: dict[str, tuple[int, KnowledgeLexicalHit]] = {}
    scores: dict[str, float] = {}
    for rank, hit in enumerate(semantic_hits, start=1):
        document_id = hit.document.document_id
        if document_id not in semantic_by_id:
            semantic_by_id[document_id] = (rank, hit)
            scores[document_id] = scores.get(document_id, 0.0) + 1 / (rrf_constant + rank)
    for rank, hit in enumerate(lexical_hits, start=1):
        document_id = hit.document.document_id
        if document_id not in lexical_by_id:
            lexical_by_id[document_id] = (rank, hit)
            scores[document_id] = scores.get(document_id, 0.0) + 1 / (rrf_constant + rank)

    results: list[KnowledgeSearchHit] = []
    for document_id, fused_score in scores.items():
        semantic_entry = semantic_by_id.get(document_id)
        lexical_entry = lexical_by_id.get(document_id)
        document: TelecomKnowledgeDocument = (
            semantic_entry[1].document if semantic_entry else lexical_entry[1].document
        )
        results.append(
            KnowledgeSearchHit(
                document=document,
                fused_score=fused_score,
                semantic_rank=semantic_entry[0] if semantic_entry else None,
                semantic_score=semantic_entry[1].similarity if semantic_entry else None,
                lexical_rank=lexical_entry[0] if lexical_entry else None,
                lexical_score=lexical_entry[1].lexical_score if lexical_entry else None,
            )
        )
    results.sort(
        key=lambda result: (
            -result.fused_score,
            result.semantic_rank if result.semantic_rank is not None else MAX_CANDIDATES + 1,
            result.lexical_rank if result.lexical_rank is not None else MAX_CANDIDATES + 1,
            result.document.document_id,
        )
    )
    return tuple(results[:limit])


class KnowledgeRetrievalService:
    """Embed once, search isolated KB vector and lexical indexes, and fuse ranks."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        document_repository: TelecomKnowledgeRepository,
        embedding_repository: KnowledgeEmbeddingRepository,
        *,
        semantic_candidate_limit: int = 20,
        lexical_candidate_limit: int = 20,
        rrf_constant: int = 60,
    ) -> None:
        if embedding_provider.dimension != EXPECTED_DIMENSION:
            raise ValueError("knowledge retrieval requires 384-dimensional embeddings")
        if not 1 <= semantic_candidate_limit <= MAX_CANDIDATES:
            raise ValueError("semantic_candidate_limit must be between 1 and 100")
        if not 1 <= lexical_candidate_limit <= MAX_CANDIDATES:
            raise ValueError("lexical_candidate_limit must be between 1 and 100")
        if rrf_constant < 1:
            raise ValueError("rrf_constant must be positive")
        self._provider = embedding_provider
        self._document_repository = document_repository
        self._embedding_repository = embedding_repository
        self._semantic_candidate_limit = semantic_candidate_limit
        self._lexical_candidate_limit = lexical_candidate_limit
        self._rrf_constant = rrf_constant

    def search(self, query: str, *, top_k: int = 5) -> KnowledgeSearchResponse:
        normalized_query = query.strip() if isinstance(query, str) else ""
        if not normalized_query:
            raise InvalidSemanticQuery("query must contain non-whitespace text")
        if not 1 <= top_k <= MAX_TOP_K:
            raise InvalidSemanticQuery(f"top_k must be between 1 and {MAX_TOP_K}")
        vectors = self._provider.embed([normalized_query])
        if len(vectors) != 1 or len(vectors[0]) != EXPECTED_DIMENSION:
            raise RuntimeError("embedding provider returned an invalid KB query vector")
        semantic_hits = self._embedding_repository.search_by_embedding(
            embedding=vectors[0],
            model_identifier=self._provider.model_identifier,
            dimension=EXPECTED_DIMENSION,
            limit=self._semantic_candidate_limit,
        )
        lexical_hits = self._document_repository.search_by_text(
            query=normalized_query,
            limit=self._lexical_candidate_limit,
        )
        return KnowledgeSearchResponse(
            query=normalized_query,
            model_identifier=self._provider.model_identifier,
            rrf_constant=self._rrf_constant,
            semantic_candidate_limit=self._semantic_candidate_limit,
            lexical_candidate_limit=self._lexical_candidate_limit,
            results=fuse_knowledge_rankings(
                semantic_hits,
                lexical_hits,
                rrf_constant=self._rrf_constant,
                limit=top_k,
            ),
        )
