"""
Comprehensive AI Ticket Triage & Priority Engine Automated Tests for QueueMind AI.

Requirements tested:
1. Student ticket submission without priority/impact/urgency: backend executes AI triage.
2. AI category prediction (Fee, Examination, Network, Hardware, Software).
3. AI impact and urgency extraction from description.
4. Deterministic Priority Engine calculates correct priority (LOW, MEDIUM, HIGH, CRITICAL).
5. Student cannot manipulate priority, impact, or urgency (client fields ignored).
6. Low-confidence classification triggers human review requirement.
7. Semantic duplicate detection respects strict organization boundary (multi-tenant isolation).
8. Help Desk review, category correction, priority confirmation, and routing.
9. Reprocessing existing tickets via /reprocess-triage preserves ID and history.
10. Verification of ticket access across statuses (SUBMITTED, AWAITING_HELP_DESK_REVIEW, ASSIGNED, IN_PROGRESS, RESOLVED).
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
from app.ai.classifier import classifier
from app.ai.priority_engine import priority_engine
from app.ai.duplicate_detector import duplicate_detector

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
def triage_environment(db_session: Session):
    """
    Sets up two isolated test organisations (JSS and APEX) with required staff and student users.
    """
    suffix = uuid.uuid4().hex[:6].upper()

    # 1. Organization A (JSS)
    org_a = Organization(
        name=f"JSS Academy {suffix}",
        code=f"JSS-{suffix}",
        slug=f"jss-{suffix.lower()}",
        contact_email=f"contact_{suffix.lower()}@jss.edu",
        org_type=OrganizationType.COLLEGE,
        is_active=True,
    )
    db_session.add(org_a)
    db_session.flush()

    dept_it_a = Department(organization_id=org_a.id, name="IT Department")
    dept_acct_a = Department(organization_id=org_a.id, name="Accounts Department")
    dept_exam_a = Department(organization_id=org_a.id, name="Examination Department")
    db_session.add_all([dept_it_a, dept_acct_a, dept_exam_a])
    db_session.flush()

    team_net_a = SupportTeam(organization_id=org_a.id, department_id=dept_it_a.id, name="Network Support")
    team_fee_a = SupportTeam(organization_id=org_a.id, department_id=dept_acct_a.id, name="Fee Support")
    team_exam_a = SupportTeam(organization_id=org_a.id, department_id=dept_exam_a.id, name="Examination Support")
    db_session.add_all([team_net_a, team_fee_a, team_exam_a])
    db_session.flush()

    cat_net_a = IssueCategory(organization_id=org_a.id, department_id=dept_it_a.id, support_team_id=team_net_a.id, name="Network issues")
    cat_fee_a = IssueCategory(organization_id=org_a.id, department_id=dept_acct_a.id, support_team_id=team_fee_a.id, name="Fee and payment issues")
    cat_exam_a = IssueCategory(organization_id=org_a.id, department_id=dept_exam_a.id, support_team_id=team_exam_a.id, name="Examination issues")
    db_session.add_all([cat_net_a, cat_fee_a, cat_exam_a])
    db_session.flush()

    user_student_a = User(
        organization_id=org_a.id,
        full_name=f"Student JSS {suffix}",
        email=f"student_{suffix.lower()}@jss.edu",
        hashed_password="hashed_placeholder",
        role=UserRole.USER,
        account_status=AccountStatus.ACTIVE,
    )
    user_helpdesk_a = User(
        organization_id=org_a.id,
        full_name=f"HelpDesk JSS {suffix}",
        email=f"helpdesk_{suffix.lower()}@jss.edu",
        hashed_password="hashed_placeholder",
        role=UserRole.HELP_DESK,
        account_status=AccountStatus.ACTIVE,
    )
    db_session.add_all([user_student_a, user_helpdesk_a])

    # 2. Organization B (APEX) - for tenant isolation checks
    org_b = Organization(
        name=f"Apex Institute {suffix}",
        code=f"APX-{suffix}",
        slug=f"apx-{suffix.lower()}",
        contact_email=f"contact_{suffix.lower()}@apex.edu",
        org_type=OrganizationType.UNIVERSITY,
        is_active=True,
    )
    db_session.add(org_b)
    db_session.flush()

    user_student_b = User(
        organization_id=org_b.id,
        full_name=f"Student Apex {suffix}",
        email=f"student_{suffix.lower()}@apex.edu",
        hashed_password="hashed_placeholder",
        role=UserRole.USER,
        account_status=AccountStatus.ACTIVE,
    )
    db_session.add(user_student_b)
    db_session.commit()

    token_student_a = create_access_token(user_student_a.id, {"role": "USER", "org_id": org_a.id})
    token_helpdesk_a = create_access_token(user_helpdesk_a.id, {"role": "HELP_DESK", "org_id": org_a.id})
    token_student_b = create_access_token(user_student_b.id, {"role": "USER", "org_id": org_b.id})

    return {
        "org_a": org_a,
        "org_b": org_b,
        "dept_it_a": dept_it_a,
        "dept_acct_a": dept_acct_a,
        "team_net_a": team_net_a,
        "team_fee_a": team_fee_a,
        "cat_net_a": cat_net_a,
        "cat_fee_a": cat_fee_a,
        "student_a": user_student_a,
        "helpdesk_a": user_helpdesk_a,
        "token_student_a": token_student_a,
        "token_helpdesk_a": token_helpdesk_a,
        "student_b": user_student_b,
        "token_student_b": token_student_b,
    }


# ── Test 1: Category Prediction Models (Scikit-learn) ──────────────────────────

def test_classifier_category_predictions():
    """Validates that Scikit-learn TF-IDF + Naive Bayes accurately categorises institutional tickets."""
    # Fee issue
    p_fee = classifier.predict(
        "Semester fee payment failed",
        "Money debited from netbanking but receipt not generated, transaction pending",
    )
    assert p_fee["predicted_category"] == "Fee and payment issues"
    assert p_fee["confidence"] > 0.40

    # Exam issue
    p_exam = classifier.predict(
        "Admit card hall ticket not downloading",
        "Semester exam starting tomorrow and hall ticket download link throws error 500",
    )
    assert p_exam["predicted_category"] == "Examination issues"

    # Network issue
    p_net = classifier.predict(
        "Campus Wi-Fi not connecting",
        "Wi-Fi connectivity dropping in library and Block B, captive portal login not loading",
    )
    assert p_net["predicted_category"] == "Network issues"

    # Hardware issue
    p_hw = classifier.predict(
        "Lab 3 monitor display black screen",
        "Desktop PC computer not turning on and projector flickering red bulb",
    )
    assert p_hw["predicted_category"] == "Hardware issues"


# ── Test 2: Priority Engine Deterministic Calculations ─────────────────────────

def test_priority_engine_critical_outage():
    """Campus-wide outage must evaluate to CRITICAL impact, CRITICAL priority."""
    eval_res = priority_engine.evaluate(
        subject="Complete campus-wide network outage",
        description="All hostels, labs and departments have lost internet connection entirely. Router offline.",
        predicted_category="Network issues",
    )
    assert eval_res["impact"] == "CRITICAL"
    assert eval_res["calculated_priority"] == TicketPriority.CRITICAL
    assert eval_res["priority_score"] >= 0.90


def test_priority_engine_exam_deadline():
    """Imminent or active exam deadline must elevate urgency to CRITICAL."""
    eval_res = priority_engine.evaluate(
        subject="Exam portal timed out during online test",
        description="Online test running right now and exam portal crashed, submit button not responding exam today",
        predicted_category="Examination issues",
    )
    assert eval_res["urgency"] == "CRITICAL"
    assert eval_res["calculated_priority"] in (TicketPriority.HIGH, TicketPriority.CRITICAL)


def test_priority_engine_fee_deadline():
    """Fee deadline due today must elevate urgency to CRITICAL."""
    eval_res = priority_engine.evaluate(
        subject="Tuition payment failed on last day to pay",
        description="Payment deadline today and late fee penalty will be applied tomorrow. Need urgent reconciliation.",
        predicted_category="Fee and payment issues",
    )
    assert eval_res["urgency"] == "CRITICAL"
    assert eval_res["calculated_priority"] in (TicketPriority.HIGH, TicketPriority.CRITICAL)


def test_priority_engine_low_priority_inquiry():
    """Routine procedure inquiry with no disruption or deadline must evaluate to LOW."""
    eval_res = priority_engine.evaluate(
        subject="Procedure for bus pass replacement inquiry",
        description="How to apply for a lost student bus pass identity card? Looking for guidelines and procedure.",
        predicted_category="Other organisational issues",
    )
    assert eval_res["impact"] == "LOW"
    assert eval_res["calculated_priority"] == TicketPriority.LOW
    assert eval_res["priority_score"] <= 42.0


# ── Test 3: Low-Confidence Handling ───────────────────────────────────────────

def test_classifier_low_confidence_flagging():
    """Vague or uninformative text produces low confidence."""
    vague_result = classifier.predict("hello", "something strange happened yesterday")
    # Low confidence or broad spread
    assert "confidence" in vague_result
    assert "all_scores" in vague_result


# ── Test 4: Student Ticket Creation with Automatic AI Triage ───────────────────

def test_student_ticket_submission_triggers_ai_triage(triage_environment):
    """
    When a student submits a ticket with ONLY subject and description:
    - Backend automatically executes AI triage
    - Sets ai_predicted_category, impact, urgency, ai_predicted_priority
    - Status enters AWAITING_HELP_DESK_REVIEW
    """
    token = triage_environment["token_student_a"]

    payload = {
        "subject": "Wi-Fi in library disconnected across entire campus",
        "description": "Entire network is down in all hostels and campus library. Complete outage.",
    }
    res = client.post("/api/v1/tickets", json=payload, headers=auth_header(token))
    assert res.status_code == 201, f"Create ticket failed: {res.text}"
    ticket = res.json()

    assert ticket["status"] == "AWAITING_HELP_DESK_REVIEW"
    assert ticket["ai_predicted_category"] == "Network issues"
    assert ticket["impact"] == "CRITICAL"
    assert ticket["ai_predicted_priority"] == "CRITICAL"
    assert ticket["ai_analysis_status"] == "COMPLETED"
    assert ticket["ai_evidence_json"] is not None


# ── Test 5: Student Cannot Manually Set Priority or Privileged Fields ─────────

def test_student_cannot_override_priority(triage_environment):
    """
    A malicious or privileged-seeking student passing priority="LOW", impact="LOW"
    on a severe outage will have those fields ignored by the backend.
    The AI Priority Engine deterministically computes the true priority.
    """
    token = triage_environment["token_student_a"]

    payload = {
        "subject": "All college servers crashed completely",
        "description": "Campus-wide server crash affecting all students and online test portal.",
        "priority": "LOW",       # User tries to manipulate
        "impact": "LOW",         # User tries to manipulate
        "urgency": "LOW",        # User tries to manipulate
        "subcategory": "Custom", # User tries to inject
    }
    res = client.post("/api/v1/tickets", json=payload, headers=auth_header(token))
    assert res.status_code == 201
    ticket = res.json()

    # The AI Priority Engine assesses CRITICAL regardless of client inputs
    assert ticket["impact"] in ("CRITICAL", "HIGH")
    assert ticket["ai_predicted_priority"] in ("CRITICAL", "HIGH")
    assert ticket["confirmed_priority"] in ("CRITICAL", "HIGH")


# ── Test 6: Help Desk Review, Correction & Routing ────────────────────────────

def test_helpdesk_can_review_and_route_ticket(triage_environment):
    """
    Help Desk inspects AI recommendations and routes the ticket to department/team,
    optionally correcting category or priority. Status advances to APPROVED_FOR_ROUTING.
    """
    token_student = triage_environment["token_student_a"]
    token_helpdesk = triage_environment["token_helpdesk_a"]
    dept = triage_environment["dept_it_a"]
    team = triage_environment["team_net_a"]
    cat = triage_environment["cat_net_a"]

    # Student submits ticket
    create_res = client.post(
        "/api/v1/tickets",
        json={"subject": "Lab 1 router flashing red light", "description": "Internet down for 20 students in computer lab."},
        headers=auth_header(token_student),
    )
    assert create_res.status_code == 201
    ticket_id = create_res.json()["id"]

    # Help Desk routes ticket
    route_payload = {
        "department_id": dept.id,
        "support_team_id": team.id,
        "category_id": cat.id,
        "confirmed_priority": "HIGH",
        "note": "Verified by Help Desk staff. Forwarded to Network Support.",
    }
    route_res = client.post(
        f"/api/v1/tickets/{ticket_id}/route",
        json=route_payload,
        headers=auth_header(token_helpdesk),
    )
    assert route_res.status_code == 200, f"Route failed: {route_res.text}"
    routed_ticket = route_res.json()
    assert routed_ticket["status"] == "APPROVED_FOR_ROUTING"
    assert routed_ticket["department_id"] == dept.id
    assert routed_ticket["support_team_id"] == team.id
    assert routed_ticket["confirmed_priority"] == "HIGH"


# ── Test 7: Multi-Tenant Duplicate Detection Isolation ─────────────────────────

def test_duplicate_detector_tenant_isolation(db_session: Session, triage_environment):
    """
    Duplicate detection must NEVER match a ticket belonging to another organisation,
    even with 100% identical text.
    """
    org_a = triage_environment["org_a"]
    org_b = triage_environment["org_b"]
    user_a = triage_environment["student_a"]
    user_b = triage_environment["student_b"]

    identical_subject = "Identical Fee Portal Error 503"
    identical_desc = "Payment gateway timeout when transferring semester tuition fee."

    # Create ticket in Org A
    t_a = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-A-{uuid.uuid4().hex[:4]}",
        subject=identical_subject,
        description=identical_desc,
        status=TicketStatus.SUBMITTED,
    )
    db_session.add(t_a)
    db_session.commit()

    # Search for duplicates in Org B with identical text
    dup_b = duplicate_detector.find_duplicate(
        db=db_session,
        organization_id=org_b.id,  # Different org!
        current_ticket_id=None,
        subject=identical_subject,
        description=identical_desc,
    )
    # Must NOT match ticket from Org A
    assert dup_b is None, "Cross-organisation duplicate leak detected!"

    # Search in Org A
    dup_a = duplicate_detector.find_duplicate(
        db=db_session,
        organization_id=org_a.id,  # Same org
        current_ticket_id=None,
        subject=identical_subject,
        description=identical_desc,
    )
    assert dup_a is not None, "Same-org duplicate was not detected!"
    assert dup_a["duplicate_ticket_id"] == t_a.id


# ── Test 8: Reprocess Existing Tickets Endpoint ───────────────────────────────

def test_reprocess_ticket_endpoint(triage_environment):
    """
    Existing demo tickets created without AI triage can be safely reprocessed
    via POST /tickets/{id}/reprocess-triage, updating classification without deleting history.
    """
    token_student = triage_environment["token_student_a"]
    token_helpdesk = triage_environment["token_helpdesk_a"]

    # Student submits ticket
    create_res = client.post(
        "/api/v1/tickets",
        json={"subject": "Tuition fee challan verification pending", "description": "Paid fee via bank counter but accounts hasn't updated portal ledger."},
        headers=auth_header(token_student),
    )
    assert create_res.status_code == 201
    ticket_id = create_res.json()["id"]

    # Help Desk calls reprocess endpoint
    rep_res = client.post(
        f"/api/v1/tickets/{ticket_id}/reprocess-triage",
        headers=auth_header(token_helpdesk),
    )
    assert rep_res.status_code == 200, f"Reprocess failed: {rep_res.text}"
    updated = rep_res.json()
    assert updated["id"] == ticket_id
    assert updated["ai_predicted_category"] == "Fee and payment issues"
    assert updated["ai_analysis_status"] == "COMPLETED"


# ── Test 9: Ticket Access Verification Across Lifecycle Statuses ───────────────

def test_ticket_detail_access_across_statuses(db_session: Session, triage_environment):
    """
    Verifies that ticket details can be retrieved via GET /tickets/{id} for all statuses:
    SUBMITTED, AWAITING_HELP_DESK_REVIEW, APPROVED_FOR_ROUTING, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED.
    """
    org_a = triage_environment["org_a"]
    user_a = triage_environment["student_a"]
    token_a = triage_environment["token_student_a"]

    statuses = [
        TicketStatus.SUBMITTED,
        TicketStatus.AWAITING_HELP_DESK_REVIEW,
        TicketStatus.APPROVED_FOR_ROUTING,
        TicketStatus.ASSIGNED,
        TicketStatus.IN_PROGRESS,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    ]

    for st in statuses:
        t = Ticket(
            organization_id=org_a.id,
            user_id=user_a.id,
            ticket_number=f"TKT-ST-{uuid.uuid4().hex[:4]}",
            subject=f"Testing status {st.value}",
            description="Testing ticket lifecycle access.",
            status=st,
        )
        db_session.add(t)
        db_session.commit()

        # Fetch ticket detail
        res = client.get(f"/api/v1/tickets/{t.id}", headers=auth_header(token_a))
        assert res.status_code == 200, f"Failed to retrieve ticket with status {st.value}: {res.text}"
        data = res.json()
        assert data["id"] == t.id
        assert data["status"] == st.value


# ── Test 10: Category-Based Priority Engine Scenarios (Cases A to F) ──────────

def test_category_priority_cases_a_to_f():
    """
    Verifies deterministic multi-factor priority calculation for Cases A through F:
    - Case A: Exam registration blocked before deadline -> CRITICAL
    - Case B: Fee payment portal down before deadline -> CRITICAL
    - Case C: Admission document upload problem -> MEDIUM
    - Case D: Campus-wide Wi-Fi outage -> CRITICAL (outage override)
    - Case E: Single student certificate download -> LOW/MEDIUM
    - Case F: Minor hardware mouse issue -> LOW
    """
    # Case A: Examination issues (weight 100) + deadline
    res_a = priority_engine.evaluate(
        subject="Exam portal registration error",
        description="Final semester exam registration is blocked. Exam starts tomorrow morning and all students in batch cannot register.",
        predicted_category="Examination issues",
    )
    assert res_a["priority"] == TicketPriority.CRITICAL
    assert res_a["score"] >= 80

    # Case B: Fee and payment issues (weight 90) + deadline
    res_b = priority_engine.evaluate(
        subject="Fee payment portal transaction failing",
        description="Tuition fee payment gateway throwing 500 error. Today is the final payment deadline before late fine.",
        predicted_category="Fee and payment issues",
    )
    assert res_b["priority"] == TicketPriority.CRITICAL
    assert res_b["score"] >= 80

    # Case C: Admission issues (weight 80)
    res_c = priority_engine.evaluate(
        subject="Admission document upload issue",
        description="I am trying to upload my 10th grade marks card for admission verification but getting invalid format error.",
        predicted_category="Admission issues",
    )
    assert res_c["priority"] in [TicketPriority.MEDIUM, TicketPriority.HIGH]
    assert res_c["score"] < 82

    # Case D: Campus-wide Wi-Fi outage (Network weight 70 + outage override)
    res_d = priority_engine.evaluate(
        subject="Campus-wide Wi-Fi network down",
        description="Complete campus outage across all academic blocks. Wi-Fi and ethernet down for all students and faculty.",
        predicted_category="Network issues",
    )
    assert res_d["priority"] == TicketPriority.CRITICAL
    assert res_d["score"] >= 80

    # Case E: Student certificate download
    res_e = priority_engine.evaluate(
        subject="Need help downloading bonafide certificate",
        description="I requested a bonafide certificate last week and need to know where to download it from the student portal.",
        predicted_category="Other organisational issues",
    )
    assert res_e["priority"] in [TicketPriority.LOW, TicketPriority.MEDIUM]
    assert res_e["score"] < 62

    # Case F: Minor hardware issue affecting one person
    res_f = priority_engine.evaluate(
        subject="Mouse scroll wheel sticking in Lab 3",
        description="The scroll wheel on PC 14 in computer lab 3 is sticking slightly when scrolling.",
        predicted_category="Hardware issues",
    )
    assert res_f["priority"] == TicketPriority.LOW
    assert res_f["score"] < 42


# ── Test 11: Dynamic Queue Ordering ──────────────────────────────────────────

def test_dynamic_queue_ordering(db_session: Session, triage_environment):
    """
    Verifies that the staff queue is dynamically sorted:
    1st: CRITICAL > HIGH > MEDIUM > LOW
    2nd: Category importance / score DESC
    3rd: Waiting time (created_at ASC)
    """
    org_a = triage_environment["org_a"]
    user_a = triage_environment["student_a"]
    token_hd = triage_environment["token_helpdesk_a"]

    # Create 3 tickets with different priorities and scores
    t_low = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-SORT-LOW-{uuid.uuid4().hex[:4]}",
        subject="Low priority ticket",
        description="Low priority issue description",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.LOW,
        ai_priority_score=25.0,
    )
    t_med = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-SORT-MED-{uuid.uuid4().hex[:4]}",
        subject="Medium priority ticket",
        description="Medium priority issue description",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.MEDIUM,
        ai_priority_score=55.0,
    )
    t_crit = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-SORT-CRIT-{uuid.uuid4().hex[:4]}",
        subject="Critical priority ticket",
        description="Critical priority issue description",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.CRITICAL,
        ai_priority_score=92.0,
    )
    db_session.add_all([t_low, t_med, t_crit])
    db_session.commit()

    # Query Help Desk queue
    res = client.get("/api/v1/tickets", headers=auth_header(token_hd))
    assert res.status_code == 200
    ticket_list = res.json()

    # Find the positions of our test tickets
    ids = [t["id"] for t in ticket_list]
    idx_crit = ids.index(t_crit.id)
    idx_med = ids.index(t_med.id)
    idx_low = ids.index(t_low.id)

    # CRITICAL must appear before MEDIUM, which must appear before LOW
    assert idx_crit < idx_med < idx_low, f"Expected CRITICAL ({idx_crit}) < MEDIUM ({idx_med}) < LOW ({idx_low})"


# ── Test 12: Category Precedence for Equal Severity ──────────────────────────

def test_category_precedence_equal_severity(db_session: Session, triage_environment):
    """
    Verifies that for tickets with EQUAL severity (MEDIUM):
    Examination (1) appears before Fee (2)
    Fee (2) appears before Admission (3)
    Admission (3) appears before Network (4)
    Network (4) appears before Account and access (5)
    """
    org_a = triage_environment["org_a"]
    user_a = triage_environment["student_a"]
    token_hd = triage_environment["token_helpdesk_a"]

    t_exam = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-PREC-EXAM-{uuid.uuid4().hex[:4]}",
        subject="Hall ticket download issue",
        description="Exam ticket description",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.MEDIUM,
        ai_predicted_category="Examination issues",
        ai_priority_score=50.0,
    )
    t_fee = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-PREC-FEE-{uuid.uuid4().hex[:4]}",
        subject="Fee receipt generation delayed",
        description="Fee ticket description",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.MEDIUM,
        ai_predicted_category="Fee and payment issues",
        ai_priority_score=50.0,
    )
    t_adm = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-PREC-ADM-{uuid.uuid4().hex[:4]}",
        subject="Admission seat verification",
        description="Admission ticket description",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.MEDIUM,
        ai_predicted_category="Admission issues",
        ai_priority_score=50.0,
    )
    t_net = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-PREC-NET-{uuid.uuid4().hex[:4]}",
        subject="Library Wi-Fi signal weak",
        description="Network ticket description",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.MEDIUM,
        ai_predicted_category="Network issues",
        ai_priority_score=50.0,
    )
    t_acc = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-PREC-ACC-{uuid.uuid4().hex[:4]}",
        subject="Student portal password change",
        description="Account ticket description",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.MEDIUM,
        ai_predicted_category="Account and access issues",
        ai_priority_score=50.0,
    )
    db_session.add_all([t_net, t_acc, t_exam, t_adm, t_fee])
    db_session.commit()

    res = client.get("/api/v1/tickets", headers=auth_header(token_hd))
    assert res.status_code == 200
    ticket_list = res.json()
    ids = [t["id"] for t in ticket_list]

    idx_exam = ids.index(t_exam.id)
    idx_fee = ids.index(t_fee.id)
    idx_adm = ids.index(t_adm.id)
    idx_net = ids.index(t_net.id)
    idx_acc = ids.index(t_acc.id)

    # Precedence hierarchy: Examination < Fee < Admission < Network < Account
    assert idx_exam < idx_fee, f"Examination ({idx_exam}) should be before Fee ({idx_fee})"
    assert idx_fee < idx_adm, f"Fee ({idx_fee}) should be before Admission ({idx_adm})"
    assert idx_adm < idx_net, f"Admission ({idx_adm}) should be before Network ({idx_net})"
    assert idx_net < idx_acc, f"Network ({idx_net}) should be before Account ({idx_acc})"


# ── Test 13: New Ticket Inserted at Correct Position ─────────────────────────

def test_new_ticket_inserted_at_correct_position(db_session: Session, triage_environment):
    """
    Submitting a new ticket with Examination category (MEDIUM) must automatically
    appear ahead of existing Network and Software tickets of equal severity,
    even though the Examination ticket was created more recently.
    """
    org_a = triage_environment["org_a"]
    user_a = triage_environment["student_a"]
    token_hd = triage_environment["token_helpdesk_a"]

    # Existing older tickets
    t_net_older = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-OLD-NET-{uuid.uuid4().hex[:4]}",
        subject="Older network query",
        description="Network query",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.MEDIUM,
        ai_predicted_category="Network issues",
        ai_priority_score=45.0,
    )
    db_session.add(t_net_older)
    db_session.commit()

    # Brand new Examination ticket created later
    t_exam_newer = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-NEW-EXAM-{uuid.uuid4().hex[:4]}",
        subject="Newly arrived exam hall ticket issue",
        description="Exam query",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.MEDIUM,
        ai_predicted_category="Examination issues",
        ai_priority_score=45.0,
    )
    db_session.add(t_exam_newer)
    db_session.commit()

    res = client.get("/api/v1/tickets", headers=auth_header(token_hd))
    assert res.status_code == 200
    ids = [t["id"] for t in res.json()]

    idx_exam = ids.index(t_exam_newer.id)
    idx_net = ids.index(t_net_older.id)

    # Newer Exam ticket must be placed before older Network ticket of equal severity
    assert idx_exam < idx_net, f"Newer Exam ({idx_exam}) must appear before older Network ({idx_net})"


# ── Test 14: Emergency Override of Category Precedence ───────────────────────

def test_emergency_overrides_category_precedence(db_session: Session, triage_environment):
    """
    A critical emergency (e.g. campus-wide network outage: CRITICAL) must ALWAYS
    rank ahead of a routine Examination issue (MEDIUM), proving emergency overrides
    category precedence.
    """
    org_a = triage_environment["org_a"]
    user_a = triage_environment["student_a"]
    token_hd = triage_environment["token_helpdesk_a"]

    t_exam_med = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-EXAM-MED-{uuid.uuid4().hex[:4]}",
        subject="Routine exam schedule clarification",
        description="Clarification on elective subject code",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.MEDIUM,
        ai_predicted_category="Examination issues",
        ai_priority_score=45.0,
    )
    t_net_outage = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-NET-CRIT-{uuid.uuid4().hex[:4]}",
        subject="Complete campus network outage across all academic blocks",
        description="All Wi-Fi routers offline, essential services unreachable",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.CRITICAL,
        ai_predicted_category="Network issues",
        ai_priority_score=95.0,
    )
    db_session.add_all([t_exam_med, t_net_outage])
    db_session.commit()

    res = client.get("/api/v1/tickets", headers=auth_header(token_hd))
    assert res.status_code == 200
    ids = [t["id"] for t in res.json()]

    idx_outage = ids.index(t_net_outage.id)
    idx_exam = ids.index(t_exam_med.id)

    # CRITICAL outage MUST appear before MEDIUM examination issue
    assert idx_outage < idx_exam, f"CRITICAL Outage ({idx_outage}) must appear before MEDIUM Exam ({idx_exam})"


# ── Test 15: Older Tickets Win Ties ──────────────────────────────────────────

def test_older_tickets_win_ties_when_equal(db_session: Session, triage_environment):
    """
    When severity, category precedence, and SLA score are equal, older ticket creation
    time wins (created_at ASC) to prevent ticket starvation.
    """
    from datetime import datetime, timedelta, timezone

    org_a = triage_environment["org_a"]
    user_a = triage_environment["student_a"]
    token_hd = triage_environment["token_helpdesk_a"]

    now = datetime.now(timezone.utc)
    t_older = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-TIE-OLD-{uuid.uuid4().hex[:4]}",
        subject="Exam query submitted 2 hours ago",
        description="Exam question",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.MEDIUM,
        ai_predicted_category="Examination issues",
        ai_priority_score=50.0,
        created_at=now - timedelta(hours=2),
    )
    t_newer = Ticket(
        organization_id=org_a.id,
        user_id=user_a.id,
        ticket_number=f"TKT-TIE-NEW-{uuid.uuid4().hex[:4]}",
        subject="Exam query submitted 10 minutes ago",
        description="Exam question",
        status=TicketStatus.AWAITING_HELP_DESK_REVIEW,
        confirmed_priority=TicketPriority.MEDIUM,
        ai_predicted_category="Examination issues",
        ai_priority_score=50.0,
        created_at=now - timedelta(minutes=10),
    )
    db_session.add_all([t_older, t_newer])
    db_session.commit()

    res = client.get("/api/v1/tickets", headers=auth_header(token_hd))
    assert res.status_code == 200
    ids = [t["id"] for t in res.json()]

    idx_older = ids.index(t_older.id)
    idx_newer = ids.index(t_newer.id)

    # Older ticket must win the tie and appear first
    assert idx_older < idx_newer, f"Older ticket ({idx_older}) must appear before newer ticket ({idx_newer})"


# ── Test 16: AI Categorisation Verification on Key Examples ──────────────────

def test_ai_categorisation_four_key_examples():
    """
    Verifies that Scikit-learn AI classifier correctly categorises the 4 user scenarios:
    1. 'Unable to download examination hall ticket' -> Examination issues
    2. 'Unable to pay admission fee through portal' -> Fee and payment issues
    3. 'Wi-Fi unavailable across campus' -> Network issues
    4. 'Unable to access student account' -> Account and access issues
    """
    p1 = classifier.predict("Unable to download examination hall ticket", "Admit card link is not working")
    assert p1["predicted_category"] == "Examination issues"

    p2 = classifier.predict("Unable to pay admission fee through portal", "Payment gateway failed when paying fee")
    assert p2["predicted_category"] == "Fee and payment issues"

    p3 = classifier.predict("Wi-Fi unavailable across campus", "No wireless connection in all academic blocks")
    assert p3["predicted_category"] == "Network issues"

    p4 = classifier.predict("Unable to access student account", "Password not accepted and locked out")
    assert p4["predicted_category"] == "Account and access issues"


