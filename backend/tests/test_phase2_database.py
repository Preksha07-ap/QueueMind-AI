"""
Phase 2 — Automated Test Suite
================================
Tests:
  1. Database connection
  2. Model creation (all 10 models)
  3. Foreign key relationships
  4. Ticket creation with all fields
  5. Organisation-level data separation (multi-tenancy)
  6. Ticket history creation

Run with:
    cd backend
    python -m pytest tests/test_phase2_database.py -v
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.database.base import Base, import_all_models
from app.database.session import check_db_connection

# Ensure all models are registered on Base.metadata
import_all_models()

from app.models import (
    Organization, OrganizationType,
    Department,
    SupportTeam,
    User, UserRole, AccountStatus,
    IssueCategory,
    Ticket, TicketStatus, TicketPriority, TicketSource,
    TicketHistory,
    TicketComment,
    Notification, NotificationType,
    KnowledgeBase, KBApprovalStatus,
)

# ── Test engine (uses the same MySQL DB, isolated via transaction rollbacks) ───
engine = create_engine(settings.database_url, pool_pre_ping=True, echo=False)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Session:
    """
    Provide a database session wrapped in a transaction that is rolled back
    after each test.  This keeps tests isolated without truncating tables.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Required for MySQL nested transaction support
    session.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Database connection
# ─────────────────────────────────────────────────────────────────────────────

class TestDatabaseConnection:

    def test_check_db_connection_returns_connected(self):
        result = check_db_connection()
        assert result["connected"] is True, (
            f"Expected DB to be reachable but got: {result['detail']}"
        )

    def test_raw_select_one(self):
        with engine.connect() as conn:
            row = conn.execute(text("SELECT 1 AS ping")).fetchone()
        assert row is not None
        assert row[0] == 1

    def test_database_url_uses_pymysql(self):
        assert "pymysql" in settings.database_url

    def test_database_credentials_read_from_env(self):
        # Confirm values are not the placeholder defaults
        assert settings.DB_PASSWORD != "your_secure_password_here"
        assert settings.DB_NAME == "queuemind_db"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Model creation
# ─────────────────────────────────────────────────────────────────────────────

def _make_org(db: Session, name: str = "Test University", email: str = "admin@testuni.edu", code: str | None = None, slug: str | None = None) -> Organization:
    unique_suffix = f"{abs(hash(name + email)) % 100000:05d}"
    org = Organization(
        name=name,
        code=code or f"ORG-{unique_suffix}",
        slug=slug or f"org-{unique_suffix}",
        org_type=OrganizationType.UNIVERSITY,
        description="A test organisation",
        contact_email=email,
        is_active=True,
    )
    db.add(org)
    db.flush()
    return org


def _make_department(db: Session, org: Organization, name: str = "IT Department") -> Department:
    dept = Department(organization_id=org.id, name=name, description="IT", is_active=True)
    db.add(dept)
    db.flush()
    return dept


def _make_support_team(db: Session, org: Organization, dept: Department, name: str = "Network Support") -> SupportTeam:
    team = SupportTeam(
        organization_id=org.id,
        department_id=dept.id,
        name=name,
        description="Handles network issues",
        is_active=True,
    )
    db.add(team)
    db.flush()
    return team


def _make_user(
    db: Session,
    org: Organization,
    email: str = "user@testuni.edu",
    role: UserRole = UserRole.USER,
    dept: Department | None = None,
) -> User:
    user = User(
        organization_id=org.id,
        full_name="Test User",
        email=email,
        hashed_password="$2b$12$fakehash",
        role=role,
        department_id=dept.id if dept else None,
        account_status=AccountStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    return user


def _make_category(db: Session, org: Organization, dept: Department, team: SupportTeam, name: str = "Network Issue") -> IssueCategory:
    cat = IssueCategory(
        organization_id=org.id,
        name=name,
        description="Internet/Network issues",
        department_id=dept.id,
        support_team_id=team.id,
        is_active=True,
    )
    db.add(cat)
    db.flush()
    return cat


def _make_ticket(
    db: Session,
    org: Organization,
    user: User,
    category: IssueCategory,
    ticket_number: str = "TKT-00001",
) -> Ticket:
    ticket = Ticket(
        organization_id=org.id,
        ticket_number=ticket_number,
        user_id=user.id,
        category_id=category.id,
        subject="Cannot connect to internet",
        description="My laptop lost its WiFi connection after the last update.",
        source=TicketSource.WEB,
        status=TicketStatus.SUBMITTED,
    )
    db.add(ticket)
    db.flush()
    return ticket


class TestModelCreation:

    def test_create_organization(self, db: Session):
        org = _make_org(db)
        assert org.id is not None
        assert org.name == "Test University"
        assert org.org_type == OrganizationType.UNIVERSITY
        assert org.is_active is True

    def test_create_department(self, db: Session):
        org = _make_org(db)
        dept = _make_department(db, org)
        assert dept.id is not None
        assert dept.organization_id == org.id

    def test_create_support_team(self, db: Session):
        org = _make_org(db)
        dept = _make_department(db, org)
        team = _make_support_team(db, org, dept)
        assert team.id is not None
        assert team.department_id == dept.id

    def test_create_user_with_hashed_password(self, db: Session):
        org = _make_org(db)
        user = _make_user(db, org)
        assert user.id is not None
        # Confirm password is NEVER stored in plain text
        assert user.hashed_password != "password123"
        assert user.hashed_password.startswith("$")

    def test_create_issue_category(self, db: Session):
        org = _make_org(db)
        dept = _make_department(db, org)
        team = _make_support_team(db, org, dept)
        cat = _make_category(db, org, dept, team)
        assert cat.id is not None
        assert cat.department_id == dept.id
        assert cat.support_team_id == team.id

    def test_create_ticket_with_all_fields(self, db: Session):
        org = _make_org(db)
        dept = _make_department(db, org)
        team = _make_support_team(db, org, dept)
        user = _make_user(db, org)
        cat = _make_category(db, org, dept, team)
        ticket = _make_ticket(db, org, user, cat)

        assert ticket.id is not None
        assert ticket.ticket_number == "TKT-00001"
        assert ticket.status == TicketStatus.SUBMITTED
        assert ticket.source == TicketSource.WEB
        # AI & routing fields start as None
        assert ticket.ai_predicted_priority is None
        assert ticket.confirmed_priority is None
        assert ticket.department_id is None
        assert ticket.support_team_id is None
        assert ticket.assigned_engineer_id is None

    def test_create_ticket_comment(self, db: Session):
        org = _make_org(db)
        dept = _make_department(db, org)
        team = _make_support_team(db, org, dept)
        user = _make_user(db, org)
        cat = _make_category(db, org, dept, team)
        ticket = _make_ticket(db, org, user, cat)

        comment = TicketComment(
            organization_id=org.id,
            ticket_id=ticket.id,
            user_id=user.id,
            comment="Please provide more details about your OS version.",
        )
        db.add(comment)
        db.flush()
        assert comment.id is not None

    def test_create_notification(self, db: Session):
        org = _make_org(db)
        user = _make_user(db, org)
        notif = Notification(
            organization_id=org.id,
            recipient_user_id=user.id,
            ticket_id=None,
            title="Welcome",
            message="Your account has been created.",
            notification_type=NotificationType.SYSTEM,
            is_read=False,
        )
        db.add(notif)
        db.flush()
        assert notif.id is not None
        assert notif.is_read is False

    def test_create_knowledge_base_entry(self, db: Session):
        org = _make_org(db)
        dept = _make_department(db, org)
        team = _make_support_team(db, org, dept)
        user = _make_user(db, org, role=UserRole.SUPPORT_TEAM_MEMBER)
        cat = _make_category(db, org, dept, team)
        kb = KnowledgeBase(
            organization_id=org.id,
            title="Fix for WiFi dropout after update",
            problem_description="Laptop loses WiFi after Windows update KB12345.",
            solution="Roll back driver or disable power saving on adapter.",
            category_id=cat.id,
            created_by_user_id=user.id,
            approval_status=KBApprovalStatus.DRAFT,
        )
        db.add(kb)
        db.flush()
        assert kb.id is not None


# ─────────────────────────────────────────────────────────────────────────────
# 3. Foreign key relationships
# ─────────────────────────────────────────────────────────────────────────────

class TestForeignKeyRelationships:

    def test_org_has_many_departments(self, db: Session):
        org = _make_org(db)
        _make_department(db, org, "IT Department")
        _make_department(db, org, "Accounts Department")
        db.refresh(org)
        assert len(org.departments) == 2

    def test_department_has_many_support_teams(self, db: Session):
        org = _make_org(db)
        dept = _make_department(db, org)
        _make_support_team(db, org, dept, "Network Support")
        _make_support_team(db, org, dept, "Hardware Support")
        db.refresh(dept)
        assert len(dept.support_teams) == 2

    def test_user_belongs_to_org(self, db: Session):
        org = _make_org(db)
        user = _make_user(db, org)
        db.refresh(user)
        assert user.organization.id == org.id

    def test_ticket_belongs_to_user_and_org(self, db: Session):
        org = _make_org(db)
        dept = _make_department(db, org)
        team = _make_support_team(db, org, dept)
        user = _make_user(db, org)
        cat = _make_category(db, org, dept, team)
        ticket = _make_ticket(db, org, user, cat)
        db.refresh(ticket)
        assert ticket.submitted_by.id == user.id
        assert ticket.organization.id == org.id

    def test_user_has_many_submitted_tickets(self, db: Session):
        org = _make_org(db)
        dept = _make_department(db, org)
        team = _make_support_team(db, org, dept)
        user = _make_user(db, org)
        cat = _make_category(db, org, dept, team)
        _make_ticket(db, org, user, cat, "TKT-00001")
        _make_ticket(db, org, user, cat, "TKT-00002")
        db.refresh(user)
        assert len(user.submitted_tickets) == 2

    def test_engineer_can_be_assigned_multiple_tickets(self, db: Session):
        org = _make_org(db)
        dept = _make_department(db, org)
        team = _make_support_team(db, org, dept)
        submitter = _make_user(db, org, email="submitter@uni.edu")
        engineer = _make_user(db, org, email="eng@uni.edu", role=UserRole.SUPPORT_TEAM_MEMBER)
        cat = _make_category(db, org, dept, team)

        for i in range(3):
            t = _make_ticket(db, org, submitter, cat, f"TKT-{i:05d}")
            t.assigned_engineer_id = engineer.id
            t.status = TicketStatus.ASSIGNED
        db.flush()
        db.refresh(engineer)
        assert len(engineer.assigned_tickets) == 3


# ─────────────────────────────────────────────────────────────────────────────
# 4. Ticket history creation
# ─────────────────────────────────────────────────────────────────────────────

class TestTicketHistoryCreation:

    def test_create_initial_history_entry(self, db: Session):
        org = _make_org(db)
        dept = _make_department(db, org)
        team = _make_support_team(db, org, dept)
        user = _make_user(db, org)
        cat = _make_category(db, org, dept, team)
        ticket = _make_ticket(db, org, user, cat)

        history = TicketHistory(
            organization_id=org.id,
            ticket_id=ticket.id,
            previous_status=None,
            new_status=TicketStatus.SUBMITTED,
            changed_by_user_id=user.id,
            description="Ticket submitted via web portal.",
        )
        db.add(history)
        db.flush()
        assert history.id is not None
        assert history.previous_status is None

    def test_ticket_has_many_history_records(self, db: Session):
        org = _make_org(db)
        dept = _make_department(db, org)
        team = _make_support_team(db, org, dept)
        user = _make_user(db, org)
        helpdesk = _make_user(db, org, email="helpdesk@uni.edu", role=UserRole.HELP_DESK)
        cat = _make_category(db, org, dept, team)
        ticket = _make_ticket(db, org, user, cat)

        transitions = [
            (None, TicketStatus.SUBMITTED, user.id, "Ticket submitted."),
            (TicketStatus.SUBMITTED, TicketStatus.AI_ANALYSIS, None, "AI analysis started."),
            (TicketStatus.AI_ANALYSIS, TicketStatus.AWAITING_HELP_DESK_REVIEW, None, "AI analysis complete."),
            (TicketStatus.AWAITING_HELP_DESK_REVIEW, TicketStatus.APPROVED_FOR_ROUTING, helpdesk.id, "Help Desk approved routing."),
        ]
        for prev, new, changer, desc in transitions:
            h = TicketHistory(
                organization_id=org.id,
                ticket_id=ticket.id,
                previous_status=prev,
                new_status=new,
                changed_by_user_id=changer,
                description=desc,
            )
            db.add(h)
        db.flush()
        db.refresh(ticket)
        assert len(ticket.history) == 4


# ─────────────────────────────────────────────────────────────────────────────
# 5. Organisation-level data separation (multi-tenancy)
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiTenancyIsolation:

    def test_organisations_are_independent(self, db: Session):
        org_a = _make_org(db, name="University A", email="admin@a.edu")
        org_b = _make_org(db, name="University B", email="admin@b.edu")
        assert org_a.id != org_b.id

    def test_tickets_scoped_to_their_org(self, db: Session):
        org_a = _make_org(db, name="Org Alpha", email="alpha@alpha.edu")
        org_b = _make_org(db, name="Org Beta", email="beta@beta.edu")

        dept_a = _make_department(db, org_a, "IT-A")
        team_a = _make_support_team(db, org_a, dept_a, "Net-A")
        user_a = _make_user(db, org_a, email="user@alpha.edu")
        cat_a = _make_category(db, org_a, dept_a, team_a, "Net Issue A")
        ticket_a = _make_ticket(db, org_a, user_a, cat_a, "TKT-A0001")

        dept_b = _make_department(db, org_b, "IT-B")
        team_b = _make_support_team(db, org_b, dept_b, "Net-B")
        user_b = _make_user(db, org_b, email="user@beta.edu")
        cat_b = _make_category(db, org_b, dept_b, team_b, "Net Issue B")
        ticket_b = _make_ticket(db, org_b, user_b, cat_b, "TKT-B0001")

        # Query strictly filtered by org_id
        tickets_in_a = db.query(Ticket).filter(Ticket.organization_id == org_a.id).all()
        tickets_in_b = db.query(Ticket).filter(Ticket.organization_id == org_b.id).all()

        assert all(t.organization_id == org_a.id for t in tickets_in_a)
        assert all(t.organization_id == org_b.id for t in tickets_in_b)
        assert ticket_a.id not in [t.id for t in tickets_in_b]
        assert ticket_b.id not in [t.id for t in tickets_in_a]

    def test_users_scoped_to_their_org(self, db: Session):
        org_a = _make_org(db, name="School A", email="admin@schoola.edu")
        org_b = _make_org(db, name="School B", email="admin@schoolb.edu")
        _make_user(db, org_a, email="alice@schoola.edu")
        _make_user(db, org_a, email="bob@schoola.edu")
        _make_user(db, org_b, email="charlie@schoolb.edu")

        users_a = db.query(User).filter(User.organization_id == org_a.id).all()
        users_b = db.query(User).filter(User.organization_id == org_b.id).all()

        assert len(users_a) == 2
        assert len(users_b) == 1

    def test_same_ticket_number_allowed_across_orgs(self, db: Session):
        """ticket_number uniqueness is per-org, not global."""
        org_a = _make_org(db, name="College A", email="admin@ca.edu")
        org_b = _make_org(db, name="College B", email="admin@cb.edu")

        dept_a = _make_department(db, org_a)
        team_a = _make_support_team(db, org_a, dept_a)
        user_a = _make_user(db, org_a, email="u@ca.edu")
        cat_a = _make_category(db, org_a, dept_a, team_a)

        dept_b = _make_department(db, org_b)
        team_b = _make_support_team(db, org_b, dept_b)
        user_b = _make_user(db, org_b, email="u@cb.edu")
        cat_b = _make_category(db, org_b, dept_b, team_b)

        # Same ticket_number "TKT-00001" in two different orgs — must not conflict
        t_a = _make_ticket(db, org_a, user_a, cat_a, "TKT-00001")
        t_b = _make_ticket(db, org_b, user_b, cat_b, "TKT-00001")

        assert t_a.ticket_number == t_b.ticket_number
        assert t_a.organization_id != t_b.organization_id

    def test_knowledge_base_scoped_to_org(self, db: Session):
        org_a = _make_org(db, name="Institute A", email="admin@ia.edu")
        org_b = _make_org(db, name="Institute B", email="admin@ib.edu")

        user_a = _make_user(db, org_a, email="u@ia.edu")
        user_b = _make_user(db, org_b, email="u@ib.edu")

        kb_a = KnowledgeBase(
            organization_id=org_a.id,
            title="Fix A",
            problem_description="Problem in A",
            solution="Solution for A",
            created_by_user_id=user_a.id,
            approval_status=KBApprovalStatus.APPROVED,
        )
        kb_b = KnowledgeBase(
            organization_id=org_b.id,
            title="Fix B",
            problem_description="Problem in B",
            solution="Solution for B",
            created_by_user_id=user_b.id,
            approval_status=KBApprovalStatus.DRAFT,
        )
        db.add_all([kb_a, kb_b])
        db.flush()

        kb_in_a = db.query(KnowledgeBase).filter(KnowledgeBase.organization_id == org_a.id).all()
        kb_in_b = db.query(KnowledgeBase).filter(KnowledgeBase.organization_id == org_b.id).all()

        assert len(kb_in_a) == 1
        assert len(kb_in_b) == 1
        assert kb_in_a[0].title == "Fix A"
        assert kb_in_b[0].title == "Fix B"
