"""
IncidentCluster model for QueueMind AI — Phase 6.

Groups semantically similar tickets from the same organisation into an incident cluster.
Preserves ALL original tickets — this model only tracks the grouping.
Strictly tenant-isolated: organisation_id is non-nullable and all queries filter by it.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class IncidentCluster(Base):
    __tablename__ = "incident_clusters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Tenant isolation — mandatory
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )

    # Representative / primary ticket for this cluster
    primary_ticket_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True
    )

    # Human-readable cluster reference, e.g. "INC-00001"
    cluster_number: Mapped[str] = mapped_column(String(50), nullable=False)

    # AI-generated summary of the common issue
    common_issue_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Category that best describes the cluster
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Current escalated priority of the cluster (highest of member tickets)
    incident_priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")

    # Cluster lifecycle status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="OPEN")
    # Values: OPEN, INVESTIGATING, RESOLVED, CLOSED

    # Ticket IDs in this cluster (JSON list stored as text)
    related_ticket_ids_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Distinct affected users (not total reports — one user submitting 3 tickets counts as 1)
    distinct_affected_users: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Total number of tickets (reports) in this cluster
    total_reports: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Similarity score of the best semantic match that triggered grouping
    similarity_score: Mapped[float | None] = mapped_column(nullable=True)

    # Verified resolution (populated when cluster resolved)
    verified_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    first_reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Escalation metadata — why priority was escalated
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Whether this cluster has been confirmed by Help Desk (vs auto-generated)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")  # type: ignore[name-defined]
    primary_ticket: Mapped["Ticket | None"] = relationship("Ticket", foreign_keys=[primary_ticket_id])  # type: ignore[name-defined]

    __table_args__ = (
        Index("ix_incident_clusters_organization_id", "organization_id"),
        Index("ix_incident_clusters_status", "status"),
        Index("ix_incident_clusters_incident_priority", "incident_priority"),
        Index("ix_incident_clusters_first_reported_at", "first_reported_at"),
    )

    def __repr__(self) -> str:
        return f"<IncidentCluster id={self.id} number={self.cluster_number!r} priority={self.incident_priority}>"
