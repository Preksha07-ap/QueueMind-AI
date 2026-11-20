"""
Comprehensive Automated Test Suite for Phase 4:
Core Ticket Management and User Registration in QueueMind AI.

Tests:
1. User registration with organization code validation and duplicate protection.
2. Ticket submission (unique ticket numbers, status SUBMITTED, history entry).
3. Multi-tenant scoping and cross-organization isolation.
4. Role-based ticket visibility (USER, HELP_DESK, SUPPORT_TEAM_MEMBER, SUPPORT_TEAM_LEAD).
5. Help Desk triage and routing workflow (APPROVED_FOR_ROUTING).
6. Team Lead queue prioritisation and engineer assignment (ASSIGNED).
7. Solution Helper / Engineer lifecycle and resolution (IN_PROGRESS, RESOLVED).
8. Threaded discussion with internal staff notes vs public comments isolation.
9. Audit trail completeness (TicketHistory).
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.database.session import SessionLocal
from app.main import app
from app.models.department import Department
from app.models.issue_category import IssueCategory
from app.models.organization import Organization, OrganizationType
from app.models.support_team import SupportTeam
from app.models.ticket import Ticket, TicketPriority, TicketSource, TicketStatus
from app.models.ticket_comment import TicketComment
from app.models.ticket_history import TicketHistory
from app.models.user import AccountStatus, User, UserRole

client = TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def test_environment(db_session: Session):
    """
    Sets up two independent test organisations with staff and users for Phase 4 testing:
    - Primary Org: 'TKT-ORG-A'
    - Foreign Org: 'TKT-ORG-B'
    """
    uid = uuid.uuid4().hex[:6].upper()

    # Org A
    org_a = Organization(
        name=f"Phase 4 Org A {uid}",
        code=f"ORG-A-{uid}",
        slug=f"org-a-{uid.lower()}",
        org_type=OrganizationType.COLLEGE,
        contact_email=f"admin_{uid.lower()}@orga.edu",
        is_active=True,
    )
    db_session.add(org_a)

    # Org B
    org_b = Organization(
        name=f"Phase 4 Org B {uid}",
        code=f"ORG-B-{uid}",
        slug=f"org-b-{uid.lower()}",
        org_type=OrganizationType.UNIVERSITY,
        contact_email=f"admin_{uid.lower()}@orgb.edu",
        is_active=True,
    )
    db_session.add(org_b)
    db_session.flush()

    # Department and Support Team in Org A
    dept_a = Department(
        organization_id=org_a.id,
        name="IT Services",
        is_active=True,
    )
    db_session.add(dept_a)
    db_session.flush()

    team_a = SupportTeam(
        organization_id=org_a.id,
        department_id=dept_a.id,
        name="Hardware & Systems",
        is_active=True,
    )
    db_session.add(team_a)
    db_session.flush()

    # Category in Org A
    cat_a = IssueCategory(
        organization_id=org_a.id,
        name="Hardware Fault",
        description="Desktop and printer hardware issues",
        department_id=dept_a.id,
        support_team_id=team_a.id,
        is_active=True,
    )
    db_session.add(cat_a)
    db_session.flush()

    # Users in Org A
    student_a = User(
        organization_id=org_a.id,
        full_name="Alice Student",
        email=f"alice_{uid.lower()}@orga.edu",
        hashed_password=get_password_hash("Pass123!"),
        role=UserRole.USER,
        account_status=AccountStatus.ACTIVE,
    )
    student_a_2 = User(
        organization_id=org_a.id,
        full_name="Bob Student",
        email=f"bob_{uid.lower()}@orga.edu",
        hashed_password=get_password_hash("Pass123!"),
        role=UserRole.USER,
        account_status=AccountStatus.ACTIVE,
    )
    helpdesk_a = User(
        organization_id=org_a.id,
        full_name="Henry HelpDesk",
        email=f"henry_{uid.lower()}@orga.edu",
        hashed_password=get_password_hash("Pass123!"),
        role=UserRole.HELP_DESK,
        department_id=dept_a.id,
        account_status=AccountStatus.ACTIVE,
    )
    lead_a = User(
        organization_id=org_a.id,
        full_name="Liam TeamLead",
        email=f"liam_{uid.lower()}@orga.edu",
        hashed_password=get_password_hash("Pass123!"),
        role=UserRole.SUPPORT_TEAM_LEAD,
        department_id=dept_a.id,
        support_team_id=team_a.id,
        account_status=AccountStatus.ACTIVE,
    )
    engineer_a = User(
        organization_id=org_a.id,
        full_name="Evan Engineer",
        email=f"evan_{uid.lower()}@orga.edu",
        hashed_password=get_password_hash("Pass123!"),
        role=UserRole.SUPPORT_TEAM_MEMBER,
        department_id=dept_a.id,
        support_team_id=team_a.id,
        account_status=AccountStatus.ACTIVE,
    )
    admin_a = User(
        organization_id=org_a.id,
        full_name="Arthur Admin",
        email=f"admin_{uid.lower()}@orga.edu",
        hashed_password=get_password_hash("Pass123!"),
        role=UserRole.ORGANIZATION_ADMIN,
        department_id=dept_a.id,
        account_status=AccountStatus.ACTIVE,
    )

    # Users in Org B
    student_b = User(
        organization_id=org_b.id,
        full_name="Brenda Student B",
        email=f"brenda_{uid.lower()}@orgb.edu",
        hashed_password=get_password_hash("Pass123!"),
        role=UserRole.USER,
        account_status=AccountStatus.ACTIVE,
    )

    db_session.add_all([student_a, student_a_2, helpdesk_a, lead_a, engineer_a, admin_a, student_b])
    db_session.commit()

    def make_auth_header(user: User):
        token = create_access_token(
            subject=user.id,
            claims={"role": user.role.value, "org_id": user.organization_id, "email": user.email},
        )
        return {"Authorization": f"Bearer {token}"}

    return {
        "org_a": org_a,
        "org_b": org_b,
        "dept_a": dept_a,
        "team_a": team_a,
        "cat_a": cat_a,
        "student_a": student_a,
        "student_a_headers": make_auth_header(student_a),
        "student_a_2": student_a_2,
        "student_a_2_headers": make_auth_header(student_a_2),
        "helpdesk_a": helpdesk_a,
        "helpdesk_a_headers": make_auth_header(helpdesk_a),
        "lead_a": lead_a,
        "lead_a_headers": make_auth_header(lead_a),
        "engineer_a": engineer_a,
        "engineer_a_headers": make_auth_header(engineer_a),
        "admin_a": admin_a,
        "admin_a_headers": make_auth_header(admin_a),
        "student_b": student_b,
        "student_b_headers": make_auth_header(student_b),
    }


# ── 1. User Registration Tests ─────────────────────────────────────────────────

def test_user_registration_validates_org_and_role(test_environment):
    org_code = test_environment["org_a"].code
    email = f"newstudent_{uuid.uuid4().hex[:6]}@orga.edu"

    # Successful registration
    response = client.post(
        "/api/v1/auth/register",
        json={
            "org_code": org_code,
            "full_name": "New Enrolled Student",
            "email": email,
            "password": "SecurePassword123!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "USER"
    assert data["email"] == email.lower()
    assert data["organization_code"] == org_code

    # Prevent duplicate in same org
    dup_res = client.post(
        "/api/v1/auth/register",
        json={
            "org_code": org_code,
            "full_name": "Duplicate Student",
            "email": email,
            "password": "SecurePassword123!",
        },
    )
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"].lower()

    # Reject non-existent organisation code
    fake_res = client.post(
        "/api/v1/auth/register",
        json={
            "org_code": "DOES-NOT-EXIST",
            "full_name": "Fake Student",
            "email": f"fake_{uuid.uuid4().hex[:4]}@unknown.edu",
            "password": "SecurePassword123!",
        },
    )
    assert fake_res.status_code == 404


# ── 2. Ticket Creation Tests ───────────────────────────────────────────────────

def test_user_ticket_submission_lifecycle(test_environment):
    headers = test_environment["student_a_headers"]
    cat_id = test_environment["cat_a"].id

    payload = {
        "subject": "Lab 3 Desktop Monitor Flashing Repeatedly",
        "description": "The monitor in row B terminal 4 flickers constantly when turned on.",
        "category_id": cat_id,
        "impact": "HIGH",
        "urgency": "MEDIUM",
        "priority": "HIGH",
        "source": "WEB",
        "attachment_names": ["screenshot_flicker.png"],
    }

    res = client.post("/api/v1/tickets", json=payload, headers=headers)
    assert res.status_code == 201
    ticket = res.json()

    assert ticket["ticket_number"].startswith("TKT-")
    assert ticket["status"] in ("SUBMITTED", "AWAITING_HELP_DESK_REVIEW")
    assert ticket["subject"] == payload["subject"]
    assert ticket["confirmed_priority"] in ("HIGH", "LOW", "MEDIUM", "CRITICAL")
    assert ticket["category_name"] == "Hardware Fault"
    assert ticket["user_id"] == test_environment["student_a"].id

    ticket_id = ticket["id"]

    # Verify history entry created
    hist_res = client.get(f"/api/v1/tickets/{ticket_id}/history", headers=headers)
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 1
    assert history[0]["new_status"] == "SUBMITTED"
    assert "Ticket created" in history[0]["description"]


# ── 3. Multi-Tenant and Scoping Isolation Tests ────────────────────────────────

def test_user_can_only_see_own_tickets(test_environment):
    headers_a = test_environment["student_a_headers"]
    headers_a_2 = test_environment["student_a_2_headers"]

    # Student A creates a ticket
    create_res = client.post(
        "/api/v1/tickets",
        json={
            "subject": "Alice Private Ticket",
            "description": "Private network connection problem for Alice.",
            "priority": "LOW",
        },
        headers=headers_a,
    )
    alice_tkt_id = create_res.json()["id"]

    # Student A can view it
    get_alice = client.get(f"/api/v1/tickets/{alice_tkt_id}", headers=headers_a)
    assert get_alice.status_code == 200

    # Student A2 in the same organisation CANNOT view it
    get_bob = client.get(f"/api/v1/tickets/{alice_tkt_id}", headers=headers_a_2)
    assert get_bob.status_code == 403

    # Student B in another organisation CANNOT view it
    headers_b = test_environment["student_b_headers"]
    get_brenda = client.get(f"/api/v1/tickets/{alice_tkt_id}", headers=headers_b)
    assert get_brenda.status_code == 403


def test_cross_tenant_ticket_modification_forbidden(test_environment):
    headers_a = test_environment["student_a_headers"]
    headers_b = test_environment["student_b_headers"]

    # Create ticket in Org A
    create_res = client.post(
        "/api/v1/tickets",
        json={
            "subject": "Org A Confidential Issue",
            "description": "Sensitive server error in Org A.",
        },
        headers=headers_a,
    )
    tkt_id = create_res.json()["id"]

    # User in Org B attempts to comment
    comment_res = client.post(
        f"/api/v1/tickets/{tkt_id}/comments",
        json={"comment": "Intruding comment from Org B"},
        headers=headers_b,
    )
    assert comment_res.status_code == 403

    # User in Org B attempts to update
    patch_res = client.patch(
        f"/api/v1/tickets/{tkt_id}",
        json={"subject": "Hacked Title"},
        headers=headers_b,
    )
    assert patch_res.status_code == 403


# ── 4. Help Desk Review & Routing Workflow ─────────────────────────────────────

def test_helpdesk_review_and_routing_workflow(test_environment):
    student_headers = test_environment["student_a_headers"]
    helpdesk_headers = test_environment["helpdesk_a_headers"]
    dept_id = test_environment["dept_a"].id
    team_id = test_environment["team_a"].id

    # 1. Student creates ticket
    tkt_res = client.post(
        "/api/v1/tickets",
        json={
            "subject": "Campus WiFi Dropouts in Library",
            "description": "Connection drops every 10 minutes in Library 2nd floor.",
            "priority": "LOW",
        },
        headers=student_headers,
    )
    tkt_id = tkt_res.json()["id"]

    # 2. Help Desk views incoming queue
    queue_res = client.get("/api/v1/tickets?status=SUBMITTED", headers=helpdesk_headers)
    assert queue_res.status_code == 200
    ticket_ids = [t["id"] for t in queue_res.json()]
    assert tkt_id in ticket_ids

    # 3. Regular student cannot route ticket
    unauth_route = client.post(
        f"/api/v1/tickets/{tkt_id}/route",
        json={
            "department_id": dept_id,
            "support_team_id": team_id,
            "confirmed_priority": "CRITICAL",
        },
        headers=student_headers,
    )
    assert unauth_route.status_code == 403

    # 4. Help Desk validates urgency, elevates priority to CRITICAL, routes to Support Team
    route_res = client.post(
        f"/api/v1/tickets/{tkt_id}/route",
        json={
            "department_id": dept_id,
            "support_team_id": team_id,
            "confirmed_priority": "CRITICAL",
            "note": "Confirmed library access point outage affecting 80+ students.",
        },
        headers=helpdesk_headers,
    )
    assert route_res.status_code == 200
    routed_tkt = route_res.json()
    assert routed_tkt["status"] == "APPROVED_FOR_ROUTING"
    assert routed_tkt["confirmed_priority"] == "CRITICAL"
    assert routed_tkt["department_name"] == "IT Services"
    assert routed_tkt["support_team_name"] == "Hardware & Systems"

    # 5. Check history audit entry
    hist = client.get(f"/api/v1/tickets/{tkt_id}/history", headers=helpdesk_headers).json()
    assert any(h["new_status"] == "APPROVED_FOR_ROUTING" for h in hist)


# ── 5. Team Lead Workload & Assignment Tests ───────────────────────────────────

def test_team_lead_assignment_and_prioritisation(test_environment):
    lead_headers = test_environment["lead_a_headers"]
    student_headers = test_environment["student_a_headers"]
    helpdesk_headers = test_environment["helpdesk_a_headers"]
    engineer_id = test_environment["engineer_a"].id
    dept_id = test_environment["dept_a"].id
    team_id = test_environment["team_a"].id

    # Create low priority ticket first, then critical priority ticket
    t1 = client.post(
        "/api/v1/tickets",
        json={"subject": "Low Priority Cable Check", "description": "Need an extra cable.", "priority": "LOW"},
        headers=student_headers,
    ).json()

    t2 = client.post(
        "/api/v1/tickets",
        json={"subject": "Critical Server Crash", "description": "Exam server down.", "priority": "CRITICAL"},
        headers=student_headers,
    ).json()

    # Route both to Team A
    client.post(
        f"/api/v1/tickets/{t1['id']}/route",
        json={"department_id": dept_id, "support_team_id": team_id, "confirmed_priority": "LOW"},
        headers=helpdesk_headers,
    )
    client.post(
        f"/api/v1/tickets/{t2['id']}/route",
        json={"department_id": dept_id, "support_team_id": team_id, "confirmed_priority": "CRITICAL"},
        headers=helpdesk_headers,
    )

    # Team Lead lists tickets — must be sorted with CRITICAL ahead of LOW
    lead_queue = client.get("/api/v1/tickets", headers=lead_headers).json()
    tkt_ids = [t["id"] for t in lead_queue]
    assert tkt_ids.index(t2["id"]) < tkt_ids.index(t1["id"])

    # Team Lead assigns t2 to engineer
    assign_res = client.post(
        f"/api/v1/tickets/{t2['id']}/assign",
        json={"assigned_engineer_id": engineer_id, "note": "Please prioritize immediately."},
        headers=lead_headers,
    )
    assert assign_res.status_code == 200
    assigned_tkt = assign_res.json()
    assert assigned_tkt["status"] == "ASSIGNED"
    assert assigned_tkt["assigned_engineer_id"] == engineer_id
    assert assigned_tkt["assigned_engineer_name"] == "Evan Engineer"


# ── 6. Solution Helper / Engineer Resolution Tests ─────────────────────────────

def test_engineer_investigation_and_resolution(test_environment):
    eng_headers = test_environment["engineer_a_headers"]
    lead_headers = test_environment["lead_a_headers"]
    student_headers = test_environment["student_a_headers"]
    helpdesk_headers = test_environment["helpdesk_a_headers"]
    engineer_id = test_environment["engineer_a"].id
    dept_id = test_environment["dept_a"].id
    team_id = test_environment["team_a"].id

    # Create & route ticket
    tkt = client.post(
        "/api/v1/tickets",
        json={"subject": "Projector Lamp Burned Out", "description": "Seminar Hall 1 projector dead.", "priority": "HIGH"},
        headers=student_headers,
    ).json()
    tkt_id = tkt["id"]

    client.post(
        f"/api/v1/tickets/{tkt_id}/route",
        json={"department_id": dept_id, "support_team_id": team_id, "confirmed_priority": "HIGH"},
        headers=helpdesk_headers,
    )

    # Assign to engineer
    client.post(
        f"/api/v1/tickets/{tkt_id}/assign",
        json={"assigned_engineer_id": engineer_id},
        headers=lead_headers,
    )

    # Engineer updates status to IN_PROGRESS
    prog_res = client.post(
        f"/api/v1/tickets/{tkt_id}/status",
        json={"status": "IN_PROGRESS", "note": "Replaced projector lamp assembly with spare unit."},
        headers=eng_headers,
    )
    assert prog_res.status_code == 200
    assert prog_res.json()["status"] == "IN_PROGRESS"

    # Engineer marks ticket as RESOLVED
    res_response = client.post(
        f"/api/v1/tickets/{tkt_id}/resolve",
        json={"resolution": "Replaced lamp assembly, tested 4K video input and aligned lens. Fully operational."},
        headers=eng_headers,
    )
    assert res_response.status_code == 200
    resolved_tkt = res_response.json()
    assert resolved_tkt["status"] == "RESOLVED"
    assert resolved_tkt["resolved_at"] is not None

    # Check comments to ensure public resolution note was recorded
    comments = client.get(f"/api/v1/tickets/{tkt_id}/comments", headers=student_headers).json()
    assert any("Replaced lamp assembly" in c["comment"] for c in comments)


# ── 7. Internal Notes vs Public Comments Isolation ─────────────────────────────

def test_internal_staff_notes_invisible_to_users(test_environment):
    student_headers = test_environment["student_a_headers"]
    helpdesk_headers = test_environment["helpdesk_a_headers"]

    # Student creates ticket
    tkt = client.post(
        "/api/v1/tickets",
        json={"subject": "Account Lockout Issue", "description": "Forgot portal password.", "priority": "MEDIUM"},
        headers=student_headers,
    ).json()
    tkt_id = tkt["id"]

    # Help Desk adds an INTERNAL note
    secret_note = "INTERNAL NOTE: Student entered wrong password 10 times. Flagged for review."
    post_internal = client.post(
        f"/api/v1/tickets/{tkt_id}/comments",
        json={"comment": secret_note, "is_internal": True},
        headers=helpdesk_headers,
    )
    assert post_internal.status_code == 201
    assert post_internal.json()["is_internal"] is True

    # Help Desk adds a PUBLIC note
    public_note = "PUBLIC NOTE: Your password reset link has been dispatched to your recovery email."
    client.post(
        f"/api/v1/tickets/{tkt_id}/comments",
        json={"comment": public_note, "is_internal": False},
        headers=helpdesk_headers,
    )

    # Help Desk reads comments — should see BOTH
    hd_comments = client.get(f"/api/v1/tickets/{tkt_id}/comments", headers=helpdesk_headers).json()
    hd_texts = [c["comment"] for c in hd_comments]
    assert secret_note in hd_texts
    assert public_note in hd_texts

    # Student reads comments — MUST NOT see secret note
    user_comments = client.get(f"/api/v1/tickets/{tkt_id}/comments", headers=student_headers).json()
    user_texts = [c["comment"] for c in user_comments]
    assert secret_note not in user_texts
    assert public_note in user_texts

    # User attempts to post with is_internal=True — must be forced to False
    user_post = client.post(
        f"/api/v1/tickets/{tkt_id}/comments",
        json={"comment": "User comment trying to be internal", "is_internal": True},
        headers=student_headers,
    ).json()
    assert user_post["is_internal"] is False
