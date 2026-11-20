"""
Health-check endpoints.

/health      — application-level (always works, no DB needed)
/health/db   — database-level (executes a real query against MySQL)
"""

from datetime import datetime, timezone

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.database.session import check_db_connection
from app.schemas.health import DatabaseHealthResponse, HealthCheckResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Application Health Check",
    description=(
        "Returns the current operational status, environment, and version of "
        "QueueMind AI.  This endpoint does **not** query the database; it always "
        "responds as long as the application process is running."
    ),
    tags=["Health"],
)
async def check_health() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="healthy",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    summary="Database Health Check",
    description=(
        "Executes a **real** `SELECT 1` query against MySQL to verify the "
        "database is reachable and the connection pool is healthy.  Returns "
        "HTTP 503 when the database is unreachable."
    ),
    tags=["Health"],
)
async def check_db_health() -> JSONResponse:
    result = check_db_connection()
    db_status = "healthy" if result["connected"] else "unhealthy"
    http_status = status.HTTP_200_OK if result["connected"] else status.HTTP_503_SERVICE_UNAVAILABLE

    payload = DatabaseHealthResponse(
        status=db_status,
        database=result,
        timestamp=datetime.now(timezone.utc),
    )
    return JSONResponse(
        content=payload.model_dump(mode="json"),
        status_code=http_status,
    )
