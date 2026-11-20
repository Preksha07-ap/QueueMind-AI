"""
Incident Cluster Service for QueueMind AI — Phase 6.

Responsibilities:
  - Create / update incident clusters from duplicate detection results.
  - Count DISTINCT affected users (one user submitting many tickets still = 1 user).
  - Escalate cluster priority when the number of distinct users crosses thresholds.
  - Provide cluster summary for Help Desk, Team Lead and Solution Helper dashboards.
  - Enforce strict tenant isolation on every query.
  - Never delete original tickets — only manages grouping metadata.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from app.models.incident_cluster import IncidentCluster
from app.models.ticket import Ticket, TicketPriority


PRIORITY_ORDER = {
    TicketPriority.CRITICAL: 0,
    TicketPriority.HIGH: 1,
    TicketPriority.MEDIUM: 2,
    TicketPriority.LOW: 3,
}

# Distinct-user escalation thresholds
ESCALATION_RULES = [
    # (min_distinct_users, escalated_priority_str, reason_template)
    (10, "CRITICAL", "10+ distinct users reporting the same incident — organisation-wide impact"),
    (5,  "HIGH",     "{n} distinct users reporting the same incident within the incident window"),
    (3,  "HIGH",     "{n} distinct users reporting the same incident"),
    (2,  "MEDIUM",   "2 distinct users reporting the same issue (potential shared incident)"),
]


def _generate_cluster_number(db: Session, org_id: int) -> str:
    count = db.query(IncidentCluster).filter(IncidentCluster.organization_id == org_id).count()
    candidate = f"INC-{count + 1:05d}"
    attempts = 0
    while db.query(IncidentCluster).filter(
        IncidentCluster.organization_id == org_id,
        IncidentCluster.cluster_number == candidate,
    ).first():
        count += 1
        attempts += 1
        candidate = f"INC-{count + 1:05d}"
        if attempts > 500:
            candidate = f"INC-{int(datetime.now(timezone.utc).timestamp())}"
            break
    return candidate


def _priority_str_to_enum(p: str) -> TicketPriority:
    try:
        return TicketPriority(p.upper())
    except ValueError:
        return TicketPriority.MEDIUM


def _higher_priority(a: str, b: str) -> str:
    """Returns the higher-severity priority string."""
    ea = _priority_str_to_enum(a)
    eb = _priority_str_to_enum(b)
    return a if PRIORITY_ORDER.get(ea, 99) <= PRIORITY_ORDER.get(eb, 99) else b


def get_or_create_cluster(
    db: Session,
    organization_id: int,
    new_ticket: Ticket,
    dup_result: Optional[Dict[str, Any]],
    new_ticket_priority: str,
) -> Optional[IncidentCluster]:
    """
    Called during triage for every new ticket that is a potential duplicate/related.
    - If a cluster already references the primary duplicate ticket, adds the new ticket to it.
    - Otherwise creates a new cluster seeded with the duplicate pair.
    - Counts DISTINCT affected users (by user_id), not raw report count.
    - Escalates cluster priority according to escalation rules.
    - Returns None when no duplicate relationship exists.
    """
    if not dup_result or not dup_result.get("is_duplicate"):
        return None

    primary_ticket_id = dup_result.get("duplicate_ticket_id")
    if not primary_ticket_id:
        return None

    # Collect all related ticket IDs from dup_result
    related_in_result: List[int] = [
        r["ticket_id"] for r in dup_result.get("related_tickets", []) if r.get("ticket_id")
    ]
    all_candidate_ids = list({primary_ticket_id, new_ticket.id} | set(related_in_result))

    # Look for an existing open cluster that contains the primary ticket
    existing: Optional[IncidentCluster] = (
        db.query(IncidentCluster)
        .filter(
            IncidentCluster.organization_id == organization_id,
            IncidentCluster.primary_ticket_id == primary_ticket_id,
            IncidentCluster.status.in_(["OPEN", "INVESTIGATING"]),
        )
        .first()
    )

    if not existing:
        # Also check if the new ticket is already the primary somewhere
        existing = (
            db.query(IncidentCluster)
            .filter(
                IncidentCluster.organization_id == organization_id,
                IncidentCluster.primary_ticket_id == new_ticket.id,
                IncidentCluster.status.in_(["OPEN", "INVESTIGATING"]),
            )
            .first()
        )

    now = datetime.now(timezone.utc)

    if existing:
        # Merge new ticket into existing cluster
        existing_ids: List[int] = []
        try:
            existing_ids = json.loads(existing.related_ticket_ids_json or "[]")
        except Exception:
            existing_ids = []

        merged_ids = list(set(existing_ids + all_candidate_ids))
        existing.related_ticket_ids_json = json.dumps(merged_ids)

        # Count distinct affected users from DB
        distinct_users = _count_distinct_users(db, organization_id, merged_ids)
        existing.distinct_affected_users = distinct_users
        existing.total_reports = len(merged_ids)
        existing.last_reported_at = now
        existing.updated_at = now

        # Recalculate escalated priority
        new_ep, reason = _escalate_priority(
            current_cluster_priority=existing.incident_priority,
            new_ticket_priority=new_ticket_priority,
            distinct_users=distinct_users,
        )
        if new_ep != existing.incident_priority:
            existing.incident_priority = new_ep
            existing.escalation_reason = reason

        # Update category if more specific
        if new_ticket.ai_predicted_category and not existing.category:
            existing.category = new_ticket.ai_predicted_category

        db.flush()
        return existing

    else:
        # Create a new cluster
        cluster_num = _generate_cluster_number(db, organization_id)

        # Determine initial priority
        distinct_users = _count_distinct_users(db, organization_id, all_candidate_ids)
        incident_priority, reason = _escalate_priority(
            current_cluster_priority=new_ticket_priority,
            new_ticket_priority=new_ticket_priority,
            distinct_users=distinct_users,
        )

        # Build a simple issue summary
        summary = _build_issue_summary(new_ticket, dup_result)

        cluster = IncidentCluster(
            organization_id=organization_id,
            primary_ticket_id=primary_ticket_id,
            cluster_number=cluster_num,
            common_issue_summary=summary,
            category=new_ticket.ai_predicted_category,
            incident_priority=incident_priority,
            status="OPEN",
            related_ticket_ids_json=json.dumps(all_candidate_ids),
            distinct_affected_users=distinct_users,
            total_reports=len(all_candidate_ids),
            similarity_score=dup_result.get("similarity_score"),
            first_reported_at=now,
            last_reported_at=now,
            created_at=now,
            updated_at=now,
            escalation_reason=reason if reason else None,
            is_confirmed=False,
        )
        db.add(cluster)
        db.flush()
        return cluster


def _count_distinct_users(db: Session, organization_id: int, ticket_ids: List[int]) -> int:
    """
    Counts the number of DISTINCT user_ids among the given ticket IDs.
    One user submitting 5 tickets still counts as 1 distinct user.
    """
    if not ticket_ids:
        return 0
    rows = (
        db.query(Ticket.user_id)
        .filter(
            Ticket.organization_id == organization_id,
            Ticket.id.in_(ticket_ids),
        )
        .distinct()
        .all()
    )
    return len(rows)


def _escalate_priority(
    current_cluster_priority: str,
    new_ticket_priority: str,
    distinct_users: int,
) -> tuple[str, str]:
    """
    Returns (escalated_priority_str, reason_str).
    Uses the highest of: current cluster priority, new ticket priority, threshold rules.
    """
    base = _higher_priority(current_cluster_priority, new_ticket_priority)

    for min_users, escalated, reason_tpl in ESCALATION_RULES:
        if distinct_users >= min_users:
            reason = reason_tpl.format(n=distinct_users)
            return (_higher_priority(base, escalated), reason)

    return (base, "")


def _build_issue_summary(ticket: Ticket, dup_result: Dict[str, Any]) -> str:
    subject = ticket.subject or ""
    dup_subject = dup_result.get("duplicate_subject", "")
    count = dup_result.get("related_count", 1)
    cat = ticket.ai_predicted_category or "Unknown category"
    if dup_subject and dup_subject.lower() != subject.lower():
        return f"{cat}: Multiple reports — e.g. '{subject[:60]}' and '{dup_subject[:60]}' ({count} related reports)"
    return f"{cat}: Multiple reports of '{subject[:80]}' ({count} related reports)"


def list_clusters_for_org(
    db: Session,
    organization_id: int,
    status_filter: Optional[str] = None,
    limit: int = 50,
) -> List[IncidentCluster]:
    """Returns incident clusters for an organisation, ordered by priority and recency."""
    q = db.query(IncidentCluster).filter(
        IncidentCluster.organization_id == organization_id
    )
    if status_filter:
        q = q.filter(IncidentCluster.status == status_filter)

    from sqlalchemy import case as sa_case
    priority_rank = sa_case(
        (IncidentCluster.incident_priority == "CRITICAL", 1),
        (IncidentCluster.incident_priority == "HIGH", 2),
        (IncidentCluster.incident_priority == "MEDIUM", 3),
        (IncidentCluster.incident_priority == "LOW", 4),
        else_=5,
    )
    return q.order_by(priority_rank.asc(), IncidentCluster.last_reported_at.desc()).limit(limit).all()


def get_cluster_detail(
    db: Session, organization_id: int, cluster_id: int
) -> Optional[IncidentCluster]:
    return (
        db.query(IncidentCluster)
        .filter(
            IncidentCluster.id == cluster_id,
            IncidentCluster.organization_id == organization_id,
        )
        .first()
    )


def get_ticket_cluster(
    db: Session, organization_id: int, ticket_id: int
) -> Optional[IncidentCluster]:
    """Find the cluster that contains the given ticket (as primary or related)."""
    # Check as primary first
    cluster = (
        db.query(IncidentCluster)
        .filter(
            IncidentCluster.organization_id == organization_id,
            IncidentCluster.primary_ticket_id == ticket_id,
        )
        .first()
    )
    if cluster:
        return cluster

    # Scan related_ticket_ids_json (small clusters — acceptable)
    all_clusters = (
        db.query(IncidentCluster)
        .filter(IncidentCluster.organization_id == organization_id)
        .all()
    )
    for c in all_clusters:
        try:
            ids = json.loads(c.related_ticket_ids_json or "[]")
            if ticket_id in ids:
                return c
        except Exception:
            continue
    return None


def confirm_cluster(
    db: Session, organization_id: int, cluster_id: int
) -> Optional[IncidentCluster]:
    cluster = get_cluster_detail(db, organization_id, cluster_id)
    if cluster:
        cluster.is_confirmed = True
        cluster.updated_at = datetime.now(timezone.utc)
        db.flush()
    return cluster


def resolve_cluster(
    db: Session, organization_id: int, cluster_id: int, resolution: str
) -> Optional[IncidentCluster]:
    cluster = get_cluster_detail(db, organization_id, cluster_id)
    if cluster:
        cluster.status = "RESOLVED"
        cluster.verified_resolution = resolution
        cluster.resolved_at = datetime.now(timezone.utc)
        cluster.updated_at = datetime.now(timezone.utc)
        db.flush()
    return cluster


incident_cluster_service = {
    "get_or_create": get_or_create_cluster,
    "list": list_clusters_for_org,
    "detail": get_cluster_detail,
    "ticket_cluster": get_ticket_cluster,
    "confirm": confirm_cluster,
    "resolve": resolve_cluster,
}
