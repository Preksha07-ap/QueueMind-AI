"""
IssueCategory model — configurable by organisation admins.
Maps categories to departments and support teams so the AI can suggest routing.

Examples:
  - Internet/Network Issue  → IT Department → Network Support
  - Examination Portal Issue → Examination Dept → Examination Support
  - Admission/Examination Fee Issue → Accounts Dept → Fee Support
  - Hardware Issue → IT Department → Hardware Support
  - Login/Account Issue → IT Department → Network Support
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class IssueCategory(Base):
    __tablename__ = "issue_categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Nullable: admin maps category after creation
    department_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    support_team_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("support_teams.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── relationships ──────────────────────────────────────────────────────────
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="issue_categories"
    )
    department: Mapped["Department | None"] = relationship(
        "Department", back_populates="issue_categories"
    )
    support_team: Mapped["SupportTeam | None"] = relationship(
        "SupportTeam", back_populates="issue_categories"
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="category"
    )
    knowledge_base: Mapped[list["KnowledgeBase"]] = relationship(
        "KnowledgeBase", back_populates="category"
    )

    __table_args__ = (
        Index("uq_issue_categories_org_name", "organization_id", "name", unique=True),
        Index("ix_issue_categories_organization_id", "organization_id"),
        Index("ix_issue_categories_department_id", "department_id"),
        Index("ix_issue_categories_support_team_id", "support_team_id"),
        Index("ix_issue_categories_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<IssueCategory id={self.id} name={self.name!r}>"
