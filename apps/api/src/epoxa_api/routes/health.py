"""
Sanitized health and readiness endpoints for container health checks and uptime monitoring.
"""

from typing import Any, Dict
from fastapi import APIRouter, Response, status

from epoxa_core.database import check_database_health

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def health_live() -> Dict[str, str]:
    """Liveness probe confirming the FastAPI process is running."""
    return {"status": "ok", "service": "epoxa-api"}


@router.get("/ready")
async def health_ready(response: Response) -> Dict[str, Any]:
    """
    Readiness probe validating database connectivity.
    Sanitized output leaks no internal counts, schemas, or credentials.
    """
    db_ok = await check_database_health()

    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "service": "epoxa-api",
            "database": "unavailable",
        }

    return {
        "status": "ready",
        "service": "epoxa-api",
        "database": "connected",
    }
