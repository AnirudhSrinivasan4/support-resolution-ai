"""Semantic historical-ticket retrieval endpoint."""

from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.semantic_retrieval import (
    EXPECTED_EMBEDDING_DIMENSION,
    MAX_TOP_K,
    InvalidSemanticQuery,
    SemanticRetrievalService,
)
from app.infrastructure.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)
from app.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.persistence.semantic_ticket_search_repository import (
    SQLAlchemySemanticTicketSearchRepository,
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


@lru_cache(maxsize=1)
def _get_service() -> SemanticRetrievalService:
    """Load the configured local model and create its database adapter once."""
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be set to use semantic retrieval")
    provider = SentenceTransformerEmbeddingProvider(
        settings.embedding_model,
        revision=settings.embedding_model_revision,
        batch_size=settings.embedding_batch_size,
    )
    if provider.dimension != EXPECTED_EMBEDDING_DIMENSION:
        raise RuntimeError("configured retrieval model must output 384 dimensions")
    engine = create_database_engine(settings.database_url)
    return SemanticRetrievalService(
        provider,
        SQLAlchemySemanticTicketSearchRepository(create_session_factory(engine)),
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
