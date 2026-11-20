"""
KnowledgeBase model — repository of approved problem/solution pairs.
Will be used for RAG-assisted AI response generation in later phases.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum as SAEnum,
    ForeignKey, Index, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
import enum


class KBApprovalStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    solution: Mapped[str] = mapped_column(Text, nullable=False)
    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    possible_causes: Mapped[str | None] = mapped_column(Text, nullable=True)
    troubleshooting_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), default="MANUAL_KB", nullable=True)
    source_ticket_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True
    )
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), default="1.0", nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("issue_categories.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approval_status: Mapped[KBApprovalStatus] = mapped_column(
        SAEnum(KBApprovalStatus, name="kb_approval_status_enum"),
        nullable=False,
        default=KBApprovalStatus.DRAFT,
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

    # ── relationships ──────────────────────────────────────────────────────────
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="knowledge_base"
    )
    category: Mapped["IssueCategory | None"] = relationship(
        "IssueCategory", back_populates="knowledge_base"
    )
    created_by_user: Mapped["User | None"] = relationship(
        "User", back_populates="knowledge_base_entries"
    )

    __table_args__ = (
        Index("ix_knowledge_base_organization_id", "organization_id"),
        Index("ix_knowledge_base_category_id", "category_id"),
        Index("ix_knowledge_base_approval_status", "approval_status"),
        Index("ix_knowledge_base_created_by_user_id", "created_by_user_id"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase id={self.id} title={self.title!r} status={self.approval_status}>"
