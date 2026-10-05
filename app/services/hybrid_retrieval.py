"""Reciprocal Rank Fusion for semantic and lexical ticket rankings."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.models import (
    HybridTicketResult,
    LexicalTicketResult,
    SemanticTicketResult,
)
from app.domain.ports import LexicalTicketSearchRepository
from app.services.semantic_retrieval import (
    MAX_TOP_K,
    InvalidSemanticQuery,
    SemanticRetrievalService,
)

DEFAULT_RRF_CONSTANT = 60
MAX_CANDIDATES = 100


@dataclass(frozen=True, slots=True)
class HybridRetrievalResponse:
    query: str
    model_identifier: str
    results: tuple[HybridTicketResult, ...]


def fuse_rankings(
    semantic_results: Sequence[SemanticTicketResult],
    lexical_results: Sequence[LexicalTicketResult],
    *,
    rrf_constant: int = DEFAULT_RRF_CONSTANT,
    limit: int = MAX_TOP_K,
) -> tuple[HybridTicketResult, ...]:
    """Fuse one-based ranks with 1/(constant + rank), never raw-score averaging."""
    if rrf_constant < 1:
        raise ValueError("rrf_constant must be positive")
    if limit < 1:
        raise ValueError("limit must be positive")

    scores: dict[int, float] = {}
    semantic_by_id: dict[int, tuple[int, SemanticTicketResult]] = {}
    lexical_by_id: dict[int, tuple[int, LexicalTicketResult]] = {}
    for rank, result in enumerate(semantic_results, start=1):
        if result.ticket_id not in semantic_by_id:
            semantic_by_id[result.ticket_id] = (rank, result)
            scores[result.ticket_id] = scores.get(result.ticket_id, 0.0) + 1.0 / (
                rrf_constant + rank
            )
    for rank, result in enumerate(lexical_results, start=1):
        if result.ticket_id not in lexical_by_id:
            lexical_by_id[result.ticket_id] = (rank, result)
            scores[result.ticket_id] = scores.get(result.ticket_id, 0.0) + 1.0 / (
                rrf_constant + rank
            )

    fused: list[HybridTicketResult] = []
    for ticket_id, fused_score in scores.items():
        semantic_entry = semantic_by_id.get(ticket_id)
        lexical_entry = lexical_by_id.get(ticket_id)
        chosen_ticket = (
            semantic_entry[1] if semantic_entry is not None else lexical_entry[1]
        )
        fused.append(
            HybridTicketResult(
                ticket=chosen_ticket,
                fused_score=fused_score,
                semantic_rank=semantic_entry[0] if semantic_entry else None,
                semantic_score=semantic_entry[1].similarity if semantic_entry else None,
                lexical_rank=lexical_entry[0] if lexical_entry else None,
                lexical_score=lexical_entry[1].lexical_score if lexical_entry else None,
            )
        )
    fused.sort(
        key=lambda item: (
            -item.fused_score,
            item.semantic_rank if item.semantic_rank is not None else MAX_CANDIDATES + 1,
            item.lexical_rank if item.lexical_rank is not None else MAX_CANDIDATES + 1,
            item.ticket.ticket_id,
        )
    )
    return tuple(fused[:limit])


class HybridRetrievalService:
    """Reuse semantic query embedding, retrieve lexical candidates, and fuse ranks."""

    def __init__(
        self,
        semantic_service: SemanticRetrievalService,
        lexical_repository: LexicalTicketSearchRepository,
        *,
        semantic_candidate_limit: int = MAX_TOP_K,
        lexical_candidate_limit: int = MAX_TOP_K,
        rrf_constant: int = DEFAULT_RRF_CONSTANT,
    ) -> None:
        if not 1 <= semantic_candidate_limit <= MAX_CANDIDATES:
            raise ValueError("semantic_candidate_limit must be between 1 and 100")
        if not 1 <= lexical_candidate_limit <= MAX_CANDIDATES:
            raise ValueError("lexical_candidate_limit must be between 1 and 100")
        if rrf_constant < 1:
            raise ValueError("rrf_constant must be positive")
        self._semantic_service = semantic_service
        self._lexical_repository = lexical_repository
        self._semantic_candidate_limit = semantic_candidate_limit
        self._lexical_candidate_limit = lexical_candidate_limit
        self._rrf_constant = rrf_constant

    def retrieve(self, query: str, *, top_k: int = 5) -> HybridRetrievalResponse:
        normalized_query = query.strip() if isinstance(query, str) else ""
        if not normalized_query:
            raise InvalidSemanticQuery("query must contain non-whitespace text")
        if not 1 <= top_k <= MAX_TOP_K:
            raise InvalidSemanticQuery(f"top_k must be between 1 and {MAX_TOP_K}")
        semantic = self._semantic_service.retrieve(
            normalized_query, top_k=self._semantic_candidate_limit
        )
        lexical = self._lexical_repository.search_by_text(
            query=normalized_query, limit=self._lexical_candidate_limit
        )
        return HybridRetrievalResponse(
            query=normalized_query,
            model_identifier=semantic.model_identifier,
            results=fuse_rankings(
                semantic.results,
                lexical,
                rrf_constant=self._rrf_constant,
                limit=top_k,
            ),
        )
