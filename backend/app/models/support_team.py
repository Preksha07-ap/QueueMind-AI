"""
SupportTeam model — a team within a department that handles specific types of issues.
Examples: Network Support, Fee Support, Examination Support, Hardware Support.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class SupportTeam(Base):
    __tablename__ = "support_teams"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    department_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── relationships ──────────────────────────────────────────────────────────
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="support_teams"
    )
    department: Mapped["Department"] = relationship(
        "Department", back_populates="support_teams"
    )
    issue_categories: Mapped[list["IssueCategory"]] = relationship(
        "IssueCategory", back_populates="support_team"
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        back_populates="support_team",
        foreign_keys="Ticket.support_team_id",
    )
    members: Mapped[list["User"]] = relationship(
        "User",
        back_populates="support_team",
        foreign_keys="User.support_team_id",
    )

    __table_args__ = (
        Index("uq_support_teams_org_name", "organization_id", "name", unique=True),
        Index("ix_support_teams_organization_id", "organization_id"),
        Index("ix_support_teams_department_id", "department_id"),
        Index("ix_support_teams_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<SupportTeam id={self.id} name={self.name!r}>"
