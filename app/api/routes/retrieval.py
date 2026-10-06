"""Semantic historical-ticket retrieval endpoint."""

from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.semantic_retrieval import (
    MAX_TOP_K,
    InvalidSemanticQuery,
    SemanticRetrievalService,
)
from app.services.hybrid_retrieval import HybridRetrievalService
from app.infrastructure.embeddings.runtime import get_embedding_provider
from app.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.persistence.semantic_ticket_search_repository import (
    SQLAlchemySemanticTicketSearchRepository,
)
from app.infrastructure.persistence.lexical_ticket_search_repository import (
    SQLAlchemyLexicalTicketSearchRepository,
)

router = APIRouter(prefix="/v1/retrieval", tags=["retrieval"])


class SemanticRetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=MAX_TOP_K)


class TicketSourceResponse(BaseModel):
    dataset: str
    split: str
    record_id: str
    revision: str | None


class SemanticTicketResponse(BaseModel):
    ticket_id: int
    subject: str | None
    body: str | None
    answer: str | None
    queue: str | None
    type: str | None
    priority: str | None
    language: str | None
    tags: list[str]
    similarity: float
    source: TicketSourceResponse


class SemanticRetrievalResponseModel(BaseModel):
    query: str
    model: str
    results: list[SemanticTicketResponse]


class HybridTicketResponse(BaseModel):
    ticket_id: int
    subject: str | None
    body: str | None
    answer: str | None
    queue: str | None
    type: str | None
    priority: str | None
    language: str | None
    tags: list[str]
    source: TicketSourceResponse
    fused_score: float
    semantic_rank: int | None
    semantic_score: float | None
    lexical_rank: int | None
    lexical_score: float | None


class HybridRetrievalResponseModel(BaseModel):
    query: str
    model: str
    rrf_constant: int
    semantic_candidate_limit: int
    lexical_candidate_limit: int
    results: list[HybridTicketResponse]


@lru_cache(maxsize=1)
def _get_service() -> SemanticRetrievalService:
    """Load the configured local model and create its database adapter once."""
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be set to use semantic retrieval")
    provider = get_embedding_provider()
    engine = create_database_engine(settings.database_url)
    return SemanticRetrievalService(
        provider,
        SQLAlchemySemanticTicketSearchRepository(create_session_factory(engine)),
        max_top_k=max(MAX_TOP_K, settings.semantic_candidate_limit),
    )


@lru_cache(maxsize=1)
def _get_hybrid_service() -> HybridRetrievalService:
    """Share the semantic provider/service and add the lexical database adapter."""
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be set to use hybrid retrieval")
    lexical_engine = create_database_engine(settings.database_url)
    return HybridRetrievalService(
        semantic_service=_get_service(),
        lexical_repository=SQLAlchemyLexicalTicketSearchRepository(
            create_session_factory(lexical_engine)
        ),
        semantic_candidate_limit=settings.semantic_candidate_limit,
        lexical_candidate_limit=settings.lexical_candidate_limit,
        rrf_constant=settings.rrf_constant,
    )


@router.post("/semantic", response_model=SemanticRetrievalResponseModel)
def semantic_retrieval(
    request: SemanticRetrievalRequest,
) -> SemanticRetrievalResponseModel:
    """Return nearest historical tickets; similarity is not a confidence score."""
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="query must contain non-whitespace text")
    try:
        result = _get_service().retrieve(request.query, top_k=request.top_k)
    except InvalidSemanticQuery as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Semantic retrieval is unavailable") from error
    return SemanticRetrievalResponseModel(
        query=result.query,
        model=result.model_identifier,
        results=[
            SemanticTicketResponse(
                ticket_id=item.ticket_id,
                subject=item.subject,
                body=item.body,
                answer=item.answer,
                queue=item.queue,
                type=item.ticket_type,
                priority=item.priority,
                language=item.language,
                tags=list(item.tags),
                similarity=item.similarity,
                source=TicketSourceResponse(
                    dataset=item.source_dataset,
                    split=item.source_split,
                    record_id=item.source_record_id,
                    revision=item.source_revision,
                ),
            )
            for item in result.results
        ],
    )


@router.post("/hybrid", response_model=HybridRetrievalResponseModel)
def hybrid_retrieval(
    request: SemanticRetrievalRequest,
) -> HybridRetrievalResponseModel:
    """Combine semantic and lexical ticket ranks using Reciprocal Rank Fusion."""
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="query must contain non-whitespace text")
    try:
        result = _get_hybrid_service().retrieve(
            request.query, top_k=request.top_k
        )
    except InvalidSemanticQuery as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Hybrid retrieval is unavailable") from error
    return HybridRetrievalResponseModel(
        query=result.query,
        model=result.model_identifier,
        rrf_constant=settings.rrf_constant,
        semantic_candidate_limit=settings.semantic_candidate_limit,
        lexical_candidate_limit=settings.lexical_candidate_limit,
        results=[
            HybridTicketResponse(
                ticket_id=item.ticket.ticket_id,
                subject=item.ticket.subject,
                body=item.ticket.body,
                answer=item.ticket.answer,
                queue=item.ticket.queue,
                type=item.ticket.ticket_type,
                priority=item.ticket.priority,
                language=item.ticket.language,
                tags=list(item.ticket.tags),
                source=TicketSourceResponse(
                    dataset=item.ticket.source_dataset,
                    split=item.ticket.source_split,
                    record_id=item.ticket.source_record_id,
                    revision=item.ticket.source_revision,
                ),
                fused_score=item.fused_score,
                semantic_rank=item.semantic_rank,
                semantic_score=item.semantic_score,
                lexical_rank=item.lexical_rank,
                lexical_score=item.lexical_score,
            )
            for item in result.results
        ],
    )
