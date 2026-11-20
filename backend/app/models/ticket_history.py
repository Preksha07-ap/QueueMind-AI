"""
TicketHistory model — immutable audit trail for every status transition.
Records are never deleted (cascade is intentionally omitted on the
organization side; only the ticket's cascade controls deletion).
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, DateTime, Enum as SAEnum, ForeignKey, Index, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.ticket import TicketStatus


class TicketHistory(Base):
    __tablename__ = "ticket_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    ticket_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    previous_status: Mapped[TicketStatus | None] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status_enum"),
        nullable=True,  # null for the initial SUBMITTED entry
    )
    new_status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status_enum"),
        nullable=False,
    )
    changed_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── relationships ──────────────────────────────────────────────────────────
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="ticket_history"
    )
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="history")
    changed_by: Mapped["User | None"] = relationship(
        "User",
        back_populates="ticket_history_entries",
        foreign_keys=[changed_by_user_id],
    )

    __table_args__ = (
        Index("ix_ticket_history_organization_id", "organization_id"),
        Index("ix_ticket_history_ticket_id", "ticket_id"),
        Index("ix_ticket_history_changed_by_user_id", "changed_by_user_id"),
        Index("ix_ticket_history_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<TicketHistory id={self.id} ticket_id={self.ticket_id} "
            f"{self.previous_status} → {self.new_status}>"
        )
