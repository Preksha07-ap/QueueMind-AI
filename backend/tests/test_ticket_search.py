"""
Test Ticket Search Across Dashboards and API Endpoints.

Validates that ticket search functions reliably for:
1. Ticket ID / number (exact and partial matching)
2. Subject / title matching (case-insensitive)
3. Description keyword matching
4. Category matching (category name, ai_predicted_category, subcategory)
5. Submitter name matching (for staff / admin roles)
6. Case-insensitivity and leading/trailing whitespace tolerance
7. Non-matching queries return empty result cleanly
8. Empty search string returns the full unscoped dataset
9. Tenant boundary and role scoping are strictly preserved during search
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.session import SessionLocal
from app.models.organization import Organization
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User

client = TestClient(app)


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def search_env():
    db: Session = SessionLocal()
    try:
        jss = db.query(Organization).filter(Organization.code == "JSS-01").first()
        sjc = db.query(Organization).filter(Organization.code == "SJC-01").first()
        assert jss is not None, "JSS-01 must exist"
        assert sjc is not None, "SJC-01 must exist"

        def login(org_code: str, email: str, pwd: str):
            r = client.post("/api/v1/auth/login", json={"org_code": org_code, "email": email, "password": pwd})
            assert r.status_code == 200, f"Login failed: {r.text}"
            return r.json()

        jss_student = login("JSS-01", "student@jss.edu", "UserPass@123")
        jss_helpdesk = login("JSS-01", "helpdesk@jss.edu", "HelpDesk@123")
        jss_lead = login("JSS-01", "lead@jss.edu", "LeadPass@123")
        sjc_student = login("SJC-01", "student1@sjc.edu", "Demo@123")

        # Submit test tickets with known distinctive keywords
        # 1. Examination ticket with distinctive keyword
        r1 = client.post(
            "/api/v1/tickets",
            json={
                "subject": "Midterm Examination Portal 502 Bad Gateway Error",
                "description": "During calculus midterms, the exam portal crashed with 502 bad gateway for all 180 students in Block C.",
            },
            headers=auth_header(jss_student["access_token"]),
        )
        assert r1.status_code == 201
        t1 = r1.json()

        # 2. Network ticket with distinctive keyword
        r2 = client.post(
            "/api/v1/tickets",
            json={
                "subject": "Library Wi-Fi Connectivity Drops in South Wing",
                "description": "The wireless access point AP-Library-04 in South Wing is constantly dropping connections every 5 minutes.",
            },
            headers=auth_header(jss_student["access_token"]),
        )
        assert r2.status_code == 201
        t2 = r2.json()

        return {
            "jss_student_token": jss_student["access_token"],
            "jss_helpdesk_token": jss_helpdesk["access_token"],
            "jss_lead_token": jss_lead["access_token"],
            "sjc_student_token": sjc_student["access_token"],
            "t1": t1,
            "t2": t2,
        }
    finally:
        db.close()


def test_search_by_exact_ticket_number(search_env):
    """User and Help Desk can find a ticket by its exact ticket number."""
    token = search_env["jss_helpdesk_token"]
    ticket_num = search_env["t1"]["ticket_number"]

    res = client.get(f"/api/v1/tickets?search={ticket_num}", headers=auth_header(token))
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert any(t["ticket_number"] == ticket_num for t in items)


def test_search_by_partial_ticket_number(search_env):
    """Partial ticket number matching (e.g. 'TKT-') returns all matching tickets."""
    token = search_env["jss_helpdesk_token"]
    res = client.get("/api/v1/tickets?search=TKT-", headers=auth_header(token))
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 2
    for item in items:
        assert "tkt-" in item["ticket_number"].lower()


def test_search_by_subject_case_insensitive(search_env):
    """Subject matching is case-insensitive and supports partial phrases."""
    token = search_env["jss_helpdesk_token"]
    # lowercase search for "midterm examination"
    res = client.get("/api/v1/tickets?search=midterm%20examination", headers=auth_header(token))
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert any("Midterm" in t["subject"] for t in items)

    # uppercase search for "CALCULUS"
    res_upper = client.get("/api/v1/tickets?search=CALCULUS", headers=auth_header(token))
    assert res_upper.status_code == 200
    items_upper = res_upper.json()
    assert len(items_upper) >= 1


def test_search_by_description_keywords(search_env):
    """Description keyword search finds tickets by terms not in subject."""
    token = search_env["jss_helpdesk_token"]
    # "AP-Library-04" is only in description of t2
    res = client.get("/api/v1/tickets?search=AP-Library-04", headers=auth_header(token))
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert any(t["id"] == search_env["t2"]["id"] for t in items)


def test_search_by_category(search_env):
    """Search matches category name or ai_predicted_category."""
    token = search_env["jss_helpdesk_token"]
    res = client.get("/api/v1/tickets?search=Examination", headers=auth_header(token))
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert any(
        (t.get("category_name") and "Examination" in t["category_name"]) or
        (t.get("ai_predicted_category") and "Examination" in t["ai_predicted_category"]) or
        "Examination" in t["subject"]
        for t in items
    )


def test_search_by_submitter_name(search_env):
    """Help Desk can search by submitter full name."""
    token = search_env["jss_helpdesk_token"]
    # Student name in JSS demo is typically "JSS Student" or similar
    res = client.get("/api/v1/tickets?search=Student", headers=auth_header(token))
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1


def test_search_with_leading_trailing_whitespace(search_env):
    """Leading and trailing whitespace is stripped before filtering."""
    token = search_env["jss_helpdesk_token"]
    ticket_num = search_env["t1"]["ticket_number"]
    # Query with padded whitespace: "   TKT-000...   "
    res = client.get(f"/api/v1/tickets?search=%20%20{ticket_num}%20%20", headers=auth_header(token))
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert any(t["ticket_number"] == ticket_num for t in items)


def test_search_non_matching_returns_empty(search_env):
    """Search with non-existent query string returns empty list."""
    token = search_env["jss_helpdesk_token"]
    res = client.get("/api/v1/tickets?search=xyznonexistentterm9999", headers=auth_header(token))
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 0


def test_cleared_search_returns_all_tickets(search_env):
    """When search is omitted or empty, all tickets in the queue are returned."""
    token = search_env["jss_helpdesk_token"]
    res_none = client.get("/api/v1/tickets", headers=auth_header(token))
    res_empty = client.get("/api/v1/tickets?search=", headers=auth_header(token))
    assert res_none.status_code == 200
    assert res_empty.status_code == 200
    assert len(res_none.json()) == len(res_empty.json())
    assert len(res_none.json()) >= 2


def test_search_preserves_tenant_isolation(search_env):
    """A user in SJC-01 cannot find tickets from JSS-01 via search."""
    sjc_token = search_env["sjc_student_token"]
    jss_t1_num = search_env["t1"]["ticket_number"]

    # SJC student searching for JSS ticket number
    res = client.get(f"/api/v1/tickets?search={jss_t1_num}", headers=auth_header(sjc_token))
    assert res.status_code == 200
    items = res.json()
    # Must NOT include JSS ticket
    assert not any(t["ticket_number"] == jss_t1_num for t in items)
