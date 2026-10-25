import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import EpoxaException
from app.api.v1.health import router as health_router
from app.api.v1.router import api_v1_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Safe startup logging (redacted)
    logger.info("Starting Epoxa Application", **settings.redacted_summary())
    yield
    logger.info("Shutting down Epoxa Application")

app = FastAPI(
    title="Epoxa API",
    description="Production-Grade AI Voice Customer Support Platform API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration from explicit allowlist
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Correlation ID and Request Timing Middleware
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.perf_counter()

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)

    # Log non-health requests
    if not request.url.path.startswith("/health"):
        logger.info(
            "HTTP Request Completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms
        )

    return response

# Standardized Error Handling
@app.exception_handler(EpoxaException)
async def epoxa_exception_handler(request: Request, exc: EpoxaException):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning("Domain exception handled", request_id=request_id, error=exc.message, code=exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "details": exc.details,
                "correlation_id": request_id
            }
        }
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    # Never expose internal stack traces or database URLs to clients
    logger.error("Unhandled server exception", request_id=request_id, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "An unexpected internal server error occurred. Please try again later.",
                "correlation_id": request_id
            }
        }
    )

# Mount Health router at root
app.include_router(health_router)

# Mount API v1 router
app.include_router(api_v1_router)
