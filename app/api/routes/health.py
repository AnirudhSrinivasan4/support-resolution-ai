"""Health endpoint for container and service checks."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz", tags=["health"])
def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}
