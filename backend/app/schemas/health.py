"""
Health-check response schemas.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Schema for the application health-check endpoint response."""

    status: str = Field(default="healthy", description="Application health status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Current deployment environment")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the check",
    )


class DatabaseHealthDetail(BaseModel):
    """Detail block for the database sub-check."""

    connected: bool = Field(..., description="Whether the database is reachable")
    detail: str = Field(..., description="Human-readable connection message")


class DatabaseHealthResponse(BaseModel):
    """Schema for the database health-check endpoint response."""

    status: str = Field(..., description="'healthy' or 'unhealthy'")
    database: DatabaseHealthDetail
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the check",
    )
