"""
Ticket Assignment Workflow Tests for QueueMind AI.

Verifies:
1. Routing a ticket to a team places it in the Team Queue.
2. Assigning a ticket to Ananya places it in Ananya's My Assigned list.
3. The same ticket does NOT appear in Vikram's My Assigned list.
4. Reassignment from Ananya to Vikram updates both dashboards.
5. Assignment persists after refresh (re-query).
6. Cross-organisation assignment is rejected.
7. Assignment history is recorded.
8. Help Desk can optionally assign during routing.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.database.session import SessionLocal
from app.main import app
from app.models.organization import Organization, OrganizationType
from app.models.department import Department
from app.models.support_team import SupportTeam
from app.models.issue_category import IssueCategory
from app.models.ticket import Ticket, TicketPriority, TicketSource, TicketStatus
from app.models.user import AccountStatus, User, UserRole

client = TestClient(app)


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def assignment_env(db_session: Session):
    """
    Sets up two organisations with staff:
    Org A (JSS): Student, Help Desk, Team Lead, Ananya (Support), Vikram (Support), Org Admin
    Org B (APEX): Team Lead (for cross-org rejection test)
    """
    s = uuid.uuid4().hex[:6].upper()

    # Org A
    org_a = Organization(
        name=f"JSS Assign Test {s}", code=f"JSS-{s}", slug=f"jss-assign-{s.lower()}",
        contact_email=f"assign_{s.lower()}@jss.edu", org_type=OrganizationType.COLLEGE, is_active=True,
    )
    db_session.add(org_a)
    db_session.flush()

    dept_a = Department(organization_id=org_a.id, name="IT Department")
    db_session.add(dept_a)
    db_session.flush()

    team_a = SupportTeam(organization_id=org_a.id, department_id=dept_a.id, name="Network Support")
    db_session.add(team_a)
    db_session.flush()

    cat_a = IssueCategory(
        organization_id=org_a.id, department_id=dept_a.id,
        support_team_id=team_a.id, name="Network issues",
    )
    db_session.add(cat_a)
    db_session.flush()

    student_a = User(
        organization_id=org_a.id, full_name=f"Student {s}", email=f"student_{s.lower()}@jss.edu",
        hashed_password="hashed_placeholder", role=UserRole.USER, account_status=AccountStatus.ACTIVE,
    )
    helpdesk_a = User(
        organization_id=org_a.id, full_name=f"HelpDesk {s}", email=f"helpdesk_{s.lower()}@jss.edu",
        hashed_password="hashed_placeholder", role=UserRole.HELP_DESK, account_status=AccountStatus.ACTIVE,
    )
    teamlead_a = User(
        organization_id=org_a.id, full_name=f"TeamLead {s}", email=f"teamlead_{s.lower()}@jss.edu",
        hashed_password="hashed_placeholder", role=UserRole.SUPPORT_TEAM_LEAD,
        department_id=dept_a.id, support_team_id=team_a.id, account_status=AccountStatus.ACTIVE,
    )
    ananya = User(
        organization_id=org_a.id, full_name=f"Ananya {s}", email=f"ananya_{s.lower()}@jss.edu",
        hashed_password="hashed_placeholder", role=UserRole.SUPPORT_TEAM_MEMBER,
        department_id=dept_a.id, support_team_id=team_a.id, account_status=AccountStatus.ACTIVE,
    )
    vikram = User(
        organization_id=org_a.id, full_name=f"Vikram {s}", email=f"vikram_{s.lower()}@jss.edu",
        hashed_password="hashed_placeholder", role=UserRole.SUPPORT_TEAM_MEMBER,
        department_id=dept_a.id, support_team_id=team_a.id, account_status=AccountStatus.ACTIVE,
    )
    orgadmin_a = User(
        organization_id=org_a.id, full_name=f"OrgAdmin {s}", email=f"orgadmin_{s.lower()}@jss.edu",
        hashed_password="hashed_placeholder", role=UserRole.ORGANIZATION_ADMIN, account_status=AccountStatus.ACTIVE,
    )
    db_session.add_all([student_a, helpdesk_a, teamlead_a, ananya, vikram, orgadmin_a])

    # Org B (for cross-org rejection)
    org_b = Organization(
        name=f"Apex Assign Test {s}", code=f"APX-{s}", slug=f"apx-assign-{s.lower()}",
        contact_email=f"assign_{s.lower()}@apex.edu", org_type=OrganizationType.UNIVERSITY, is_active=True,
    )
    db_session.add(org_b)
    db_session.flush()

    teamlead_b = User(
        organization_id=org_b.id, full_name=f"TeamLead B {s}", email=f"teamlead_b_{s.lower()}@apex.edu",
        hashed_password="hashed_placeholder", role=UserRole.SUPPORT_TEAM_LEAD, account_status=AccountStatus.ACTIVE,
    )
    db_session.add(teamlead_b)
    db_session.commit()

    return {
        "org_a": org_a, "org_b": org_b,
        "dept_a": dept_a, "team_a": team_a, "cat_a": cat_a,
        "student_a": student_a, "helpdesk_a": helpdesk_a, "teamlead_a": teamlead_a,
        "ananya": ananya, "vikram": vikram, "orgadmin_a": orgadmin_a,
        "teamlead_b": teamlead_b,
        "token_student_a": create_access_token(student_a.id, {"role": "USER", "org_id": org_a.id}),
        "token_helpdesk_a": create_access_token(helpdesk_a.id, {"role": "HELP_DESK", "org_id": org_a.id}),
        "token_teamlead_a": create_access_token(teamlead_a.id, {"role": "SUPPORT_TEAM_LEAD", "org_id": org_a.id}),
        "token_ananya": create_access_token(ananya.id, {"role": "SUPPORT_TEAM_MEMBER", "org_id": org_a.id}),
        "token_vikram": create_access_token(vikram.id, {"role": "SUPPORT_TEAM_MEMBER", "org_id": org_a.id}),
        "token_orgadmin_a": create_access_token(orgadmin_a.id, {"role": "ORGANIZATION_ADMIN", "org_id": org_a.id}),
        "token_teamlead_b": create_access_token(teamlead_b.id, {"role": "SUPPORT_TEAM_LEAD", "org_id": org_b.id}),
    }


# ── Helper: submit and route a ticket ───────────────────────────────────────────

def _submit_ticket(env: dict, subject: str = "Wi-Fi down in lab") -> dict:
    """Submit a ticket as a student and return the response dict."""
    resp = client.post(
        "/api/v1/tickets",
        json={"subject": subject, "description": "Cannot connect to campus network in computer lab Block B."},
        headers=auth_header(env["token_student_a"]),
    )
    assert resp.status_code == 201
    return resp.json()


def _route_ticket(env: dict, ticket_id: int, assigned_engineer_id: int | None = None) -> dict:
    """Route a ticket via Help Desk and optionally assign to an engineer."""
    payload: dict = {
        "department_id": env["dept_a"].id,
        "support_team_id": env["team_a"].id,
        "confirmed_priority": "MEDIUM",
        "category_id": env["cat_a"].id,
    }
    if assigned_engineer_id is not None:
        payload["assigned_engineer_id"] = assigned_engineer_id
    resp = client.post(
        f"/api/v1/tickets/{ticket_id}/route",
        json=payload,
        headers=auth_header(env["token_helpdesk_a"]),
    )
    assert resp.status_code == 200
    return resp.json()


# ── Test 1: Route to Team places ticket in Team Queue ────────────────────────────

def test_route_to_team_places_in_team_queue(assignment_env):
    """Routing a ticket without engineer assignment puts it in APPROVED_FOR_ROUTING status."""
    ticket = _submit_ticket(assignment_env)
    routed = _route_ticket(assignment_env, ticket["id"])

    assert routed["status"] == "APPROVED_FOR_ROUTING"
    assert routed["department_id"] == assignment_env["dept_a"].id
    assert routed["support_team_id"] == assignment_env["team_a"].id
    assert routed["assigned_engineer_id"] is None

    # Team Lead should see this ticket
    resp = client.get("/api/v1/tickets", headers=auth_header(assignment_env["token_teamlead_a"]))
    assert resp.status_code == 200
    team_tickets = resp.json()
    ids = [t["id"] for t in team_tickets]
    assert ticket["id"] in ids


# ── Test 2: Assign to Ananya places it in Ananya's My Assigned ───────────────────

def test_assign_to_ananya_my_assigned(assignment_env):
    """Assigning a ticket to Ananya makes it appear in her 'assigned_to_me' query."""
    ticket = _submit_ticket(assignment_env, "Network outage hostel 3")
    _route_ticket(assignment_env, ticket["id"])

    # Team Lead assigns to Ananya
    resp = client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_engineer_id": assignment_env["ananya"].id},
        headers=auth_header(assignment_env["token_teamlead_a"]),
    )
    assert resp.status_code == 200
    assert resp.json()["assigned_engineer_id"] == assignment_env["ananya"].id
    assert resp.json()["status"] == "ASSIGNED"

    # Ananya's My Assigned list
    resp = client.get(
        "/api/v1/tickets", params={"assigned_to_me": "true"},
        headers=auth_header(assignment_env["token_ananya"]),
    )
    assert resp.status_code == 200
    ananya_ids = [t["id"] for t in resp.json()]
    assert ticket["id"] in ananya_ids


# ── Test 3: Assigned ticket does NOT appear in Vikram's My Assigned ──────────────

def test_assigned_ticket_not_in_vikram_my_assigned(assignment_env):
    """Ticket assigned to Ananya must not appear in Vikram's My Assigned list."""
    ticket = _submit_ticket(assignment_env, "Lab PC not booting")
    _route_ticket(assignment_env, ticket["id"])

    # Assign to Ananya
    client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_engineer_id": assignment_env["ananya"].id},
        headers=auth_header(assignment_env["token_teamlead_a"]),
    )

    # Vikram's My Assigned list must NOT contain this ticket
    resp = client.get(
        "/api/v1/tickets", params={"assigned_to_me": "true"},
        headers=auth_header(assignment_env["token_vikram"]),
    )
    assert resp.status_code == 200
    vikram_ids = [t["id"] for t in resp.json()]
    assert ticket["id"] not in vikram_ids

    # But Vikram can still see it in team view (no assigned_to_me filter)
    resp = client.get("/api/v1/tickets", headers=auth_header(assignment_env["token_vikram"]))
    assert resp.status_code == 200
    all_ids = [t["id"] for t in resp.json()]
    assert ticket["id"] in all_ids


# ── Test 4: Reassignment from Ananya to Vikram ──────────────────────────────────

def test_reassign_from_ananya_to_vikram(assignment_env):
    """Reassigning a ticket from Ananya to Vikram updates both dashboards."""
    ticket = _submit_ticket(assignment_env, "Printer jam in office")
    _route_ticket(assignment_env, ticket["id"])

    # Assign to Ananya first
    client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_engineer_id": assignment_env["ananya"].id},
        headers=auth_header(assignment_env["token_teamlead_a"]),
    )

    # Reassign to Vikram
    resp = client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_engineer_id": assignment_env["vikram"].id, "note": "Reassigning to Vikram"},
        headers=auth_header(assignment_env["token_teamlead_a"]),
    )
    assert resp.status_code == 200
    assert resp.json()["assigned_engineer_id"] == assignment_env["vikram"].id

    # Vikram now sees it in My Assigned
    resp = client.get(
        "/api/v1/tickets", params={"assigned_to_me": "true"},
        headers=auth_header(assignment_env["token_vikram"]),
    )
    vikram_ids = [t["id"] for t in resp.json()]
    assert ticket["id"] in vikram_ids

    # Ananya no longer sees it in My Assigned
    resp = client.get(
        "/api/v1/tickets", params={"assigned_to_me": "true"},
        headers=auth_header(assignment_env["token_ananya"]),
    )
    ananya_ids = [t["id"] for t in resp.json()]
    assert ticket["id"] not in ananya_ids


# ── Test 5: Assignment persists after re-query (simulates refresh) ───────────────

def test_assignment_persists_after_requery(assignment_env):
    """Re-querying the ticket after assignment must still show correct assigned_engineer_id."""
    ticket = _submit_ticket(assignment_env, "Email server offline")
    _route_ticket(assignment_env, ticket["id"])

    client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_engineer_id": assignment_env["ananya"].id},
        headers=auth_header(assignment_env["token_teamlead_a"]),
    )

    # Re-query the specific ticket
    resp = client.get(
        f"/api/v1/tickets/{ticket['id']}",
        headers=auth_header(assignment_env["token_ananya"]),
    )
    assert resp.status_code == 200
    assert resp.json()["assigned_engineer_id"] == assignment_env["ananya"].id
    assert resp.json()["assigned_engineer_name"] == assignment_env["ananya"].full_name


# ── Test 6: Cross-organisation assignment rejected ───────────────────────────────

def test_cross_org_assignment_rejected(assignment_env):
    """Team Lead from Org B must not be able to assign tickets in Org A."""
    ticket = _submit_ticket(assignment_env, "Cross-org test ticket")
    _route_ticket(assignment_env, ticket["id"])

    # Team Lead B tries to assign
    resp = client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_engineer_id": assignment_env["ananya"].id},
        headers=auth_header(assignment_env["token_teamlead_b"]),
    )
    assert resp.status_code == 403


# ── Test 7: Assignment history is recorded ───────────────────────────────────────

def test_assignment_history_recorded(assignment_env):
    """Assigning a ticket must create a TicketHistory entry."""
    ticket = _submit_ticket(assignment_env, "Library system login error")
    _route_ticket(assignment_env, ticket["id"])

    client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_engineer_id": assignment_env["vikram"].id, "note": "Specialist for library systems"},
        headers=auth_header(assignment_env["token_teamlead_a"]),
    )

    # Fetch history
    resp = client.get(
        f"/api/v1/tickets/{ticket['id']}/history",
        headers=auth_header(assignment_env["token_teamlead_a"]),
    )
    assert resp.status_code == 200
    history = resp.json()

    # Find assignment entry
    assign_entries = [h for h in history if "Assigned to" in h.get("description", "")]
    assert len(assign_entries) >= 1
    assert assignment_env["vikram"].full_name in assign_entries[-1]["description"]
    assert assign_entries[-1]["new_status"] == "ASSIGNED"


# ── Test 8: Help Desk can assign directly during routing ─────────────────────────

def test_helpdesk_direct_assign_during_routing(assignment_env):
    """Help Desk can optionally assign to engineer in the same route operation."""
    ticket = _submit_ticket(assignment_env, "Projector broken in conference room")

    routed = _route_ticket(assignment_env, ticket["id"], assigned_engineer_id=assignment_env["vikram"].id)

    assert routed["status"] == "ASSIGNED"
    assert routed["assigned_engineer_id"] == assignment_env["vikram"].id
    assert routed["department_id"] == assignment_env["dept_a"].id
    assert routed["support_team_id"] == assignment_env["team_a"].id

    # Vikram sees it in My Assigned
    resp = client.get(
        "/api/v1/tickets", params={"assigned_to_me": "true"},
        headers=auth_header(assignment_env["token_vikram"]),
    )
    vikram_ids = [t["id"] for t in resp.json()]
    assert ticket["id"] in vikram_ids


# ── Test 9: Help Desk can also use standalone assign endpoint ────────────────────

def test_helpdesk_standalone_assign(assignment_env):
    """Help Desk can assign tickets using the /assign endpoint (now HELP_DESK is an allowed role)."""
    ticket = _submit_ticket(assignment_env, "Scanner not responding")
    _route_ticket(assignment_env, ticket["id"])

    resp = client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_engineer_id": assignment_env["ananya"].id},
        headers=auth_header(assignment_env["token_helpdesk_a"]),
    )
    assert resp.status_code == 200
    assert resp.json()["assigned_engineer_id"] == assignment_env["ananya"].id


# ── Test 10: Cannot assign to non-support role ──────────────────────────────────

def test_cannot_assign_to_non_support_role(assignment_env):
    """Assigning a ticket to a user with non-support role (e.g., Student) must be rejected."""
    ticket = _submit_ticket(assignment_env, "Non-support role test")
    _route_ticket(assignment_env, ticket["id"])

    resp = client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_engineer_id": assignment_env["student_a"].id},
        headers=auth_header(assignment_env["token_teamlead_a"]),
    )
    assert resp.status_code == 400
    assert "role" in resp.json()["detail"].lower()
