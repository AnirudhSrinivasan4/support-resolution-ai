"""Authoritative telecom knowledge-base retrieval endpoint."""

from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.infrastructure.embeddings.runtime import get_embedding_provider
from app.infrastructure.persistence.database import create_database_engine, create_session_factory
from app.infrastructure.persistence.knowledge_document_repository import (
    SQLAlchemyKnowledgeDocumentRepository,
)
from app.infrastructure.persistence.knowledge_embedding_repository import (
    SQLAlchemyKnowledgeEmbeddingRepository,
)
from app.services.knowledge_retrieval import KnowledgeRetrievalService
from app.services.semantic_retrieval import InvalidSemanticQuery, MAX_TOP_K

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=MAX_TOP_K)


class KnowledgeDocumentResponse(BaseModel):
    document_id: str
    title: str
    content: str
    category: str
    product: str
    severity: str
    escalation_conditions: str
    source: str
    version: str
    fused_score: float
    semantic_rank: int | None
    semantic_score: float | None
    lexical_rank: int | None
    lexical_score: float | None


class KnowledgeSearchResponseModel(BaseModel):
    query: str
    model: str
    rrf_constant: int
    semantic_candidate_limit: int
    lexical_candidate_limit: int
    results: list[KnowledgeDocumentResponse]


@lru_cache(maxsize=1)
def _get_service() -> KnowledgeRetrievalService:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be set to use knowledge retrieval")
    engine = create_database_engine(settings.database_url)
    sessions = create_session_factory(engine)
    return KnowledgeRetrievalService(
        get_embedding_provider(),
        SQLAlchemyKnowledgeDocumentRepository(sessions, engine.dialect.name),
        SQLAlchemyKnowledgeEmbeddingRepository(sessions, engine),
        semantic_candidate_limit=settings.knowledge_semantic_candidate_limit,
        lexical_candidate_limit=settings.knowledge_lexical_candidate_limit,
        rrf_constant=settings.rrf_constant,
    )


@router.post("/search", response_model=KnowledgeSearchResponseModel)
def search_knowledge(request: KnowledgeSearchRequest) -> KnowledgeSearchResponseModel:
    """Return separately sourced authoritative KB evidence, without vectors."""
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="query must contain non-whitespace text")
    try:
        result = _get_service().search(request.query, top_k=request.top_k)
    except InvalidSemanticQuery as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Knowledge retrieval is unavailable") from error
    return KnowledgeSearchResponseModel(
        query=result.query,
        model=result.model_identifier,
        rrf_constant=result.rrf_constant,
        semantic_candidate_limit=result.semantic_candidate_limit,
        lexical_candidate_limit=result.lexical_candidate_limit,
        results=[
            KnowledgeDocumentResponse(
                document_id=hit.document.document_id,
                title=hit.document.title,
                content=hit.document.content,
                category=hit.document.category,
                product=hit.document.product,
                severity=hit.document.severity,
                escalation_conditions=hit.document.escalation_conditions,
                source=hit.document.source,
                version=hit.document.version,
                fused_score=hit.fused_score,
                semantic_rank=hit.semantic_rank,
                semantic_score=hit.semantic_score,
                lexical_rank=hit.lexical_rank,
                lexical_score=hit.lexical_score,
            )
            for hit in result.results
        ],
    )
