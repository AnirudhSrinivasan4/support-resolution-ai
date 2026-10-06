"""Standalone complaint-understanding endpoint."""

from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.infrastructure.llm.runtime import get_llm_provider
from app.services.complaint_understanding import (
    ComplaintUnderstandingError,
    ComplaintUnderstandingService,
)

router = APIRouter(prefix="/v1/complaints", tags=["complaints"])


class ComplaintUnderstandingRequest(BaseModel):
    complaint: str = Field(min_length=1, max_length=4000)


class ComplaintUnderstandingResponse(BaseModel):
    intent: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    category: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    product: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    severity: Literal["low", "medium", "high", "critical", "unknown"]
    sentiment: Literal["positive", "neutral", "frustrated", "angry", "negative", "unknown"]


@lru_cache(maxsize=1)
def _get_service() -> ComplaintUnderstandingService:
    return ComplaintUnderstandingService(get_llm_provider(), settings.complaint_taxonomy)


@router.post("/understand", response_model=ComplaintUnderstandingResponse)
def understand_complaint(
    request: ComplaintUnderstandingRequest,
) -> ComplaintUnderstandingResponse:
    if not request.complaint.strip():
        raise HTTPException(status_code=422, detail="complaint must contain non-whitespace text")
    try:
        result = _get_service().understand(request.complaint)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ComplaintUnderstandingError as error:
        raise HTTPException(status_code=502, detail="Complaint understanding failed validation") from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Complaint understanding is unavailable") from error
    return ComplaintUnderstandingResponse(
        intent=result.intent,
        category=result.category,
        product=result.product,
        severity=result.severity,
        sentiment=result.sentiment,
    )
