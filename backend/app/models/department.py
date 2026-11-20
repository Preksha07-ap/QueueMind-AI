"""
Department model — logical grouping of staff within an organisation.
Examples: IT Department, Examination Department, Accounts Department.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
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
        "Organization", back_populates="departments"
    )
    members: Mapped[list["User"]] = relationship(
        "User",
        back_populates="department",
        foreign_keys="User.department_id",
    )
    support_teams: Mapped[list["SupportTeam"]] = relationship(
        "SupportTeam", back_populates="department"
    )
    issue_categories: Mapped[list["IssueCategory"]] = relationship(
        "IssueCategory", back_populates="department"
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        back_populates="department",
        foreign_keys="Ticket.department_id",
    )

    __table_args__ = (
        Index("uq_departments_org_name", "organization_id", "name", unique=True),
        Index("ix_departments_organization_id", "organization_id"),
        Index("ix_departments_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Department id={self.id} name={self.name!r}>"
