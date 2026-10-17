"""main.py — Application entry point.

Run with:
    uvicorn main:app --reload
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.helpers.config import get_settings
from src.helpers.database import check_db_connectivity
from src.helpers.exceptions import AppError
from src.helpers.logging import configure_logging
from src.helpers.response import error_response
from src.routes.export_routes import router as export_router
from src.routes.weather_routes import router as weather_router

# ---------------------------------------------------------------------------
# Bootstrap logging before anything else
# ---------------------------------------------------------------------------
settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_name,
    description=(
        "A fully-featured Weather Backend demonstrating REST API development, "
        "MVC architecture, external API integration (Open-Meteo), PostgreSQL "
        "persistence, CRUD operations, and automated testing.\n\n"
        "Built for the **PM Accelerator AI Engineer Intern** technical assessment."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "AppError [%s] %s %s: %s",
        exc.code,
        request.method,
        request.url.path,
        exc.message,
    )
    return JSONResponse(
        status_code=exc.http_status,
        content=error_response(exc.code, exc.message),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Flatten Pydantic errors into a human-readable string
    details = "; ".join(
        f"{' -> '.join(str(loc) for loc in e['loc'])}: {e['msg']}"
        for e in exc.errors()
    )
    logger.info("Validation error %s %s: %s", request.method, request.url.path, details)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response("VALIDATION_ERROR", details),
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please try again later.",
        ),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
API_PREFIX = "/api/v1"
app.include_router(weather_router, prefix=API_PREFIX)
app.include_router(export_router, prefix=API_PREFIX)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Health"], summary="Basic liveness check")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/ready", tags=["Health"], summary="Readiness check (includes DB)")
async def readiness() -> JSONResponse:
    db_ok = await check_db_connectivity()
    if not db_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "database": "unreachable",
                "service": settings.app_name,
            },
        )
    return JSONResponse(
        content={"status": "ready", "database": "ok", "service": settings.app_name}
    )
