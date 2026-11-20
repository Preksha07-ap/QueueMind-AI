"""
TicketAttachment model — file attachments uploaded to support tickets.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, DateTime, ForeignKey, Index, String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    ticket_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── relationships ──────────────────────────────────────────────────────────
    organization: Mapped["Organization"] = relationship("Organization")
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="attachments")
    uploaded_by: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("ix_ticket_attachments_organization_id", "organization_id"),
        Index("ix_ticket_attachments_ticket_id", "ticket_id"),
        Index("ix_ticket_attachments_uploaded_by_user_id", "uploaded_by_user_id"),
    )

    def __repr__(self) -> str:
        return f"<TicketAttachment id={self.id} file_name={self.file_name!r}>"
