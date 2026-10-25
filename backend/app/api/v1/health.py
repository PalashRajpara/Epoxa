from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from app.db.session import check_database_health
from app.core.config import settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])

@router.get("/health/live", summary="Liveness probe")
async def health_live():
    """Returns 200 if the FastAPI application process is alive."""
    return {"status": "ok"}

@router.get("/health/ready", response_model=HealthResponse, summary="Readiness probe")
async def health_ready(response: Response):
    """Checks database connectivity safely without exposing credentials."""
    db_healthy = await check_database_health()
    if not db_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ready" if db_healthy else "degraded",
        version="0.1.0",
        environment=settings.APP_ENV,
        database="connected" if db_healthy else "unavailable",
        livekit="configured" if settings.LIVEKIT_URL else "mock",
        deepgram="configured" if settings.DEEPGRAM_API_KEY else "mock",
        groq="configured" if settings.GROQ_API_KEY else "mock",
        timestamp=datetime.now(timezone.utc)
    )
