"""
Ticket model — the central entity of QueueMind AI.

The department_id, support_team_id, and assigned_engineer_id are intentionally
nullable on creation.  The Help Desk reviews the AI recommendation before
confirming routing.  Priority is set by AI first, then confirmed by Help Desk.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum as SAEnum,
    Float, ForeignKey, Index, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
import enum


class TicketSource(str, enum.Enum):
    WEB = "WEB"
    EMAIL = "EMAIL"
    CHAT = "CHAT"
    PHONE = "PHONE"


class TicketPriority(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TicketStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    AI_ANALYSIS = "AI_ANALYSIS"
    AWAITING_HELP_DESK_REVIEW = "AWAITING_HELP_DESK_REVIEW"
    APPROVED_FOR_ROUTING = "APPROVED_FOR_ROUTING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    # Human-readable reference unique per organisation, e.g. "TKT-00001"
    ticket_number: Mapped[str] = mapped_column(String(50), nullable=False)

    # Who raised the ticket
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("issue_categories.id", ondelete="SET NULL"), nullable=True
    )
    subcategory: Mapped[str | None] = mapped_column(String(255), nullable=True)
    impact: Mapped[str | None] = mapped_column(String(50), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(50), nullable=True)

    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[TicketSource] = mapped_column(
        SAEnum(TicketSource, name="ticket_source_enum"),
        nullable=False,
        default=TicketSource.WEB,
    )

    # ── AI analysis fields ─────────────────────────────────────────────────────
    ai_predicted_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_predicted_priority: Mapped[TicketPriority | None] = mapped_column(
        SAEnum(TicketPriority, name="ticket_priority_enum"),
        nullable=True,
    )
    ai_priority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_priority_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_recommended_department_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    ai_recommended_support_team_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("support_teams.id", ondelete="SET NULL"), nullable=True
    )
    ai_duplicate_ticket_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True
    )
    ai_duplicate_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_analysis_status: Mapped[str | None] = mapped_column(String(50), nullable=True, default="PENDING")
    ai_evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Historical Incident & Outage Grouping ─────────────────────────────────
    related_incident_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True
    )
    # Phase 6: cluster membership
    incident_cluster_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("incident_clusters.id", ondelete="SET NULL"), nullable=True
    )
    verified_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_resolution_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Help Desk confirmed fields ─────────────────────────────────────────────
    confirmed_priority: Mapped[TicketPriority | None] = mapped_column(
        SAEnum(TicketPriority, name="confirmed_priority_enum"),
        nullable=True,
    )

    # ── Routing (nullable until Help Desk confirms) ───────────────────────────
    department_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    support_team_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("support_teams.id", ondelete="SET NULL"), nullable=True
    )
    assigned_engineer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Status & timestamps ───────────────────────────────────────────────────
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status_enum"),
        nullable=False,
        default=TicketStatus.SUBMITTED,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── relationships ──────────────────────────────────────────────────────────
    organization: Mapped["Organization"] = relationship("Organization", back_populates="tickets")
    submitted_by: Mapped["User"] = relationship(
        "User", back_populates="submitted_tickets", foreign_keys=[user_id]
    )
    assigned_engineer: Mapped["User | None"] = relationship(
        "User", back_populates="assigned_tickets", foreign_keys=[assigned_engineer_id]
    )
    category: Mapped["IssueCategory | None"] = relationship("IssueCategory", back_populates="tickets")
    department: Mapped["Department | None"] = relationship(
        "Department", back_populates="tickets", foreign_keys=[department_id]
    )
    support_team: Mapped["SupportTeam | None"] = relationship(
        "SupportTeam", back_populates="tickets", foreign_keys=[support_team_id]
    )
    ai_recommended_department: Mapped["Department | None"] = relationship(
        "Department", foreign_keys=[ai_recommended_department_id]
    )
    ai_recommended_support_team: Mapped["SupportTeam | None"] = relationship(
        "SupportTeam", foreign_keys=[ai_recommended_support_team_id]
    )
    history: Mapped[list["TicketHistory"]] = relationship(
        "TicketHistory",
        back_populates="ticket",
        cascade="all, delete-orphan",  # history is owned by ticket
    )
    comments: Mapped[list["TicketComment"]] = relationship(
        "TicketComment",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="ticket"
    )
    attachments: Mapped[list["TicketAttachment"]] = relationship(
        "TicketAttachment",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Ticket number is unique within an organisation
        UniqueConstraint("organization_id", "ticket_number", name="uq_tickets_org_number"),
        Index("ix_tickets_organization_id", "organization_id"),
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_confirmed_priority", "confirmed_priority"),
        Index("ix_tickets_ai_predicted_priority", "ai_predicted_priority"),
        Index("ix_tickets_department_id", "department_id"),
        Index("ix_tickets_support_team_id", "support_team_id"),
        Index("ix_tickets_assigned_engineer_id", "assigned_engineer_id"),
        Index("ix_tickets_user_id", "user_id"),
        Index("ix_tickets_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} number={self.ticket_number!r} status={self.status}>"
