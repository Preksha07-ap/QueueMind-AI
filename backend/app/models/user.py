"""
User model — represents every person who can log in to QueueMind AI.
Roles control access to features.  Passwords are always stored hashed.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum as SAEnum,
    ForeignKey, Index, String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
import enum


class UserRole(str, enum.Enum):
    USER = "USER"
    HELP_DESK = "HELP_DESK"
    SUPPORT_TEAM_MEMBER = "SUPPORT_TEAM_MEMBER"
    SUPPORT_TEAM_LEAD = "SUPPORT_TEAM_LEAD"
    ORGANIZATION_ADMIN = "ORGANIZATION_ADMIN"
    PLATFORM_OWNER = "PLATFORM_OWNER"


class AccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role_enum"),
        nullable=False,
        default=UserRole.USER,
    )
    department_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    support_team_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("support_teams.id", ondelete="SET NULL"), nullable=True
    )
    account_status: Mapped[AccountStatus] = mapped_column(
        SAEnum(AccountStatus, name="account_status_enum"),
        nullable=False,
        default=AccountStatus.ACTIVE,
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── relationships ──────────────────────────────────────────────────────────
    organization: Mapped["Organization | None"] = relationship("Organization", back_populates="users")
    department: Mapped["Department | None"] = relationship("Department", back_populates="members", foreign_keys=[department_id])
    support_team: Mapped["SupportTeam | None"] = relationship("SupportTeam", back_populates="members", foreign_keys=[support_team_id])

    submitted_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        back_populates="submitted_by",
        foreign_keys="Ticket.user_id",
    )
    assigned_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        back_populates="assigned_engineer",
        foreign_keys="Ticket.assigned_engineer_id",
    )
    ticket_history_entries: Mapped[list["TicketHistory"]] = relationship(
        "TicketHistory", back_populates="changed_by", foreign_keys="TicketHistory.changed_by_user_id"
    )
    comments: Mapped[list["TicketComment"]] = relationship(
        "TicketComment", back_populates="author"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="recipient"
    )
    knowledge_base_entries: Mapped[list["KnowledgeBase"]] = relationship(
        "KnowledgeBase", back_populates="created_by_user"
    )

    __table_args__ = (
        # email must be unique within an organisation
        Index("uq_users_org_email", "organization_id", "email", unique=True),
        Index("ix_users_organization_id", "organization_id"),
        Index("ix_users_role", "role"),
        Index("ix_users_account_status", "account_status"),
        Index("ix_users_department_id", "department_id"),
        Index("ix_users_support_team_id", "support_team_id"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
