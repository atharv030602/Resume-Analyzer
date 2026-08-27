from fastapi import APIRouter

from app.config import settings
from app.database import db_ready
from app.schemas import HealthResponse
from app.services.vectorstore import get_vector_store

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
@router.get("/api/v2/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.environment,
        ai_enabled=settings.ai_enabled,
        llm_provider=settings.llm_provider,
        vector_backend=get_vector_store().backend,
        db_connected=db_ready(),
    )
