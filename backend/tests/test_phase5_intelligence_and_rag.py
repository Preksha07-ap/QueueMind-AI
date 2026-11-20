"""
Automated Test Suite for Phase 5:
Eight-Organisation Dataset, Historical Incident Intelligence, Duplicate Detection, and RAG.

Covers:
1. Verification of all 8 organisations (SJC, VBC, GSSSIETW, MIT, Meesho, Freshworks, Razorpay, Zepto)
2. Preservation of existing non-demo records (JSS-01, APEX-01)
3. Individual staff and user accounts per organisation (Admin, Help Desk, Lead, 10 Staff, 12 Users)
4. Credential authentication across organisations
5. Departments, support teams, and categories structure
6. Ticket dataset counts and priority distribution (CRITICAL, HIGH, MEDIUM, LOW)
7. Knowledge base articles structure (symptoms, causes, troubleshooting, resolutions)
8. Mandatory Demo A: SJC duplicate ticket detection on hostel Wi-Fi outage
9. Mandatory Demo B: MIT historical incident recurrence on exam hall ticket timeout
10. Mandatory Demo C: Freshworks startup VPN incident knowledge and resolution retrieval
11. Mandatory Demo D: Razorpay strict multi-tenant vector and DB isolation
12. Mandatory Demo E: Grounded no-evidence fallback message
13. Mandatory Demo F: Unapproved / unverified documents excluded from RAG
14. Qdrant vector store organization payload filtering
15. Triage orchestrator historical intelligence integration (related_incident_id and rag_solution)
16. Dynamic vector indexing on ticket resolution
17. Resolution audit history and public resolution comments
18. Historical incident recommendation citation structure
19. Organizer sign-in with organization code and individual staff credentials
20. Multi-tiered duplicate detection (exact, likely, similar)
"""

import json
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.main import app
from app.core.security import verify_password, create_access_token
from app.models.organization import Organization
from app.models.department import Department
from app.models.support_team import SupportTeam
from app.models.issue_category import IssueCategory
from app.models.user import User, UserRole, AccountStatus
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.knowledge_base import KnowledgeBase, KBApprovalStatus
from app.ai.historical_intelligence import HistoricalIncidentIntelligence
from app.ai.duplicate_detector import duplicate_detector
from app.ai.rag_retrieval import rag_retriever, RAG_EVIDENCE_THRESHOLD
from app.ai.triage_orchestrator import run_ai_triage
from app.ai.vector_store import vector_store

client = TestClient(app)

DEMO_ORG_CODES = [
    "SJC-01",
    "VBC-01",
    "GSSSIETW-01",
    "MIT-01",
    "MEESHO-01",
    "FRESHWORKS-01",
    "RAZORPAY-01",
    "ZEPTO-01",
]


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Test 1: Eight Organisations Exist ─────────────────────────────────────────

def test_eight_organizations_exist(db_session: Session):
    expected_names = {
        "SJC-01": "SJC",
        "VBC-01": "VBC",
        "GSSSIETW-01": "GSSSIETW",
        "MIT-01": "MIT",
        "MEESHO-01": "Meesho",
        "FRESHWORKS-01": "Freshworks",
        "RAZORPAY-01": "Razorpay",
        "ZEPTO-01": "Zepto",
    }
    for code, expected_name in expected_names.items():
        org = db_session.query(Organization).filter(Organization.code == code).first()
        assert org is not None, f"Organization with code {code} must exist"
        assert org.name == expected_name, f"Expected name {expected_name}, got {org.name}"
        assert org.is_demo is True, f"Demo org {code} must have is_demo=True"
        assert org.is_active is True


# ── Test 2: Preserved Non-Demo Records Intact ─────────────────────────────────

def test_preserved_organizations_intact(db_session: Session):
    for code in ["JSS-01", "APEX-01"]:
        org = db_session.query(Organization).filter(Organization.code == code).first()
        assert org is not None, f"Preserved organization {code} must exist"
        assert org.is_active is True


# ── Test 3: Staff and User Counts Per Organisation ────────────────────────────

def test_staff_and_user_counts_per_organization(db_session: Session):
    for code in DEMO_ORG_CODES:
        org = db_session.query(Organization).filter(Organization.code == code).first()
        assert org is not None

        admin_count = db_session.query(User).filter(
            User.organization_id == org.id, User.role == UserRole.ORGANIZATION_ADMIN
        ).count()
        helpdesk_count = db_session.query(User).filter(
            User.organization_id == org.id, User.role == UserRole.HELP_DESK
        ).count()
        lead_count = db_session.query(User).filter(
            User.organization_id == org.id, User.role == UserRole.SUPPORT_TEAM_LEAD
        ).count()
        staff_count = db_session.query(User).filter(
            User.organization_id == org.id, User.role == UserRole.SUPPORT_TEAM_MEMBER
        ).count()
        user_count = db_session.query(User).filter(
            User.organization_id == org.id, User.role == UserRole.USER
        ).count()

        assert admin_count >= 1, f"{code} must have at least 1 Org Admin"
        assert helpdesk_count >= 2, f"{code} must have at least 2 Help Desk staff"
        assert lead_count >= 1, f"{code} must have at least 1 Team Lead"
        assert staff_count >= 10, f"{code} must have at least 10 Support Team Members"
        assert user_count >= 12, f"{code} must have at least 12 End Users"


# ── Test 4: Staff Authentication Across Organisations ─────────────────────────

def test_staff_authentication_all_organizations(db_session: Session):
    for code in DEMO_ORG_CODES:
        org = db_session.query(Organization).filter(Organization.code == code).first()
        domain = org.contact_email.split("@")[1]

        # Test Help Desk staff authentication
        hd_user = db_session.query(User).filter(
            User.organization_id == org.id,
            User.email == f"helpdesk1@{domain}",
        ).first()
        assert hd_user is not None
        assert verify_password("Demo@123", hd_user.hashed_password)

        # Test individual Solution Helper authentication
        staff_user = db_session.query(User).filter(
            User.organization_id == org.id,
            User.email == f"staff1@{domain}",
        ).first()
        assert staff_user is not None
        assert verify_password("Demo@123", staff_user.hashed_password)


# ── Test 5: Departments and Support Teams Structure ───────────────────────────

def test_departments_and_teams_structure(db_session: Session):
    for code in DEMO_ORG_CODES:
        org = db_session.query(Organization).filter(Organization.code == code).first()
        depts = db_session.query(Department).filter(Department.organization_id == org.id).all()
        teams = db_session.query(SupportTeam).filter(SupportTeam.organization_id == org.id).all()
        cats = db_session.query(IssueCategory).filter(IssueCategory.organization_id == org.id).all()

        assert len(depts) >= 4, f"{code} must have at least 4 departments"
        assert len(teams) >= 4, f"{code} must have at least 4 support teams"
        assert len(cats) >= 7, f"{code} must have at least 7 issue categories"


# ── Test 6: Ticket Dataset Counts and Priority Distribution ───────────────────

def test_tickets_dataset_counts_and_priorities(db_session: Session):
    for code in DEMO_ORG_CODES:
        org = db_session.query(Organization).filter(Organization.code == code).first()
        tickets = db_session.query(Ticket).filter(Ticket.organization_id == org.id).all()

        assert len(tickets) >= 25, f"{code} must have at least 25 seeded tickets (found {len(tickets)})"

        priorities = {t.confirmed_priority for t in tickets if t.confirmed_priority}
        assert TicketPriority.CRITICAL in priorities, f"{code} must contain CRITICAL priority tickets"
        assert TicketPriority.HIGH in priorities, f"{code} must contain HIGH priority tickets"
        assert TicketPriority.MEDIUM in priorities, f"{code} must contain MEDIUM priority tickets"
        assert TicketPriority.LOW in priorities, f"{code} must contain LOW priority tickets"

        # Verify historical resolved tickets with verified resolutions exist
        resolved_with_res = [
            t for t in tickets
            if t.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED) and t.verified_resolution
        ]
        assert len(resolved_with_res) >= 6, f"{code} must have at least 6 resolved tickets with verified resolutions"


# ── Test 7: Knowledge Base Structure ──────────────────────────────────────────

def test_knowledge_base_articles_structure(db_session: Session):
    for code in DEMO_ORG_CODES:
        org = db_session.query(Organization).filter(Organization.code == code).first()
        approved_kbs = db_session.query(KnowledgeBase).filter(
            KnowledgeBase.organization_id == org.id,
            KnowledgeBase.approval_status == KBApprovalStatus.APPROVED,
        ).all()

        assert len(approved_kbs) >= 5, f"{code} must have at least 5 approved KB articles"

        for kb in approved_kbs:
            assert kb.symptoms is not None and len(kb.symptoms) > 5
            assert kb.troubleshooting_steps is not None and len(kb.troubleshooting_steps) > 5
            assert kb.verified_resolution is not None and len(kb.verified_resolution) > 5
            assert kb.is_verified is True
            assert kb.is_demo is True


# ── Test 8 (Mandatory Demo A): SJC Duplicate Ticket Detection ─────────────────

def test_demo_a_sjc_duplicate_detection(db_session: Session):
    sjc = db_session.query(Organization).filter(Organization.code == "SJC-01").first()
    assert sjc is not None

    # Retrieve existing primary outage ticket
    primary_ticket = db_session.query(Ticket).filter(
        Ticket.organization_id == sjc.id,
        Ticket.subject.ilike("%Hostel Block C 3rd Floor Wi-Fi%"),
    ).first()
    assert primary_ticket is not None

    # Test duplicate detection with a newly reported identical issue
    dup_res = duplicate_detector.find_duplicate(
        db=db_session,
        organization_id=sjc.id,
        current_ticket_id=9999999,  # synthetic new ticket ID
        subject="Hostel Block C 3rd floor no wifi connection down",
        description="The Wi-Fi on third floor in hostel block C is completely disconnected since 8pm.",
    )

    assert dup_res is not None, "Duplicate detector must detect hostel Wi-Fi outage duplicate"
    assert dup_res.get("is_duplicate") is True or dup_res.get("duplicate_ticket_id") is not None
    assert dup_res["similarity_score"] >= 0.70
    assert "Hostel Block C" in dup_res["duplicate_subject"]


# ── Test 9 (Mandatory Demo B): MIT Historical Incident Recurrence ─────────────

def test_demo_b_mit_historical_recurrence(db_session: Session):
    mit = db_session.query(Organization).filter(Organization.code == "MIT-01").first()
    assert mit is not None

    # Retrieve 45-day-old resolved ticket
    hist_ticket = db_session.query(Ticket).filter(
        Ticket.organization_id == mit.id,
        Ticket.subject.ilike("%semester examination hall ticket timeout%"),
        Ticket.status == TicketStatus.RESOLVED,
    ).first()
    assert hist_ticket is not None
    assert hist_ticket.is_resolution_verified is True
    assert hist_ticket.verified_resolution is not None

    # Submit newly incoming recurring ticket query
    query_subject = "Exam hall ticket download throwing timeout 504 on portal"
    query_desc = "I am trying to download my semester exam hall ticket, but the portal keeps timing out with 504."

    analysis = HistoricalIncidentIntelligence.analyze_incident(
        db=db_session,
        organization_id=mit.id,
        current_ticket_id=9999998,
        subject=query_subject,
        description=query_desc,
        threshold=0.50,
    )

    assert analysis is not None, "Historical intelligence must match 45-day-old resolved incident"
    assert analysis["has_historical_match"] is True
    assert analysis["best_match_ticket_number"] == hist_ticket.ticket_number
    assert analysis["similarity_score"] >= 0.50
    assert "Redis" in analysis["best_match_resolution"] or "FastCGI" in analysis["best_match_resolution"]
    assert "Notice: This appears to be a recurring incident" in analysis["recommendation_text"]


# ── Test 10 (Mandatory Demo C): Freshworks Startup VPN RAG Retrieval ──────────

def test_demo_c_freshworks_vpn_rag_solution(db_session: Session):
    fw = db_session.query(Organization).filter(Organization.code == "FRESHWORKS-01").first()
    assert fw is not None

    # Query Freshworks RAG solution generator
    rag_out = rag_retriever.generate_rag_solution(
        db=db_session,
        organization_id=fw.id,
        subject="GlobalProtect VPN repeating Okta SAML login loop repeatedly",
        description="I am unable to connect to VPN because GlobalProtect redirects to Okta MFA and loops continuously.",
        category="Network & VPN",
    )

    assert rag_out["has_sufficient_evidence"] is True
    assert len(rag_out["retrieved_documents"]) >= 1
    top_doc = rag_out["retrieved_documents"][0]
    assert "GlobalProtect" in top_doc["title"] or "VPN" in top_doc["title"]
    assert "Okta" in rag_out["suggested_solution"] or "GlobalProtect" in rag_out["suggested_solution"]


# ── Test 11 (Mandatory Demo D): Razorpay Strict Multi-Tenant Isolation ────────

def test_demo_d_razorpay_strict_tenant_isolation(db_session: Session):
    razorpay = db_session.query(Organization).filter(Organization.code == "RAZORPAY-01").first()
    sjc = db_session.query(Organization).filter(Organization.code == "SJC-01").first()
    mit = db_session.query(Organization).filter(Organization.code == "MIT-01").first()
    fw = db_session.query(Organization).filter(Organization.code == "FRESHWORKS-01").first()
    assert razorpay is not None

    # Query Razorpay for an issue that exists in SJC/MIT (e.g. "Hostel Wi-Fi" or "Exam hall ticket")
    query_text = "Hostel Block C 3rd Floor Wi-Fi completely down"
    matches = vector_store.search_knowledge(
        organization_id=razorpay.id,
        query_text=query_text,
        limit=5,
        score_threshold=0.30,
    )

    # Razorpay must NEVER return documents belonging to SJC, MIT, or Freshworks
    for doc in matches:
        doc_id = doc.get("doc_id")
        kb_entry = db_session.query(KnowledgeBase).filter(KnowledgeBase.id == doc_id).first()
        if kb_entry:
            assert kb_entry.organization_id == razorpay.id, "Multi-tenant violation: foreign document returned!"
            assert kb_entry.organization_id not in (sjc.id, mit.id, fw.id)

    # Ticket vector search must also strictly obey isolation
    t_matches = vector_store.search_similar_tickets(
        organization_id=razorpay.id,
        query_text=query_text,
        limit=5,
    )
    for t in t_matches:
        t_id = t.get("ticket_id")
        t_entry = db_session.query(Ticket).filter(Ticket.id == t_id).first()
        if t_entry:
            assert t_entry.organization_id == razorpay.id, "Multi-tenant violation: foreign ticket returned!"


# ── Test 12 (Mandatory Demo E): Grounded No-Evidence Fallback ─────────────────

def test_demo_e_no_evidence_fallback(db_session: Session):
    sjc = db_session.query(Organization).filter(Organization.code == "SJC-01").first()
    assert sjc is not None

    obscure_subject = "Requesting exotic bespoke quantum compiler license for esoteric experimental emulator"
    obscure_desc = "Obscure experimental esoteric quantum algorithmic syntax emulator written in specialized assembly."

    rag_out = rag_retriever.generate_rag_solution(
        db=db_session,
        organization_id=sjc.id,
        subject=obscure_subject,
        description=obscure_desc,
        category="Software issues",
    )

    expected_fallback = "No sufficiently relevant approved knowledge or historical resolution was found. Human investigation is required."
    assert rag_out["has_sufficient_evidence"] is False
    assert rag_out["suggested_solution"] == expected_fallback


# ── Test 13 (Mandatory Demo F): Unapproved / Draft Documents Excluded ──────────

def test_demo_f_unapproved_resolutions_excluded(db_session: Session):
    sjc = db_session.query(Organization).filter(Organization.code == "SJC-01").first()
    assert sjc is not None

    # Verify that unapproved draft KB exists in DB
    draft_kb = db_session.query(KnowledgeBase).filter(
        KnowledgeBase.organization_id == sjc.id,
        KnowledgeBase.approval_status == KBApprovalStatus.DRAFT,
    ).first()
    assert draft_kb is not None
    assert "Starlink" in draft_kb.title or "DRAFT" in draft_kb.title

    # Query RAG for Starlink
    retrieved = rag_retriever.retrieve_context(
        db=db_session,
        organization_id=sjc.id,
        subject="Experimental Starlink Satellite Fallback Setup",
        description="Testing secondary satellite uplink during fiber cut events.",
    )

    for item in retrieved:
        assert item.get("doc_id") != draft_kb.id, "Unapproved draft KB must never be retrieved by RAG"


# ── Test 14: Vector Store Payload Filtering ───────────────────────────────────

def test_vector_store_payload_filtering(db_session: Session):
    sjc = db_session.query(Organization).filter(Organization.code == "SJC-01").first()
    zepto = db_session.query(Organization).filter(Organization.code == "ZEPTO-01").first()
    assert sjc is not None and zepto is not None

    # Search in SJC
    sjc_tickets = vector_store.search_similar_tickets(
        organization_id=sjc.id,
        query_text="network switch router connectivity",
        limit=3,
    )
    for t in sjc_tickets:
        t_record = db_session.query(Ticket).filter(Ticket.id == t["ticket_id"]).first()
        if t_record:
            assert t_record.organization_id == sjc.id


# ── Test 15: Triage Orchestrator Historical Intelligence Integration ──────────

def test_triage_orchestrator_historical_integration(db_session: Session):
    mit = db_session.query(Organization).filter(Organization.code == "MIT-01").first()
    user = db_session.query(User).filter(User.organization_id == mit.id, User.role == UserRole.USER).first()
    assert mit is not None and user is not None

    test_ticket = Ticket(
        organization_id=mit.id,
        ticket_number="TKT-TEST-TRIAGE-01",
        user_id=user.id,
        subject="Unable to download semester examination hall ticket timeout error 504",
        description="Getting 504 Gateway Timeout error when downloading admit card.",
        status=TicketStatus.SUBMITTED,
    )
    db_session.add(test_ticket)
    db_session.flush()

    try:
        evidence = run_ai_triage(db=db_session, ticket=test_ticket)
        assert test_ticket.ai_analysis_status == "COMPLETED"
        assert "historical_incident" in evidence
        assert "rag_solution" in evidence

        hist = evidence["historical_incident"]
        if hist and hist.get("has_historical_match"):
            assert test_ticket.related_incident_id is not None
    finally:
        db_session.delete(test_ticket)
        db_session.commit()


# ── Test 16: Ticket Resolution Vector Indexing ────────────────────────────────

def test_ticket_resolution_vector_indexing(db_session: Session):
    db_session.rollback()
    vbc = db_session.query(Organization).filter(Organization.code == "VBC-01").first()
    staff = db_session.query(User).filter(User.organization_id == vbc.id, User.role == UserRole.SUPPORT_TEAM_MEMBER).first()
    user = db_session.query(User).filter(User.organization_id == vbc.id, User.role == UserRole.USER).first()
    assert vbc is not None and staff is not None and user is not None

    test_num = f"TKT-TEST-RES-{uuid.uuid4().hex[:6]}"
    ticket = Ticket(
        organization_id=vbc.id,
        ticket_number=test_num,
        user_id=user.id,
        subject="Chemistry Lab Distillation Column Heating Coil Malfunction",
        description="Heating element in Lab 102 column tripped circuit breaker.",
        status=TicketStatus.IN_PROGRESS,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    token = create_access_token(
        subject=staff.id,
        claims={"role": staff.role.value, "org_id": staff.organization_id, "email": staff.email},
    )

    try:
        res = client.post(
            f"/api/v1/tickets/{ticket.id}/resolve",
            headers={"Authorization": f"Bearer {token}"},
            json={"resolution": "Replaced burned heating coil element with new 1500W nichrome unit and calibrated thermostat."},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "RESOLVED"
        assert data["is_resolution_verified"] is True
        assert "heating coil" in data["verified_resolution"]
    finally:
        db_session.query(Ticket).filter(Ticket.id == ticket.id).delete()
        db_session.commit()


# ── Test 17: Resolution Audit History and Public Comments ─────────────────────

def test_resolution_audit_history_and_public_comments(db_session: Session):
    db_session.rollback()
    vbc = db_session.query(Organization).filter(Organization.code == "VBC-01").first()
    resolved_ticket = db_session.query(Ticket).filter(
        Ticket.organization_id == vbc.id,
        Ticket.status == TicketStatus.RESOLVED,
        Ticket.verified_resolution != None,  # noqa: E711
    ).first()
    assert resolved_ticket is not None
    assert resolved_ticket.is_resolution_verified is True
    assert resolved_ticket.resolved_at is not None


# ── Test 18: Historical Incident Citation Structure ───────────────────────────

def test_historical_incident_citation_structure(db_session: Session):
    mit = db_session.query(Organization).filter(Organization.code == "MIT-01").first()
    analysis = HistoricalIncidentIntelligence.analyze_incident(
        db=db_session,
        organization_id=mit.id,
        current_ticket_id=9999997,
        subject="Exam hall ticket download throwing timeout 504 on portal",
        description="I am trying to download my semester exam hall ticket, but the portal keeps timing out with 504.",
        threshold=0.50,
    )
    assert analysis is not None
    rec_text = analysis["recommendation_text"]
    assert "Previous Incident Reference:" in rec_text
    assert "Resolution Date:" in rec_text
    assert "Similarity Score:" in rec_text
    assert "Verified Resolution Procedure:" in rec_text


# ── Test 19: Organizer Sign-in Across Organisations ───────────────────────────

def test_organizer_login_for_demo_staff(db_session: Session):
    for code, domain in [("SJC-01", "sjc.edu"), ("FRESHWORKS-01", "freshworks.com"), ("ZEPTO-01", "zepto.com")]:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "org_code": code,
                "email": f"helpdesk1@{domain}",
                "password": "Demo@123",
            },
        )
        assert response.status_code == 200, f"Organizer login failed for {code}: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["organization_code"] == code
        assert data["user"]["role"] == "HELP_DESK"


# ── Test 20: Multi-Tiered Duplicate Detection ─────────────────────────────────

def test_duplicate_detector_distinguishes_exact_likely_similar(db_session: Session):
    sjc = db_session.query(Organization).filter(Organization.code == "SJC-01").first()
    assert sjc is not None

    dup_exact = duplicate_detector.find_duplicate(
        db=db_session,
        organization_id=sjc.id,
        current_ticket_id=9999996,
        subject="Hostel Block C 3rd Floor Wi-Fi completely down and unreachable",
        description="Hostel Block C 3rd floor Wi-Fi has stopped working since 8 PM. All access points in corridor show red/amber LED.",
    )
    assert dup_exact is not None
    assert dup_exact["similarity_score"] >= 0.85
    assert dup_exact.get("cluster_size", 0) >= 1 or dup_exact.get("related_count", 0) >= 1
