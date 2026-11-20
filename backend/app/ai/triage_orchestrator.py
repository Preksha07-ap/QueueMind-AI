"""
AI Triage Orchestrator for QueueMind AI — Phase 6.

Coordinates:
1. Category Classification (Scikit-learn)
2. Priority Calculation — multi-signal, category is tie-breaker ONLY (Phase 6 fix)
3. Semantic Duplicate Detection + Incident Cluster creation/update
4. Priority re-evaluation using cluster size (distinct affected users)
5. RAG Knowledge Base Retrieval (Organisation-scoped)
6. Historical Incident Intelligence (same org verified resolutions)
7. Ollama Incident Summarisation (when reachable)
8. Department & Support Team Mapping

Guarantees:
- Strict multi-tenant isolation.
- Deterministic priority calculation (never arbitrary LLM outputs).
- Category weight never inflates priority score — severity signals only.
- Graceful degradation if any AI component is offline.
"""

import json
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.ai.classifier import classifier
from app.ai.duplicate_detector import duplicate_detector
from app.ai.historical_intelligence import HistoricalIncidentIntelligence
from app.ai.incident_cluster_service import get_or_create_cluster
from app.ai.ollama_service import ollama_service
from app.ai.priority_engine import priority_engine
from app.ai.rag_retrieval import rag_retriever
from app.models.department import Department
from app.models.issue_category import IssueCategory
from app.models.support_team import SupportTeam
from app.models.ticket import Ticket, TicketStatus


# ── Domain-Aware Department and Support Team Recommendation Engine ─────────
DOMAIN_ROUTING_RULES = [
    {
        "domain": "Examination",
        "keywords": ["exam", "examination", "admit card", "hall ticket", "grade", "marks", "revaluation", "result", "semester exam", "mid-term"],
        "dept_keywords": ["academic", "exam", "examination"],
        "team_keywords": ["exam", "examination cell", "academic support", "evaluat", "examination support"],
    },
    {
        "domain": "Fee and Payment",
        "keywords": ["fee", "payment", "challan", "scholarship", "tuition", "refund", "receipt", "transaction", "gateway", "billing"],
        "dept_keywords": ["finance", "account", "payment", "bursar", "core platform & payment", "billing"],
        "team_keywords": ["fee", "accounts", "payment gateway", "fee & accounts desk", "fee support", "payment"],
    },
    {
        "domain": "Admission",
        "keywords": ["admission", "counseling", "seat allotment", "enrollment", "provisional admission", "branch change", "application status"],
        "dept_keywords": ["admission", "registrar", "enrollment"],
        "team_keywords": ["admission", "admissions support", "counseling", "registrar"],
    },
    {
        "domain": "Network",
        "keywords": ["wifi", "wi-fi", "network", "lan", "ethernet", "router", "vpn", "bandwidth", "firewall", "dns", "captive portal"],
        "dept_keywords": ["it", "network", "system", "infrastructure", "engineering & infrastructure", "devops"],
        "team_keywords": ["network support", "network", "infrastructure", "sre & cloud infra", "platform operations"],
    },
    {
        "domain": "Software",
        "keywords": ["software", "erp", "moodle", "lms", "compiler", "license", "portal error", "visual studio", "office 365", "antivirus", "bug", "crash"],
        "dept_keywords": ["it", "application", "software", "system", "core platform", "engineering"],
        "team_keywords": ["erp support", "application support", "software support", "platform operations", "software"],
    },
    {
        "domain": "Hardware",
        "keywords": ["hardware", "monitor", "pc", "desktop", "projector", "printer", "keyboard", "mouse", "ups", "screen", "smart board", "machine"],
        "dept_keywords": ["hardware", "facility", "facilities", "workplace it", "maintenance", "it"],
        "team_keywords": ["hardware maintenance", "classroom support", "hardware support", "workplace it support", "lab"],
    },
    {
        "domain": "Account & Security",
        "keywords": ["password", "account locked", "2fa", "mfa", "login", "security", "credential", "rfid", "smart card", "identity"],
        "dept_keywords": ["security", "identity", "it security", "devops & security", "it"],
        "team_keywords": ["identity & access management", "security team", "security & iam", "network support", "security"],
    },
    {
        "domain": "Facilities & Other",
        "keywords": ["facility", "facilities", "hostel", "air conditioner", "bus pass", "classroom", "maintenance", "transport", "cleaning"],
        "dept_keywords": ["facility", "facilities", "workplace", "campus", "operations"],
        "team_keywords": ["facilities helpdesk", "maintenance", "operations tech desk", "workplace it support", "transport support"],
    },
]


def resolve_intelligent_routing(
    db: Session,
    org_id: int,
    predicted_category: str,
    subject: str,
    description: str,
    default_dept_name: str,
    default_team_name: str,
) -> Dict[str, Any]:
    """
    Intelligently maps ticket requirements to real database configured departments and teams
    within the specific organisation (strictly tenant-isolated).
    """
    text = f"{predicted_category} {subject} {description}".lower()
    best_domain = DOMAIN_ROUTING_RULES[0]
    best_domain_score = -1

    for rule in DOMAIN_ROUTING_RULES:
        score = sum(1 for kw in rule["keywords"] if kw in text)
        if rule["domain"].lower() in predicted_category.lower():
            score += 5
        if score > best_domain_score:
            best_domain_score = score
            best_domain = rule

    # Query all active departments and teams strictly within the ticket's organisation
    all_depts = db.query(Department).filter(
        Department.organization_id == org_id,
        Department.is_active == True,
    ).all()
    all_teams = db.query(SupportTeam).filter(
        SupportTeam.organization_id == org_id,
        SupportTeam.is_active == True,
    ).all()

    if not all_depts or not all_teams:
        return {
            "department_id": None,
            "department_name": None,
            "support_team_id": None,
            "support_team_name": None,
            "requires_manual_review": True,
            "is_fallback": False,
            "routing_reason": "No active support departments or teams configured in this organisation. Ticket marked for manual Help Desk review.",
            "status_label": "Requires Manual Review",
        }

    dept_by_id = {d.id: d for d in all_depts}
    scored_candidates = []

    for team in all_teams:
        dept = dept_by_id.get(team.department_id)
        if not dept:
            continue
        team_score = 0
        t_name = team.name.lower()
        d_name = dept.name.lower()

        # Score matching keywords for team and dept
        for t_kw in best_domain["team_keywords"]:
            if t_kw in t_name:
                team_score += 10
        for d_kw in best_domain["dept_keywords"]:
            if d_kw in d_name:
                team_score += 5

        # Check classifier default recommendations
        if default_team_name.lower() in t_name:
            team_score += 8
        if default_dept_name.lower().split()[0] in d_name:
            team_score += 4

        scored_candidates.append((team_score, team, dept))

    if not scored_candidates:
        return {
            "department_id": None,
            "department_name": None,
            "support_team_id": None,
            "support_team_name": None,
            "requires_manual_review": True,
            "is_fallback": False,
            "routing_reason": "No active support teams associated with departments in this organisation. Ticket marked for manual Help Desk review.",
            "status_label": "Requires Manual Review",
        }

    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    best_candidate_score, best_team, best_dept = scored_candidates[0]

    if best_candidate_score > 0:
        return {
            "department_id": best_dept.id,
            "department_name": best_dept.name,
            "support_team_id": best_team.id,
            "support_team_name": best_team.name,
            "requires_manual_review": False,
            "is_fallback": False,
            "routing_reason": f"Matched to {best_dept.name} / {best_team.name} based on {best_domain['domain']} requirements.",
            "status_label": "Ready for Routing",
        }
    else:
        # Fallback to closest configured team in this organisation
        return {
            "department_id": best_dept.id,
            "department_name": best_dept.name,
            "support_team_id": best_team.id,
            "support_team_name": best_team.name,
            "requires_manual_review": False,
            "is_fallback": True,
            "routing_reason": f"No dedicated {best_domain['domain']} department/team configured in organisation. Recommended closest available team: {best_team.name} ({best_dept.name}).",
            "status_label": "Ready for Routing",
        }


def run_ai_triage(
    db: Session,
    ticket: Ticket,
    user_category_hint_id: Optional[int] = None,
) -> Dict[str, object]:
    """
    Executes automated triage for an inbound ticket.
    Updates ticket with AI predictions, priority scores, and routing recommendations.
    Never raises an uncaught exception (safely falls back if any component fails).
    """
    try:
        org_id = ticket.organization_id
        subject = ticket.subject
        description = ticket.description

        # ── 1. Classification (Scikit-learn) ──────────────────────────────────
        cls_result = classifier.predict(subject, description)
        predicted_category_name = str(cls_result["predicted_category"])
        category_confidence = float(cls_result["confidence"])
        predicted_subcat = str(cls_result["subcategory"])
        recommended_dept_name = str(cls_result["recommended_department"])
        recommended_team_name = str(cls_result["recommended_support_team"])

        is_low_confidence = category_confidence < 0.45

        # ── 2. Duplicate Detection (strictly within organisation) ─────────────
        # Run BEFORE priority engine so cluster size can feed into score.
        dup_result = duplicate_detector.find_duplicate(
            db=db,
            organization_id=org_id,
            current_ticket_id=ticket.id,
            subject=subject,
            description=description,
        )

        # ── 3. Incident Cluster — create or update ────────────────────────────
        # Use a provisional priority (no cluster context yet) for the first pass
        provisional_priority_eval = priority_engine.evaluate(
            subject=subject,
            description=description,
            predicted_category=predicted_category_name,
            organization_id=org_id,
            created_at=ticket.created_at,
            incident_cluster_size=0,
            distinct_affected_users=0,
        )
        provisional_priority = provisional_priority_eval["calculated_priority"]

        cluster = None
        distinct_users = 0
        cluster_size = 0

        if dup_result and dup_result.get("is_duplicate"):
            cluster = get_or_create_cluster(
                db=db,
                organization_id=org_id,
                new_ticket=ticket,
                dup_result=dup_result,
                new_ticket_priority=provisional_priority.value,
            )
            if cluster:
                cluster_size = cluster.total_reports
                distinct_users = cluster.distinct_affected_users

        # ── 4. Priority Engine — final pass with cluster context ──────────────
        # Category is NOT part of the score — it is a queue tie-breaker only.
        priority_eval = priority_engine.evaluate(
            subject=subject,
            description=description,
            predicted_category=predicted_category_name,
            organization_id=org_id,
            created_at=ticket.created_at,
            incident_cluster_size=cluster_size,
            distinct_affected_users=distinct_users,
        )

        calculated_priority = priority_eval["calculated_priority"]
        priority_score = float(priority_eval["priority_score"])
        impact = str(priority_eval["impact"])
        urgency = str(priority_eval["urgency"])
        priority_explanation = str(priority_eval["explanation"])

        if is_low_confidence:
            priority_explanation += (
                f"\n\n[HUMAN REVIEW REQUIRED]: Classification confidence is {category_confidence * 100:.1f}%. "
                "Help Desk staff must manually verify category and routing before approval."
            )

        # ── 5. Historical Incident Intelligence (same org verified resolutions) ─
        hist_result = HistoricalIncidentIntelligence.analyze_incident(
            db=db,
            organization_id=org_id,
            current_ticket_id=ticket.id,
            subject=subject,
            description=description,
        )

        # ── 6. RAG Document & Resolution Retrieval (within organisation) ──────
        kb_matches = rag_retriever.retrieve_context(
            db=db,
            organization_id=org_id,
            subject=subject,
            description=description,
            limit=3,
        )

        rag_solution = rag_retriever.generate_rag_solution(
            db=db,
            organization_id=org_id,
            subject=subject,
            description=description,
            category=predicted_category_name,
            historical_incident=hist_result,
        )

        # ── 7. Ollama Language Summarisation (if service available) ───────────
        ollama_result = ollama_service.generate_grounded_summary(
            subject=subject,
            description=description,
            category=predicted_category_name,
            priority=calculated_priority.value,
            kb_context=kb_matches,
        )

        # ── 8. Resolve Department & Support Team in Database ──────────────────
        resolved_cat_id: Optional[int] = ticket.category_id

        db_category = (
            db.query(IssueCategory)
            .filter(
                IssueCategory.organization_id == org_id,
                IssueCategory.name.ilike(f"%{predicted_category_name[:12]}%"),
            )
            .first()
        )
        if db_category and not resolved_cat_id:
            resolved_cat_id = db_category.id

        routing_decision = resolve_intelligent_routing(
            db=db,
            org_id=org_id,
            predicted_category=predicted_category_name,
            subject=subject,
            description=description,
            default_dept_name=recommended_dept_name,
            default_team_name=recommended_team_name,
        )

        resolved_dept_id = routing_decision["department_id"]
        resolved_team_id = routing_decision["support_team_id"]

        # ── 9. Build Evidence JSON for Help Desk Inspection ───────────────────
        cluster_summary = None
        if cluster:
            cluster_summary = {
                "cluster_id": cluster.id,
                "cluster_number": cluster.cluster_number,
                "incident_priority": cluster.incident_priority,
                "distinct_affected_users": cluster.distinct_affected_users,
                "total_reports": cluster.total_reports,
                "common_issue_summary": cluster.common_issue_summary,
                "escalation_reason": cluster.escalation_reason,
            }

        evidence_payload = {
            "classification": {
                "predicted_category": predicted_category_name,
                "confidence": category_confidence,
                "subcategory": predicted_subcat,
                "needs_human_review": is_low_confidence,
                "all_scores": cls_result.get("all_scores", {}),
            },
            "priority": {
                "impact": impact,
                "urgency": urgency,
                "priority_score": priority_score,
                "sla_rule": priority_eval.get("sla_rule"),
                "applied_rules": priority_eval.get("applied_rules", []),
                "evidence": priority_eval.get("evidence", []),
                "signals": priority_eval.get("signals", {}),
                "note": "Category weight is a queue tie-breaker only and does not influence the priority score.",
            },
            "routing": {
                "recommended_department_name": routing_decision["department_name"],
                "recommended_support_team_name": routing_decision["support_team_name"],
                "department_id": resolved_dept_id,
                "support_team_id": resolved_team_id,
                "routing_reason": routing_decision["routing_reason"],
                "requires_manual_review": routing_decision["requires_manual_review"],
                "is_fallback": routing_decision["is_fallback"],
                "status_label": routing_decision["status_label"],
            },
            "duplicate": dup_result,
            "incident_cluster": cluster_summary,
            "kb_suggestions": kb_matches,
            "historical_incident": hist_result,
            "rag_solution": rag_solution,
            "ollama": ollama_result,
        }

        # ── 10. Persist Triage Output on Ticket ───────────────────────────────
        ticket.ai_predicted_category = predicted_category_name
        ticket.ai_predicted_priority = calculated_priority
        ticket.ai_priority_score = priority_score
        full_explanation = priority_explanation
        if routing_decision.get("routing_reason"):
            full_explanation = f"{priority_explanation} | Routing: {routing_decision['routing_reason']}"
        ticket.ai_priority_explanation = full_explanation
        ticket.impact = impact
        ticket.urgency = urgency
        ticket.subcategory = predicted_subcat

        if hist_result and hist_result.get("has_historical_match") and hist_result.get("best_match_ticket_id"):
            ticket.related_incident_id = hist_result.get("best_match_ticket_id")

        if cluster:
            ticket.incident_cluster_id = cluster.id

        if not ticket.confirmed_priority:
            ticket.confirmed_priority = calculated_priority

        if not ticket.category_id and resolved_cat_id:
            ticket.category_id = resolved_cat_id

        ticket.ai_recommended_department_id = resolved_dept_id
        ticket.ai_recommended_support_team_id = resolved_team_id

        if dup_result:
            ticket.ai_duplicate_ticket_id = dup_result.get("duplicate_ticket_id")
            ticket.ai_duplicate_score = dup_result.get("similarity_score")

        ticket.ai_confidence_score = category_confidence
        ticket.ai_analysis_status = "COMPLETED"
        ticket.ai_evidence_json = json.dumps(evidence_payload)

        # Status enters Help Desk review queue
        ticket.status = TicketStatus.AWAITING_HELP_DESK_REVIEW

        return evidence_payload

    except Exception as ex:
        # Graceful degradation on failure
        ticket.ai_analysis_status = "FAILED"
        ticket.ai_priority_explanation = f"AI automated analysis failed: {str(ex)}. Ticket routed for manual triage."
        ticket.status = TicketStatus.AWAITING_HELP_DESK_REVIEW
        return {
            "error": str(ex),
            "status": "FAILED",
        }
