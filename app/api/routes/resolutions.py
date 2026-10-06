"""Thin HTTP boundary for grounded support resolution requests."""

from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.routes.complaints import ComplaintUnderstandingResponse
from app.api.routes.knowledge import _get_service as get_knowledge_retriever
from app.api.routes.retrieval import _get_hybrid_service as get_historical_retriever
from app.core.config import settings
from app.domain.ports import LLMProvider
from app.infrastructure.llm.runtime import get_llm_provider
from app.services.complaint_understanding import (
    ComplaintUnderstandingError,
    ComplaintUnderstandingService,
)
from app.services.resolution import (
    InvalidResolutionRequest,
    ResolutionGenerationError,
    ResolutionService,
)

router = APIRouter(prefix="/v1/resolutions", tags=["resolutions"])


class ResolutionRequest(BaseModel):
    complaint: str = Field(min_length=1, max_length=4000)


class ResolutionCitationResponse(BaseModel):
    source_type: Literal["knowledge", "historical_ticket"]
    source_id: str
    title: str


class ResolutionResponse(BaseModel):
    complaint_understanding: ComplaintUnderstandingResponse
    resolution: str
    steps: list[str]
    escalation: str
    citations: list[ResolutionCitationResponse]
    abstained: bool


@lru_cache(maxsize=1)
def _get_resolution_service() -> ResolutionService:
    provider: LLMProvider = get_llm_provider()
    return ResolutionService(
        knowledge_retriever=get_knowledge_retriever(),
        historical_retriever=get_historical_retriever(),
        complaint_analyzer=ComplaintUnderstandingService(
            provider, settings.complaint_taxonomy
        ),
        llm_provider=provider,
        knowledge_limit=settings.resolution_knowledge_evidence_limit,
        historical_limit=settings.resolution_historical_evidence_limit,
        minimum_knowledge_similarity=settings.resolution_min_knowledge_similarity,
        minimum_knowledge_lexical_score=settings.resolution_min_knowledge_lexical_score,
    )


@router.post("", response_model=ResolutionResponse)
def create_resolution(request: ResolutionRequest) -> ResolutionResponse:
    """Retrieve evidence, draft a cited resolution, and validate its citations."""
    if not request.complaint.strip():
        raise HTTPException(status_code=422, detail="complaint must contain non-whitespace text")
    try:
        result = _get_resolution_service().resolve(request.complaint)
    except InvalidResolutionRequest as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ComplaintUnderstandingError as error:
        raise HTTPException(status_code=502, detail="Complaint understanding failed validation") from error
    except ResolutionGenerationError as error:
        raise HTTPException(status_code=502, detail="Resolution generation failed validation") from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Resolution service is unavailable") from error
    return ResolutionResponse(
        complaint_understanding=ComplaintUnderstandingResponse(
            intent=result.complaint_understanding.intent,
            category=result.complaint_understanding.category,
            product=result.complaint_understanding.product,
            severity=result.complaint_understanding.severity,
            sentiment=result.complaint_understanding.sentiment,
        ),
        resolution=result.resolution,
        steps=[step.instruction for step in result.steps],
        escalation=result.escalation,
        citations=[
            ResolutionCitationResponse(
                source_type=citation.source_type,
                source_id=citation.source_id,
                title=citation.title,
            )
            for citation in result.citations
        ],
        abstained=result.abstained,
    )
