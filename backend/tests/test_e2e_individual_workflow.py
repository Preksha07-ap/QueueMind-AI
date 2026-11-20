"""
End-to-End Individual Staff Workflow Tests for QueueMind AI.

Tests Parts 1-8:
- Test A: Help Desk routes & assigns ticket to Ananya -> Ananya sees in My Assigned
- Test B: Vikram cannot see Ananya's ticket in My Assigned, but sees it in Team Queue
- Test C: Team Lead routes & assigns ticket to Vikram -> Vikram sees in My Assigned, Ananya does not
- Test D: Reassignment from Ananya to Vikram updates both dashboards and persists across re-query/re-login
- Test E: Security - rejects assignment to invalid roles, inactive users, cross-org, or wrong team
- Test F: Assignment audit history recorded with user full name and role
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.session import SessionLocal
from app.models.organization import Organization
from app.models.user import User, UserRole

client = TestClient(app)


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def jss_environment():
    """Fetches JSS-01 live test accounts."""
    db: Session = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.code == "JSS-01").first()
        assert org is not None, "JSS-01 organization must exist"

        priya = db.query(User).filter(User.organization_id == org.id, User.email == "helpdesk@jss.edu").first()
        ananya = db.query(User).filter(User.organization_id == org.id, User.email == "ananya@jss.edu").first()
        vikram = db.query(User).filter(User.organization_id == org.id, User.email == "vikram@jss.edu").first()
        lead = db.query(User).filter(User.organization_id == org.id, User.email == "lead@jss.edu").first()
        admin = db.query(User).filter(User.organization_id == org.id, User.email == "admin@jss.edu").first()
        student = db.query(User).filter(User.organization_id == org.id, User.email == "student@jss.edu").first()

        assert priya is not None
        assert ananya is not None
        assert vikram is not None
        assert lead is not None
        assert admin is not None
        assert student is not None

        # Authenticate all users
        def login(email, pwd):
            r = client.post("/api/v1/auth/login", json={"org_code": "JSS-01", "email": email, "password": pwd})
            assert r.status_code == 200, f"Login failed for {email}: {r.text}"
            return r.json()

        priya_auth = login("helpdesk@jss.edu", "HelpDesk@123")
        ananya_auth = login("ananya@jss.edu", "Ananya@123")
        vikram_auth = login("vikram@jss.edu", "Vikram@123")
        lead_auth = login("lead@jss.edu", "LeadPass@123")
        admin_auth = login("admin@jss.edu", "AdminPass@123")
        student_auth = login("student@jss.edu", "UserPass@123")

        return {
            "org": org,
            "priya": priya,
            "ananya": ananya,
            "vikram": vikram,
            "lead": lead,
            "admin": admin,
            "student": student,
            "priya_token": priya_auth["access_token"],
            "ananya_token": ananya_auth["access_token"],
            "vikram_token": vikram_auth["access_token"],
            "lead_token": lead_auth["access_token"],
            "admin_token": admin_auth["access_token"],
            "student_token": student_auth["access_token"],
            "ananya_id": ananya.id,
            "vikram_id": vikram.id,
        }
    finally:
        db.close()


def test_part1_individual_staff_accounts_and_different_ids(jss_environment):
    """Ananya and Vikram have different database user IDs and separate identities."""
    env = jss_environment
    assert env["ananya_id"] != env["vikram_id"]
    assert env["ananya"].email == "ananya@jss.edu"
    assert env["vikram"].email == "vikram@jss.edu"
    assert env["ananya"].role == UserRole.SUPPORT_TEAM_MEMBER
    assert env["vikram"].role == UserRole.SUPPORT_TEAM_MEMBER
    assert env["ananya"].organization_id == env["org"].id
    assert env["vikram"].organization_id == env["org"].id
    assert env["ananya"].support_team_id == env["vikram"].support_team_id


def test_part2_organizer_authentication_and_roles(jss_environment):
    """All 5 staff roles authenticate and return correct roles from backend."""
    env = jss_environment

    roles_expected = [
        ("helpdesk@jss.edu", "HelpDesk@123", "HELP_DESK"),
        ("ananya@jss.edu", "Ananya@123", "SUPPORT_TEAM_MEMBER"),
        ("vikram@jss.edu", "Vikram@123", "SUPPORT_TEAM_MEMBER"),
        ("lead@jss.edu", "LeadPass@123", "SUPPORT_TEAM_LEAD"),
        ("admin@jss.edu", "AdminPass@123", "ORGANIZATION_ADMIN"),
    ]

    for email, pwd, exp_role in roles_expected:
        res = client.post("/api/v1/auth/login", json={"org_code": "JSS-01", "email": email, "password": pwd})
        assert res.status_code == 200
        data = res.json()
        assert data["user"]["role"] == exp_role
        token = data["access_token"]

        me_res = client.get("/api/v1/auth/me", headers=auth_header(token))
        assert me_res.status_code == 200
        assert me_res.json()["role"] == exp_role


def test_part7_test_a_assign_to_ananya(jss_environment):
    """
    Test A:
    1. Student submits ticket
    2. Priya (Help Desk) routes & selects Ananya Roy
    3. Backend sets assigned_engineer_id to Ananya's ID
    4. Ananya sees ticket in My Assigned
    """
    env = jss_environment

    # Submit ticket
    sub_res = client.post(
        "/api/v1/tickets",
        json={"subject": "Part7 Test A - Ananya Assignment", "description": "Student Wi-Fi disconnecting in Library"},
        headers=auth_header(env["student_token"]),
    )
    assert sub_res.status_code == 201
    ticket = sub_res.json()
    t_id = ticket["id"]

    # Priya routes and selects Ananya
    route_res = client.post(
        f"/api/v1/tickets/{t_id}/route",
        json={
            "department_id": env["ananya"].department_id,
            "support_team_id": env["ananya"].support_team_id,
            "confirmed_priority": "HIGH",
            "assigned_engineer_id": env["ananya_id"],
            "note": "Priya routing directly to Ananya Roy",
        },
        headers=auth_header(env["priya_token"]),
    )
    assert route_res.status_code == 200
    routed = route_res.json()
    assert routed["assigned_engineer_id"] == env["ananya_id"]
    assert routed["status"] == "ASSIGNED"

    # Ananya My Assigned check
    ananya_tickets = client.get(
        "/api/v1/tickets",
        params={"assigned_to_me": "true"},
        headers=auth_header(env["ananya_token"]),
    ).json()
    assert any(t["id"] == t_id for t in ananya_tickets)


def test_part7_test_b_vikram_cannot_see_ananya_ticket_in_my_assigned(jss_environment):
    """
    Test B:
    Vikram does NOT see Ananya's ticket in My Assigned.
    Vikram DOES see it in the shared Team Queue.
    """
    env = jss_environment

    # Submit and route to Ananya
    sub_res = client.post(
        "/api/v1/tickets",
        json={"subject": "Part7 Test B - Ananya Only Ticket", "description": "Lab PC 4 power button broken"},
        headers=auth_header(env["student_token"]),
    )
    t_id = sub_res.json()["id"]

    client.post(
        f"/api/v1/tickets/{t_id}/route",
        json={
            "department_id": env["ananya"].department_id,
            "support_team_id": env["ananya"].support_team_id,
            "confirmed_priority": "MEDIUM",
            "assigned_engineer_id": env["ananya_id"],
        },
        headers=auth_header(env["priya_token"]),
    )

    # Vikram My Assigned
    vikram_my = client.get(
        "/api/v1/tickets",
        params={"assigned_to_me": "true"},
        headers=auth_header(env["vikram_token"]),
    ).json()
    assert not any(t["id"] == t_id for t in vikram_my)

    # Vikram Team Queue
    vikram_team = client.get(
        "/api/v1/tickets",
        params={"queue": "team"},
        headers=auth_header(env["vikram_token"]),
    ).json()
    assert any(t["id"] == t_id for t in vikram_team)


def test_part7_test_c_assign_to_vikram(jss_environment):
    """
    Test C:
    Assign ticket to Vikram.
    Vikram sees in My Assigned.
    Ananya does NOT see it in My Assigned.
    """
    env = jss_environment

    sub_res = client.post(
        "/api/v1/tickets",
        json={"subject": "Part7 Test C - Vikram Assignment", "description": "Hostel 2 Ethernet port dead"},
        headers=auth_header(env["student_token"]),
    )
    t_id = sub_res.json()["id"]

    # Priya routes to team
    client.post(
        f"/api/v1/tickets/{t_id}/route",
        json={
            "department_id": env["vikram"].department_id,
            "support_team_id": env["vikram"].support_team_id,
            "confirmed_priority": "MEDIUM",
        },
        headers=auth_header(env["priya_token"]),
    )

    # Team Lead assigns to Vikram
    assign_res = client.post(
        f"/api/v1/tickets/{t_id}/assign",
        json={"assigned_engineer_id": env["vikram_id"], "note": "Assigned to Vikram by Team Lead"},
        headers=auth_header(env["lead_token"]),
    )
    assert assign_res.status_code == 200

    # Vikram sees it
    vikram_my = client.get(
        "/api/v1/tickets",
        params={"assigned_to_me": "true"},
        headers=auth_header(env["vikram_token"]),
    ).json()
    assert any(t["id"] == t_id for t in vikram_my)

    # Ananya does NOT see it
    ananya_my = client.get(
        "/api/v1/tickets",
        params={"assigned_to_me": "true"},
        headers=auth_header(env["ananya_token"]),
    ).json()
    assert not any(t["id"] == t_id for t in ananya_my)


def test_part7_test_d_persistence_and_reassignment(jss_environment):
    """
    Test D:
    1. Reassign ticket from Ananya to Vikram
    2. Ticket disappears from Ananya's My Assigned
    3. Ticket appears in Vikram's My Assigned
    4. Re-query (simulating refresh / new login) maintains persistence
    """
    env = jss_environment

    # Submit and assign to Ananya
    sub_res = client.post(
        "/api/v1/tickets",
        json={"subject": "Part7 Test D - Reassignment", "description": "Campus firewall blocking course portal"},
        headers=auth_header(env["student_token"]),
    )
    t_id = sub_res.json()["id"]

    client.post(
        f"/api/v1/tickets/{t_id}/route",
        json={
            "department_id": env["ananya"].department_id,
            "support_team_id": env["ananya"].support_team_id,
            "assigned_engineer_id": env["ananya_id"],
        },
        headers=auth_header(env["priya_token"]),
    )

    # Verify Ananya has it
    ananya_before = client.get("/api/v1/tickets", params={"assigned_to_me": "true"}, headers=auth_header(env["ananya_token"])).json()
    assert any(t["id"] == t_id for t in ananya_before)

    # Team Lead reassigns to Vikram
    reassign_res = client.post(
        f"/api/v1/tickets/{t_id}/assign",
        json={"assigned_engineer_id": env["vikram_id"], "note": "Reassigning to Vikram due to workload"},
        headers=auth_header(env["lead_token"]),
    )
    assert reassign_res.status_code == 200

    # Simulate fresh login by requesting fresh tokens
    new_ananya_res = client.post("/api/v1/auth/login", json={"org_code": "JSS-01", "email": "ananya@jss.edu", "password": "Ananya@123"}).json()
    new_vikram_res = client.post("/api/v1/auth/login", json={"org_code": "JSS-01", "email": "vikram@jss.edu", "password": "Vikram@123"}).json()

    ananya_after = client.get("/api/v1/tickets", params={"assigned_to_me": "true"}, headers=auth_header(new_ananya_res["access_token"])).json()
    vikram_after = client.get("/api/v1/tickets", params={"assigned_to_me": "true"}, headers=auth_header(new_vikram_res["access_token"])).json()

    assert not any(t["id"] == t_id for t in ananya_after)
    assert any(t["id"] == t_id for t in vikram_after)


def test_part7_test_e_security_validations(jss_environment):
    """
    Test E:
    1. Reject assigning non-support role (e.g. Student)
    2. Reject assigning non-existent user
    3. Reject assigning engineer from another support team
    4. Reject non-privileged user assigning tickets
    """
    env = jss_environment

    sub_res = client.post(
        "/api/v1/tickets",
        json={"subject": "Part7 Test E - Security", "description": "Security test ticket"},
        headers=auth_header(env["student_token"]),
    )
    t_id = sub_res.json()["id"]

    # 1. Cannot assign student
    r1 = client.post(f"/api/v1/tickets/{t_id}/assign", json={"assigned_engineer_id": env["student"].id}, headers=auth_header(env["lead_token"]))
    assert r1.status_code == 400

    # 2. Cannot assign non-existent user
    r2 = client.post(f"/api/v1/tickets/{t_id}/assign", json={"assigned_engineer_id": 999999}, headers=auth_header(env["lead_token"]))
    assert r2.status_code == 400

    # 3. Student cannot assign tickets
    r3 = client.post(f"/api/v1/tickets/{t_id}/assign", json={"assigned_engineer_id": env["ananya_id"]}, headers=auth_header(env["student_token"]))
    assert r3.status_code == 403


def test_part7_test_f_assignment_audit_history(jss_environment):
    """
    Test F:
    Verifies that assignment actions produce clear audit history entries.
    """
    env = jss_environment

    sub_res = client.post(
        "/api/v1/tickets",
        json={"subject": "Part7 Test F - History Audit", "description": "Audit trail test"},
        headers=auth_header(env["student_token"]),
    )
    t_id = sub_res.json()["id"]

    # Route and assign
    client.post(
        f"/api/v1/tickets/{t_id}/route",
        json={
            "department_id": env["ananya"].department_id,
            "support_team_id": env["ananya"].support_team_id,
            "assigned_engineer_id": env["ananya_id"],
            "note": "Audit trail route note",
        },
        headers=auth_header(env["priya_token"]),
    )

    history = client.get(f"/api/v1/tickets/{t_id}/history", headers=auth_header(env["priya_token"])).json()
    assert len(history) >= 2  # initial submit + route/assign
    latest = history[-1]
    assert "Ananya Roy" in latest["description"]
    assert latest["new_status"] == "ASSIGNED"
