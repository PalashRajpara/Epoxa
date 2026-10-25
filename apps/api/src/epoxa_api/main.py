"""
Epoxa FastAPI Application Entrypoint.
Implements RFC 7807 Problem Details, CORS allowlist, Security Headers, and Background Workers.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from epoxa_api.background.reconciliation import run_reconciliation_worker
from epoxa_api.background.retention import run_retention_worker
from epoxa_api.routes import (
    admin,
    appointments,
    calls,
    customers,
    health,
    me,
    tickets,
)
from epoxa_api.schemas import ProblemDetails
from epoxa_core.database import check_database_health
from epoxa_core.exceptions import EpoxaException
from epoxa_core.logging import get_logger, setup_logging
from epoxa_core.settings import settings

logger = get_logger("epoxa_api.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan managing background workers and database connectivity."""
    setup_logging(level=settings.LOG_LEVEL, environment=settings.ENVIRONMENT)
    logger.info("Initializing Epoxa API Service", environment=settings.ENVIRONMENT)

    # Health check probe
    db_ok = await check_database_health()
    if not db_ok:
        logger.warning("Database connectivity check failed on startup. Service running in degraded mode.")
    else:
        logger.info("Database connectivity established successfully.")

    # Spawn background workers
    tasks = []
    if settings.ENVIRONMENT != "test":
        tasks.append(asyncio.create_task(run_reconciliation_worker(interval_seconds=30)))
        tasks.append(asyncio.create_task(run_retention_worker(interval_hours=24)))

    yield

    # Clean shutdown
    for task in tasks:
        task.cancel()
    logger.info("Epoxa API Service shutdown complete.")


app = FastAPI(
    title="Voice AI Agent API",
    description="Production-grade API for Voice Agent Call Management, Takeovers, and Support Operations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# MIDDLEWARE: REQUEST-ID & SECURITY HEADERS
# =============================================================================

@app.middleware("http")
async def request_middleware(request: Request, call_next: Callable[[Request], Any]) -> Response:
    """Attaches request correlation ID and security headers."""
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=req_id)

    response: Response = await call_next(request)

    # Security Headers
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self)"

    return response


# =============================================================================
# CORS CONFIGURATION (No Wildcard)
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# =============================================================================
# RFC 7807 EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(EpoxaException)
async def epoxa_exception_handler(request: Request, exc: EpoxaException) -> JSONResponse:
    """Maps domain exceptions to RFC 7807 Problem Details format."""
    req_id = request.headers.get("X-Request-ID")
    problem = ProblemDetails(
        type=f"https://epoxa.ai/errors/{exc.code.lower()}",
        title=exc.message,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url.path),
        request_id=req_id,
        code=exc.code,
        extra=exc.extra,
    )
    return JSONResponse(status_code=exc.status_code, content=problem.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Maps request body/query validation errors to RFC 7807."""
    req_id = request.headers.get("X-Request-ID")
    errors = exc.errors()
    detail = errors[0]["msg"] if errors else "Validation failed."
    problem = ProblemDetails(
        type="https://epoxa.ai/errors/validation-error",
        title="Input Validation Failed",
        status=422,
        detail=detail,
        instance=str(request.url.path),
        request_id=req_id,
        code="VALIDATION_ERROR",
        extra={"validation_errors": errors},
    )
    return JSONResponse(status_code=422, content=problem.model_dump())


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    req_id = request.headers.get("X-Request-ID")
    detail_str = str(exc.detail) if exc.detail else "HTTP Exception"
    problem = ProblemDetails(
        type="https://epoxa.ai/errors/http-error",
        title=detail_str,
        status=exc.status_code,
        detail=detail_str,
        instance=str(request.url.path),
        request_id=req_id,
        code="HTTP_ERROR",
    )
    return JSONResponse(status_code=exc.status_code, content=problem.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Guards against internal trace leaks in 500 errors."""
    req_id = request.headers.get("X-Request-ID")
    logger.error("Unhandled internal server exception", error=str(exc), exc_info=True)
    problem = ProblemDetails(
        type="https://epoxa.ai/errors/internal-server-error",
        title="Internal Server Error",
        status=500,
        detail="An unexpected internal error occurred. Please contact support.",
        instance=str(request.url.path),
        request_id=req_id,
        code="INTERNAL_SERVER_ERROR",
    )
    return JSONResponse(status_code=500, content=problem.model_dump())


# =============================================================================
# ROUTE REGISTRATIONS
# =============================================================================

# Public health probes
app.include_router(health.router)

# Versioned /api/v1 endpoints
api_v1 = FastAPI(title="Epoxa API v1")
api_v1.include_router(calls.router)
api_v1.include_router(customers.router)
api_v1.include_router(appointments.router)
api_v1.include_router(tickets.router)
api_v1.include_router(admin.router)
api_v1.include_router(me.router)

app.mount("/api/v1", api_v1)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("epoxa_api.main:app", host=settings.HOST, port=settings.PORT, reload=True)
