"""
Organization model — top-level multi-tenant entity.
Every organization-specific record references this model's PK.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum as SAEnum,
    Index, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
import enum


class OrganizationType(str, enum.Enum):
    UNIVERSITY = "UNIVERSITY"
    COLLEGE = "COLLEGE"
    SCHOOL = "SCHOOL"
    ENTERPRISE = "ENTERPRISE"
    OTHER = "OTHER"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    org_type: Mapped[OrganizationType] = mapped_column(
        SAEnum(OrganizationType, name="org_type_enum"),
        nullable=False,
        default=OrganizationType.OTHER,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── relationships ──────────────────────────────────────────────────────────
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="organization", cascade="all, delete-orphan"
    )
    departments: Mapped[list["Department"]] = relationship(
        "Department", back_populates="organization", cascade="all, delete-orphan"
    )
    support_teams: Mapped[list["SupportTeam"]] = relationship(
        "SupportTeam", back_populates="organization", cascade="all, delete-orphan"
    )
    issue_categories: Mapped[list["IssueCategory"]] = relationship(
        "IssueCategory", back_populates="organization", cascade="all, delete-orphan"
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="organization"
    )
    ticket_history: Mapped[list["TicketHistory"]] = relationship(
        "TicketHistory", back_populates="organization"
    )
    ticket_comments: Mapped[list["TicketComment"]] = relationship(
        "TicketComment", back_populates="organization"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="organization"
    )
    knowledge_base: Mapped[list["KnowledgeBase"]] = relationship(
        "KnowledgeBase", back_populates="organization"
    )

    __table_args__ = (
        Index("ix_organizations_is_active", "is_active"),
        Index("ix_organizations_contact_email", "contact_email"),
        Index("ix_organizations_code", "code"),
        Index("ix_organizations_slug", "slug"),
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} name={self.name!r}>"
