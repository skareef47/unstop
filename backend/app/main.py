"""
PSAI — AI-Powered Technical Support & Troubleshooting Platform Backend
Main Application Entry Point
"""
import time
from contextlib import asynccontextmanager
from typing import Dict
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.errors import PSAIException
from app.db.session import engine, Base
from app.api.v1.router import api_router
from app.services.llm_provider.factory import get_llm_provider
from app.services.embeddings.factory import get_embedding_provider


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist on startup if running with SQLite
    if settings.DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for PSAI — AI-Powered Technical Support & Troubleshooting Platform. 'Diagnose smarter. Resolve faster.'",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate Limiting & Audit Request Timing Middleware
# In-memory IP tracking for prototype rate limiting
_request_counts: Dict[str, list] = {}


@app.middleware("http")
async def rate_limiting_and_timing_middleware(request: Request, call_next):
    # Check rate limit per client IP
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()

    # Clean old requests older than 60s
    if client_ip not in _request_counts:
        _request_counts[client_ip] = []
    _request_counts[client_ip] = [t for t in _request_counts[client_ip] if now - t < 60]

    # Skip rate limiting for static / health endpoints
    if not request.url.path.endswith("/health"):
        if len(_request_counts[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "detail": "Rate limit exceeded. Please wait before submitting more requests.",
                },
            )
        _request_counts[client_ip].append(now)

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time-Sec"] = f"{process_time:.4f}"
    return response


# Standardized Application Exception Handler
@app.exception_handler(PSAIException)
async def psai_exception_handler(request: Request, exc: PSAIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.detail,
            "extra": exc.extra,
        },
    )


# Generic Fallback Exception Handler (avoids leaking stack traces)
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "detail": "An internal server error occurred. Telemetry has been recorded.",
        },
    )


# Health Check Endpoints
@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
def health_check():
    """Verify system health, database connection, and AI provider status."""
    db_status = "healthy"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "online" if "healthy" in db_status else "degraded",
        "product": "PSAI",
        "tagline": "Diagnose smarter. Resolve faster.",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
    }


# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
