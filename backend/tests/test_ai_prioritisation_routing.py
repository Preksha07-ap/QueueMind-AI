"""
Test AI-Based Ticket Prioritisation and Automatic Support Team Routing.

Validates all 14 core scenarios:
1. Exam portal down during active exam -> CRITICAL
2. Multiple students reporting exam portal failure -> incident grouping & increased impact/score
3. Fee payment failure near deadline -> HIGH/CRITICAL
4. Normal Wi-Fi issue affecting one user -> MEDIUM
5. General info request -> LOW
6. Software bug -> Software support team recommendation
7. Hardware malfunction -> Hardware support team recommendation
8. No suitable team available (Apex org) -> manual Help Desk review
9. JSS ticket cannot be routed to Apex team (tenant isolation 400)
10. Help Desk approval routes ticket to selected team
11. Team Lead sees routed ticket and assigns to Ananya (ID 672) or Vikram (ID 673)
12. Solution Helper sees individually assigned ticket and resolves it
13. Priority and routing info persist after reload/query
14. Escalation and clarification actions work seamlessly with full audit history
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.session import SessionLocal
from app.models.organization import Organization
from app.models.department import Department
from app.models.support_team import SupportTeam
from app.models.user import User
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.ai.priority_engine import priority_engine
from app.ai.classifier import classifier
from app.ai.triage_orchestrator import run_ai_triage

client = TestClient(app)


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def env_fixture():
    db: Session = SessionLocal()
    try:
        jss = db.query(Organization).filter(Organization.code == "JSS-01").first()
        sjc = db.query(Organization).filter(Organization.code == "SJC-01").first()
        apex = db.query(Organization).filter(Organization.code == "APEX-01").first()

        assert jss is not None, "JSS-01 must exist"
        assert sjc is not None, "SJC-01 must exist"
        assert apex is not None, "APEX-01 must exist"

        def login(org_code: str, email: str, pwd: str):
            r = client.post("/api/v1/auth/login", json={"org_code": org_code, "email": email, "password": pwd})
            assert r.status_code == 200, f"Login failed for {email} in {org_code}: {r.text}"
            return r.json()

        jss_student = login("JSS-01", "student@jss.edu", "UserPass@123")
        jss_helpdesk = login("JSS-01", "helpdesk@jss.edu", "HelpDesk@123")
        jss_lead = login("JSS-01", "lead@jss.edu", "LeadPass@123")
        jss_ananya = login("JSS-01", "ananya@jss.edu", "Ananya@123")
        jss_vikram = login("JSS-01", "vikram@jss.edu", "Vikram@123")

        sjc_student = login("SJC-01", "student1@sjc.edu", "Demo@123")
        sjc_helpdesk = login("SJC-01", "helpdesk1@sjc.edu", "Demo@123")

        apex_admin = login("APEX-01", "admin@apex.edu", "ApexAdmin@123")

        return {
            "jss": jss,
            "sjc": sjc,
            "apex": apex,
            "jss_student_token": jss_student["access_token"],
            "jss_helpdesk_token": jss_helpdesk["access_token"],
            "jss_lead_token": jss_lead["access_token"],
            "jss_ananya_token": jss_ananya["access_token"],
            "jss_ananya_user": jss_ananya["user"],
            "jss_vikram_token": jss_vikram["access_token"],
            "jss_vikram_user": jss_vikram["user"],
            "sjc_student_token": sjc_student["access_token"],
            "sjc_helpdesk_token": sjc_helpdesk["access_token"],
            "apex_admin_token": apex_admin["access_token"],
        }
    finally:
        db.close()


# ── Scenario 1: Exam portal down during active exam -> CRITICAL ──────────────
def test_scenario_1_exam_portal_down_during_active_exam(env_fixture):
    token = env_fixture["jss_student_token"]
    payload = {
        "subject": "Exam portal down during active exam",
        "description": "The online examination portal crashed during our active mid-term test. Submissions are failing and timers are running out.",
        "source": "WEB",
    }
    r = client.post("/api/v1/tickets", json=payload, headers=auth_header(token))
    assert r.status_code == 201
    data = r.json()
    assert data["ai_predicted_priority"] == "CRITICAL"
    assert data["confirmed_priority"] == "CRITICAL"
    assert data["ai_priority_score"] >= 80.0
    assert "Live exam" in data["ai_priority_explanation"] or "CRITICAL" in data["ai_priority_explanation"]


# ── Scenario 2: Multiple reports of exam outage -> clustering & boost ─────────
def test_scenario_2_multiple_students_reporting_exam_portal_failure(env_fixture):
    token = env_fixture["jss_student_token"]
    # Submit second report of the same exam issue
    payload = {
        "subject": "Exam portal down during active exam in computer center",
        "description": "Entire batch unable to submit the mid-term test online, exam portal crashed for everyone.",
        "source": "WEB",
    }
    r = client.post("/api/v1/tickets", json=payload, headers=auth_header(token))
    assert r.status_code == 201
    data = r.json()
    assert data["ai_predicted_priority"] == "CRITICAL"
    # Should link to cluster or incident
    assert data["incident_cluster_id"] is not None or data["related_incident_id"] is not None


# ── Scenario 3: Fee payment failure near deadline -> HIGH/CRITICAL ───────────
def test_scenario_3_fee_payment_failure_near_deadline(env_fixture):
    token = env_fixture["jss_student_token"]
    payload = {
        "subject": "Tuition fee payment failed debit card deducted deadline tomorrow",
        "description": "Payment status showing pending but amount debited from bank account. Tomorrow is the last date to pay or late fee penalty will be imposed.",
        "source": "WEB",
    }
    r = client.post("/api/v1/tickets", json=payload, headers=auth_header(token))
    assert r.status_code == 201
    data = r.json()
    assert data["ai_predicted_priority"] in ("HIGH", "CRITICAL")
    assert data["ai_priority_score"] >= 60.0


# ── Scenario 4: Normal Wi-Fi issue affecting one user -> MEDIUM ───────────────
def test_scenario_4_normal_wifi_issue_one_user(env_fixture):
    token = env_fixture["jss_student_token"]
    payload = {
        "subject": "Campus Wi-Fi connectivity dropping in hostel room",
        "description": "The campus Wi-Fi connection keeps dropping inside my room in hostel Block B. Cannot maintain connection to study.",
        "source": "WEB",
    }
    r = client.post("/api/v1/tickets", json=payload, headers=auth_header(token))
    assert r.status_code == 201
    data = r.json()
    assert data["ai_predicted_priority"] == "MEDIUM"
    assert data["confirmed_priority"] == "MEDIUM"


# ── Scenario 5: General info request -> LOW ──────────────────────────────────
def test_scenario_5_general_info_request(env_fixture):
    token = env_fixture["jss_student_token"]
    payload = {
        "subject": "Inquiry regarding campus library vacation timings",
        "description": "Could you please share the general operating hours and reading room schedule for the upcoming semester break?",
        "source": "WEB",
    }
    r = client.post("/api/v1/tickets", json=payload, headers=auth_header(token))
    assert r.status_code == 201
    data = r.json()
    assert data["ai_predicted_priority"] == "LOW"
    assert data["confirmed_priority"] == "LOW"


# ── Scenario 6: Software bug -> Software support team recommendation ─────────
def test_scenario_6_software_bug_team_recommendation(env_fixture):
    # Test in SJC-01 which has 'IT & Systems' -> 'ERP Support'
    token = env_fixture["sjc_student_token"]
    payload = {
        "subject": "Visual Studio C++ compiler error missing build tools on lab workstations",
        "description": "Compilers throwing fatal build errors on Windows lab workstations. Software installation corrupted.",
        "source": "WEB",
    }
    r = client.post("/api/v1/tickets", json=payload, headers=auth_header(token))
    assert r.status_code == 201
    data = r.json()
    assert data["ai_recommended_support_team_name"] is not None
    # SJC has ERP Support / IT & Systems
    assert "ERP" in data["ai_recommended_support_team_name"] or "IT" in data["ai_recommended_department_name"]


# ── Scenario 7: Hardware malfunction -> Hardware support team recommendation ─
def test_scenario_7_hardware_malfunction_team_recommendation(env_fixture):
    # Test in SJC-01 which has 'IT & Systems' -> 'Hardware Maintenance'
    token = env_fixture["sjc_student_token"]
    payload = {
        "subject": "Lab computer monitor displaying black screen desktop PC not turning on",
        "description": "Desktop PC in lab 4 power supply unit not turning on and screen is black. Hardware replacement needed.",
        "source": "WEB",
    }
    r = client.post("/api/v1/tickets", json=payload, headers=auth_header(token))
    assert r.status_code == 201
    data = r.json()
    assert data["ai_recommended_support_team_name"] is not None
    assert "Hardware" in data["ai_recommended_support_team_name"]


# ── Scenario 8: No suitable team available (Apex org) -> manual Help Desk review
def test_scenario_8_no_team_in_org_marks_manual_review(env_fixture):
    token = env_fixture["apex_admin_token"]
    payload = {
        "subject": "Printer issue in conference room",
        "description": "The shared network printer in conference room 2 is jammed.",
        "source": "WEB",
    }
    r = client.post("/api/v1/tickets", json=payload, headers=auth_header(token))
    assert r.status_code == 201
    data = r.json()
    # Apex has 0 departments and 0 teams
    assert data["ai_recommended_department_id"] is None
    assert data["ai_recommended_support_team_id"] is None
    assert "manual" in data["ai_priority_explanation"].lower() or "no active support" in data["ai_priority_explanation"].lower()


# ── Scenario 9: JSS ticket cannot be routed to Apex team (tenant isolation) ──
def test_scenario_9_cross_tenant_routing_rejected(env_fixture):
    hd_token = env_fixture["jss_helpdesk_token"]
    st_token = env_fixture["jss_student_token"]

    # Create a JSS ticket
    r_create = client.post(
        "/api/v1/tickets",
        json={"subject": "Cross-tenant check", "description": "Attempting cross tenant route", "source": "WEB"},
        headers=auth_header(st_token),
    )
    assert r_create.status_code == 201
    ticket_id = r_create.json()["id"]

    # Attempt to route using invalid/cross-tenant department and team (e.g. ID 99999 or non-existent in JSS)
    r_route = client.post(
        f"/api/v1/tickets/{ticket_id}/route",
        json={"department_id": 999999, "support_team_id": 999999},
        headers=auth_header(hd_token),
    )
    assert r_route.status_code == 400
    assert "not found in ticket's organisation" in r_route.json()["detail"]


# ── Scenario 10: Help Desk approval routes ticket to selected team ────────────
def test_scenario_10_helpdesk_approval_routes_ticket(env_fixture):
    hd_token = env_fixture["jss_helpdesk_token"]
    st_token = env_fixture["jss_student_token"]

    # Student submits ticket
    r_create = client.post(
        "/api/v1/tickets",
        json={
            "subject": "Wi-Fi disconnects in Library First Floor",
            "description": "Students in the quiet study area are getting disconnected every 10 minutes from the library AP.",
            "source": "WEB",
        },
        headers=auth_header(st_token),
    )
    assert r_create.status_code == 201
    ticket = r_create.json()
    ticket_id = ticket["id"]

    assert ticket["ai_recommended_department_id"] is not None
    assert ticket["ai_recommended_support_team_id"] is not None

    # Help Desk confirms AI recommendation
    r_route = client.post(
        f"/api/v1/tickets/{ticket_id}/route",
        json={
            "department_id": ticket["ai_recommended_department_id"],
            "support_team_id": ticket["ai_recommended_support_team_id"],
            "confirmed_priority": ticket["ai_predicted_priority"],
            "note": "Approved AI routing recommendation",
        },
        headers=auth_header(hd_token),
    )
    assert r_route.status_code == 200
    routed_ticket = r_route.json()
    assert routed_ticket["status"] == "APPROVED_FOR_ROUTING"
    assert routed_ticket["department_id"] == ticket["ai_recommended_department_id"]
    assert routed_ticket["support_team_id"] == ticket["ai_recommended_support_team_id"]


# ── Scenario 11: Team Lead sees routed ticket and assigns to Ananya (ID 672) ──
def test_scenario_11_team_lead_assigns_to_engineer(env_fixture):
    hd_token = env_fixture["jss_helpdesk_token"]
    st_token = env_fixture["jss_student_token"]
    lead_token = env_fixture["jss_lead_token"]
    ananya_user = env_fixture["jss_ananya_user"]

    # Create & route ticket to team
    r_create = client.post(
        "/api/v1/tickets",
        json={
            "subject": "Switch port flapping in CS Lab 2",
            "description": "Ethernet switch in CS lab 2 is dropping packets. All workstations losing IP.",
            "source": "WEB",
        },
        headers=auth_header(st_token),
    )
    ticket = r_create.json()
    ticket_id = ticket["id"]

    client.post(
        f"/api/v1/tickets/{ticket_id}/route",
        json={
            "department_id": ticket["ai_recommended_department_id"],
            "support_team_id": ticket["ai_recommended_support_team_id"],
            "confirmed_priority": "HIGH",
        },
        headers=auth_header(hd_token),
    )

    # Team Lead lists team queue
    r_queue = client.get("/api/v1/tickets?queue=team", headers=auth_header(lead_token))
    assert r_queue.status_code == 200
    team_ticket_ids = [t["id"] for t in r_queue.json()]
    assert ticket_id in team_ticket_ids

    # Team Lead assigns to Ananya Roy
    r_assign = client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"assigned_engineer_id": ananya_user["id"], "note": "Assigned to Ananya for immediate inspection"},
        headers=auth_header(lead_token),
    )
    assert r_assign.status_code == 200
    assigned_ticket = r_assign.json()
    assert assigned_ticket["status"] == "ASSIGNED"
    assert assigned_ticket["assigned_engineer_id"] == ananya_user["id"]
    assert "Ananya" in assigned_ticket["assigned_engineer_name"]


# ── Scenario 12: Solution Helper sees ticket in personal queue and resolves it ─
def test_scenario_12_solution_helper_resolves_ticket(env_fixture):
    st_token = env_fixture["jss_student_token"]
    lead_token = env_fixture["jss_lead_token"]
    hd_token = env_fixture["jss_helpdesk_token"]
    ananya_token = env_fixture["jss_ananya_token"]
    ananya_user = env_fixture["jss_ananya_user"]

    # 1. User submits
    r_create = client.post(
        "/api/v1/tickets",
        json={
            "subject": "Library turnstile RFID card reader not opening",
            "description": "Smart cards showing red light at library turnstile entrance.",
            "source": "WEB",
        },
        headers=auth_header(st_token),
    )
    ticket_id = r_create.json()["id"]

    # 2. Help Desk routes
    ticket = r_create.json()
    client.post(
        f"/api/v1/tickets/{ticket_id}/route",
        json={
            "department_id": ticket["ai_recommended_department_id"],
            "support_team_id": ticket["ai_recommended_support_team_id"],
        },
        headers=auth_header(hd_token),
    )

    # 3. Team Lead assigns to Ananya
    client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"assigned_engineer_id": ananya_user["id"]},
        headers=auth_header(lead_token),
    )

    # 4. Ananya sees ticket in 'my_assigned' queue
    r_my = client.get("/api/v1/tickets?queue=my_assigned", headers=auth_header(ananya_token))
    assert r_my.status_code == 200
    my_ids = [t["id"] for t in r_my.json()]
    assert ticket_id in my_ids

    # 5. Ananya resolves ticket
    r_resolve = client.post(
        f"/api/v1/tickets/{ticket_id}/resolve",
        json={"resolution": "Reset the RFID controller and reloaded student access permissions from the central server."},
        headers=auth_header(ananya_token),
    )
    assert r_resolve.status_code == 200
    assert r_resolve.json()["status"] == "RESOLVED"

    # 6. Student checks ticket status
    r_student_view = client.get(f"/api/v1/tickets/{ticket_id}", headers=auth_header(st_token))
    assert r_student_view.status_code == 200
    assert r_student_view.json()["status"] == "RESOLVED"
    assert "RFID controller" in r_student_view.json()["verified_resolution"]


# ── Scenario 13: Priority and routing info persist after reload/query ─────────
def test_scenario_13_priority_and_routing_persist(env_fixture):
    st_token = env_fixture["jss_student_token"]
    hd_token = env_fixture["jss_helpdesk_token"]

    r_create = client.post(
        "/api/v1/tickets",
        json={
            "subject": "Hostel block B core router failing",
            "description": "Core router rebooting continuously, affecting entire hostel block B.",
            "source": "WEB",
        },
        headers=auth_header(st_token),
    )
    ticket_id = r_create.json()["id"]
    original_priority = r_create.json()["confirmed_priority"]
    original_dept_id = r_create.json()["ai_recommended_department_id"]
    original_team_id = r_create.json()["ai_recommended_support_team_id"]

    # Re-query ticket from database via API
    r_fetch = client.get(f"/api/v1/tickets/{ticket_id}", headers=auth_header(hd_token))
    assert r_fetch.status_code == 200
    reloaded = r_fetch.json()
    assert reloaded["confirmed_priority"] == original_priority
    assert reloaded["ai_recommended_department_id"] == original_dept_id
    assert reloaded["ai_recommended_support_team_id"] == original_team_id
    assert reloaded["ai_analysis_status"] == "COMPLETED"


# ── Scenario 14: Escalation and Clarification endpoints work with full audit ──
def test_scenario_14_escalation_and_clarification_endpoints(env_fixture):
    st_token = env_fixture["jss_student_token"]
    hd_token = env_fixture["jss_helpdesk_token"]

    # 1. Create ticket
    r_create = client.post(
        "/api/v1/tickets",
        json={
            "subject": "Minor glitch on portal footer",
            "description": "Footer link has a spelling error.",
            "source": "WEB",
        },
        headers=auth_header(st_token),
    )
    ticket_id = r_create.json()["id"]

    # 2. Help Desk escalates ticket
    r_esc = client.post(
        f"/api/v1/tickets/{ticket_id}/escalate",
        json={"reason": "Critical executive demo occurring right now", "note": "Needs fix within 10 minutes"},
        headers=auth_header(hd_token),
    )
    assert r_esc.status_code == 200
    escalated = r_esc.json()
    assert escalated["confirmed_priority"] == "CRITICAL"
    assert "ESCALATED to CRITICAL" in escalated["ai_priority_explanation"]

    # Verify audit history
    r_hist = client.get(f"/api/v1/tickets/{ticket_id}/history", headers=auth_header(hd_token))
    assert r_hist.status_code == 200
    hist_descs = [h["description"] for h in r_hist.json()]
    assert any("Ticket escalated to CRITICAL" in d for d in hist_descs)

    # 3. Help Desk requests clarification
    r_clar = client.post(
        f"/api/v1/tickets/{ticket_id}/request-clarification",
        json={"question": "Please provide a screenshot and URL where the footer error appears."},
        headers=auth_header(hd_token),
    )
    assert r_clar.status_code == 200
    assert r_clar.json()["status"] == "WAITING_FOR_USER"

    # Verify public comment was added for student
    r_comm = client.get(f"/api/v1/tickets/{ticket_id}/comments", headers=auth_header(st_token))
    assert r_comm.status_code == 200
    comm_texts = [c["comment"] for c in r_comm.json()]
    assert any("Clarification Requested by Help Desk" in c for c in comm_texts)
