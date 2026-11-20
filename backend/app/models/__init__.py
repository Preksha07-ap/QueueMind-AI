"""
SQLAlchemy ORM models package.

Import order matters: models with no foreign-key dependencies come first
so that forward references resolve cleanly.
"""

# ── 1. Base (no FKs) ──────────────────────────────────────────────────────────
from app.models.organization import Organization, OrganizationType  # noqa: F401

# ── 2. Depend on Organization only ───────────────────────────────────────────
from app.models.department import Department  # noqa: F401

# ── 3. Depend on Organization + Department ────────────────────────────────────
from app.models.support_team import SupportTeam  # noqa: F401
from app.models.user import User, UserRole, AccountStatus  # noqa: F401

# ── 4. Depend on the above ────────────────────────────────────────────────────
from app.models.issue_category import IssueCategory  # noqa: F401

# ── 5. Core transactional models ──────────────────────────────────────────────
from app.models.ticket import Ticket, TicketStatus, TicketPriority, TicketSource  # noqa: F401
from app.models.ticket_history import TicketHistory  # noqa: F401
from app.models.ticket_comment import TicketComment  # noqa: F401
from app.models.ticket_attachment import TicketAttachment  # noqa: F401

# ── 6. Supporting models ──────────────────────────────────────────────────────
from app.models.notification import Notification, NotificationType  # noqa: F401
from app.models.knowledge_base import KnowledgeBase, KBApprovalStatus  # noqa: F401

__all__ = [
    # Organizations
    "Organization",
    "OrganizationType",
    # Users
    "User",
    "UserRole",
    "AccountStatus",
    # Departments
    "Department",
    # Support Teams
    "SupportTeam",
    # Issue Categories
    "IssueCategory",
    # Tickets
    "Ticket",
    "TicketStatus",
    "TicketPriority",
    "TicketSource",
    # Ticket History
    "TicketHistory",
    # Ticket Comments
    "TicketComment",
    # Ticket Attachments
    "TicketAttachment",
    # Notifications
    "Notification",
    "NotificationType",
    # Knowledge Base
    "KnowledgeBase",
    "KBApprovalStatus",
    # Incident Clusters
    "IncidentCluster",
]
