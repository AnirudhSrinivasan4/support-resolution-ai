"""ASGI application entry point."""

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.complaints import router as complaints_router
from app.api.routes.retrieval import router as retrieval_router
from app.api.routes.resolutions import router as resolutions_router
from app.core.config import settings

app = FastAPI(title=settings.service_name, version=settings.version)
app.include_router(health_router)
app.include_router(retrieval_router)
app.include_router(knowledge_router)
app.include_router(complaints_router)
app.include_router(resolutions_router)
