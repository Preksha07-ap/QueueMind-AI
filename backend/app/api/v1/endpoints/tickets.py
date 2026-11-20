"""
Ticket Management API Endpoints for QueueMind AI.

Supports complete ticket lifecycle:
Creation → Help Desk Review & Routing → Team Lead Assignment → Engineer Resolution → Comments & History.
Enforces multi-tenancy and role-based permissions on every action.
"""

from datetime import datetime, timezone
import os
import shutil
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.core.category_config import build_category_rank_sql

from app.ai.triage_orchestrator import run_ai_triage
from app.api.deps import (
    get_current_active_user,
    get_current_user,
    require_role,
    verify_tenant_access,
)
from app.database.session import get_db
from app.models.department import Department
from app.models.issue_category import IssueCategory
from app.models.organization import Organization
from app.models.support_team import SupportTeam
from app.models.ticket import Ticket, TicketPriority, TicketSource, TicketStatus
from app.models.ticket_attachment import TicketAttachment
from app.models.ticket_comment import TicketComment
from app.models.ticket_history import TicketHistory
from app.models.user import AccountStatus, User, UserRole
from app.schemas.ticket import (
    AttachmentResponse,
    CommentCreate,
    CommentResponse,
    HistoryResponse,
    TicketAssignRequest,
    TicketClarificationRequest,
    TicketCreate,
    TicketEscalateRequest,
    TicketResolveRequest,
    TicketResponse,
    TicketRouteRequest,
    TicketStatusUpdateRequest,
    TicketUpdate,
)

router = APIRouter()


def generate_ticket_number(db: Session, organization_id: int) -> str:
    """Generates a human-friendly unique ticket identifier per organisation."""
    count = db.query(Ticket).filter(Ticket.organization_id == organization_id).count()
    candidate = f"TKT-{count + 1:05d}"
    attempts = 0
    while db.query(Ticket).filter(
        Ticket.organization_id == organization_id,
        Ticket.ticket_number == candidate
    ).first():
        count += 1
        attempts += 1
        candidate = f"TKT-{count + 1:05d}"
        if attempts > 500:
            candidate = f"TKT-{int(datetime.now(timezone.utc).timestamp())}"
            break
    return candidate


def _build_ticket_response(ticket: Ticket) -> TicketResponse:
    """Transforms a Ticket ORM entity into TicketResponse with resolved relationship names."""
    sub_name = ticket.submitted_by.full_name if ticket.submitted_by else None
    sub_email = ticket.submitted_by.email if ticket.submitted_by else None
    cat_name = ticket.category.name if ticket.category else None
    dept_name = ticket.department.name if ticket.department else None
    team_name = ticket.support_team.name if ticket.support_team else None
    eng_name = ticket.assigned_engineer.full_name if ticket.assigned_engineer else None
    ai_rec_dept = ticket.ai_recommended_department.name if ticket.ai_recommended_department else None
    ai_rec_team = ticket.ai_recommended_support_team.name if ticket.ai_recommended_support_team else None

    return TicketResponse(
        id=ticket.id,
        organization_id=ticket.organization_id,
        ticket_number=ticket.ticket_number,
        user_id=ticket.user_id,
        submitted_by_name=sub_name,
        submitted_by_email=sub_email,
        category_id=ticket.category_id,
        category_name=cat_name,
        subcategory=ticket.subcategory,
        subject=ticket.subject,
        description=ticket.description,
        source=ticket.source,
        ai_predicted_category=ticket.ai_predicted_category,
        ai_predicted_priority=ticket.ai_predicted_priority,
        ai_priority_score=ticket.ai_priority_score,
        ai_priority_explanation=ticket.ai_priority_explanation,
        ai_recommended_department_id=ticket.ai_recommended_department_id,
        ai_recommended_department_name=ai_rec_dept,
        ai_recommended_support_team_id=ticket.ai_recommended_support_team_id,
        ai_recommended_support_team_name=ai_rec_team,
        ai_duplicate_ticket_id=ticket.ai_duplicate_ticket_id,
        ai_duplicate_score=ticket.ai_duplicate_score,
        ai_analysis_status=ticket.ai_analysis_status,
        ai_confidence_score=ticket.ai_confidence_score,
        ai_evidence_json=ticket.ai_evidence_json,
        confirmed_priority=ticket.confirmed_priority,
        department_id=ticket.department_id,
        department_name=dept_name,
        support_team_id=ticket.support_team_id,
        support_team_name=team_name,
        assigned_engineer_id=ticket.assigned_engineer_id,
        assigned_engineer_name=eng_name,
        status=ticket.status,
        impact=ticket.impact,
        urgency=ticket.urgency,
        related_incident_id=ticket.related_incident_id,
        incident_cluster_id=ticket.incident_cluster_id,
        verified_resolution=ticket.verified_resolution,
        is_resolution_verified=ticket.is_resolution_verified,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        comments_count=len(ticket.comments) if ticket.comments else 0,
        attachments_count=len(ticket.attachments) if ticket.attachments else 0,
    )


def _check_ticket_access(ticket: Ticket, current_user: User) -> None:
    """Verifies tenant isolation and role scoping for a single ticket."""
    if current_user.role == UserRole.PLATFORM_OWNER:
        return

    # Check organisation boundary
    if ticket.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to ticket from another organisation is forbidden",
        )

    # USER role can only see their own tickets
    if current_user.role == UserRole.USER and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are only authorized to access your own submitted tickets",
        )


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ticket",
)
def create_ticket(
    req: TicketCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    """
    Submits a new issue ticket.
    Assigns status SUBMITTED, generates an organisation-scoped ticket number,
    and writes the initial audit record to ticket_history.
    """
    org_id = current_user.organization_id
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an active organisation to submit tickets",
        )

    # Validate category belongs to this organisation if supplied
    if req.category_id:
        category = (
            db.query(IssueCategory)
            .filter(
                IssueCategory.id == req.category_id,
                IssueCategory.organization_id == org_id,
            )
            .first()
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected category does not exist in your organisation",
            )

    ticket_num = generate_ticket_number(db, org_id)

    # Regular users (students) cannot set priority, impact, or urgency directly
    # The AI priority engine deterministically assesses evidence and calculates priority
    is_user_role = current_user.role == UserRole.USER

    initial_impact = None if is_user_role else req.impact
    initial_urgency = None if is_user_role else req.urgency
    initial_priority = None if is_user_role else req.priority

    new_ticket = Ticket(
        organization_id=org_id,
        ticket_number=ticket_num,
        user_id=current_user.id,
        category_id=req.category_id,
        subcategory=None if is_user_role else (req.subcategory.strip() if req.subcategory else None),
        subject=req.subject.strip(),
        description=req.description.strip(),
        source=req.source,
        confirmed_priority=initial_priority,
        status=TicketStatus.SUBMITTED,
        impact=initial_impact,
        urgency=initial_urgency,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(new_ticket)
    db.flush()

    # Create initial ticket history entry
    initial_history = TicketHistory(
        organization_id=org_id,
        ticket_id=new_ticket.id,
        previous_status=None,
        new_status=TicketStatus.SUBMITTED,
        changed_by_user_id=current_user.id,
        description="Ticket created and submitted by user",
        created_at=datetime.now(timezone.utc),
    )
    db.add(initial_history)

    # Optional initial attachment references
    if req.attachment_names:
        for fname in req.attachment_names:
            att = TicketAttachment(
                organization_id=org_id,
                ticket_id=new_ticket.id,
                file_name=fname,
                file_url=f"/uploads/{org_id}/{new_ticket.id}/{fname}",
                file_size=1024,
                content_type="application/octet-stream",
                uploaded_by_user_id=current_user.id,
                created_at=datetime.now(timezone.utc),
            )
            db.add(att)

    # Run AI Automated Triage Pipeline
    run_ai_triage(db, new_ticket, user_category_hint_id=req.category_id)

    # Record triage audit in history
    pred_priority_str = new_ticket.ai_predicted_priority.value if new_ticket.ai_predicted_priority else 'PENDING'
    triage_hist = TicketHistory(
        organization_id=org_id,
        ticket_id=new_ticket.id,
        previous_status=TicketStatus.SUBMITTED,
        new_status=new_ticket.status,
        changed_by_user_id=None,
        description=(
            f"AI automated triage completed: Predicted Category '{new_ticket.ai_predicted_category}', "
            f"Calculated Priority '{pred_priority_str}'. "
            f"Awaiting Help Desk review."
        ),
        created_at=datetime.now(timezone.utc),
    )
    db.add(triage_hist)

    db.commit()
    db.refresh(new_ticket)
    return _build_ticket_response(new_ticket)


@router.get(
    "",
    response_model=List[TicketResponse],
    summary="List tickets with role-aware and tenant scoping",
)
def list_tickets(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Optional[TicketStatus] = Query(None, alias="status"),
    priority_filter: Optional[TicketPriority] = Query(None, alias="priority"),
    assigned_to_me: Optional[bool] = Query(None),
    queue: Optional[str] = Query(None, description="Queue filter: 'incoming', 'my_assigned', 'team'"),
    search: Optional[str] = Query(None),
) -> List[TicketResponse]:
    """
    Returns tickets according to user role and tenant constraints:
    - USER: sees only tickets submitted by them.
    - HELP_DESK: sees all tickets in their organisation.
    - SUPPORT_TEAM_MEMBER: sees tickets in their team/department or assigned to them.
    - SUPPORT_TEAM_LEAD: sees team tickets sorted by priority and arrival.
    - ORGANIZATION_ADMIN: sees all tickets in their organisation.
    - PLATFORM_OWNER: sees all tickets globally.
    """
    query = db.query(Ticket)

    # 1. Tenant Scoping
    if current_user.role != UserRole.PLATFORM_OWNER:
        query = query.filter(Ticket.organization_id == current_user.organization_id)

    # 2. Role Scoping
    if current_user.role == UserRole.USER:
        query = query.filter(Ticket.user_id == current_user.id)

    elif current_user.role == UserRole.SUPPORT_TEAM_MEMBER:
        if assigned_to_me:
            query = query.filter(Ticket.assigned_engineer_id == current_user.id)
        elif queue == "my_assigned":
            query = query.filter(Ticket.assigned_engineer_id == current_user.id)
        elif queue == "team":
            # Strict team queue: only tickets routed to this engineer's team or department
            conditions = []
            if current_user.support_team_id:
                conditions.append(Ticket.support_team_id == current_user.support_team_id)
            elif current_user.department_id:
                conditions.append(Ticket.department_id == current_user.department_id)
            if conditions:
                query = query.filter(or_(*conditions))
            else:
                query = query.filter(Ticket.id == -1)
        else:
            # Show tickets assigned to this engineer OR tickets routed to their team
            conditions = [Ticket.assigned_engineer_id == current_user.id]
            if current_user.support_team_id:
                conditions.append(Ticket.support_team_id == current_user.support_team_id)
            elif current_user.department_id:
                conditions.append(Ticket.department_id == current_user.department_id)
            query = query.filter(or_(*conditions))

    elif current_user.role == UserRole.SUPPORT_TEAM_LEAD:
        if current_user.support_team_id:
            query = query.filter(Ticket.support_team_id == current_user.support_team_id)
        elif current_user.department_id:
            query = query.filter(Ticket.department_id == current_user.department_id)

    # 3. Parameter Filters
    if status_filter:
        if status_filter == TicketStatus.SUBMITTED:
            query = query.filter(
                or_(
                    Ticket.status == TicketStatus.SUBMITTED,
                    Ticket.status == TicketStatus.AWAITING_HELP_DESK_REVIEW,
                )
            )
        else:
            query = query.filter(Ticket.status == status_filter)

    if priority_filter:
        query = query.filter(Ticket.confirmed_priority == priority_filter)

    # Outerjoin category and submitter for search and ranking
    query = query.outerjoin(IssueCategory, Ticket.category_id == IssueCategory.id)
    query = query.outerjoin(User, Ticket.user_id == User.id)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                Ticket.subject.ilike(term),
                Ticket.ticket_number.ilike(term),
                Ticket.description.ilike(term),
                Ticket.ai_predicted_category.ilike(term),
                Ticket.subcategory.ilike(term),
                IssueCategory.name.ilike(term),
                User.full_name.ilike(term),
                User.email.ilike(term),
            )
        )

    # 4. Strict Dynamic Queue Sorting Hierarchy:
    # 1st: Actual Severity (CRITICAL > HIGH > MEDIUM > LOW)
    # 2nd: Category Precedence (Examination > Fee > Admission > Network > Account > Software > Technical > Hardware > Other)
    # 3rd: Approaching or Breached SLA Deadlines (ai_priority_score DESC)
    # 4th: Waiting Time (created_at ASC — older tickets first)

    effective_priority = func.coalesce(Ticket.confirmed_priority, Ticket.ai_predicted_priority, TicketPriority.MEDIUM)
    priority_rank = case(
        (effective_priority == TicketPriority.CRITICAL, 1),
        (effective_priority == TicketPriority.HIGH, 2),
        (effective_priority == TicketPriority.MEDIUM, 3),
        (effective_priority == TicketPriority.LOW, 4),
        else_=5,
    )

    effective_category = func.coalesce(IssueCategory.name, Ticket.ai_predicted_category, "")
    category_rank = build_category_rank_sql(effective_category, current_user.organization_id)

    if current_user.role == UserRole.USER:
        # End user: view newest submitted tickets first
        query = query.order_by(Ticket.created_at.desc())
    else:
        # Help Desk, Team Lead, and Support: Strict dynamic queue order
        query = query.order_by(
            priority_rank.asc(),
            category_rank.asc(),
            case((Ticket.ai_priority_score.is_(None), 1), else_=0).asc(),
            Ticket.ai_priority_score.desc(),
            Ticket.created_at.asc(),
        )

    tickets = query.all()
    return [_build_ticket_response(t) for t in tickets]


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get single ticket details",
)
def get_ticket(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)
    return _build_ticket_response(ticket)


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Update ticket attributes (category, priority, subject)",
)
def update_ticket(
    ticket_id: int,
    req: TicketUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    # Users can only update their own ticket while still in SUBMITTED status
    if current_user.role == UserRole.USER:
        if ticket.status != TicketStatus.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tickets in review or progress cannot be edited by submitters",
            )
        if req.confirmed_priority is not None or req.status is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Users cannot change priority or status directly",
            )

    old_status = ticket.status
    if req.subject is not None:
        ticket.subject = req.subject.strip()
    if req.description is not None:
        ticket.description = req.description.strip()
    if req.category_id is not None:
        ticket.category_id = req.category_id
    if req.subcategory is not None:
        ticket.subcategory = req.subcategory.strip()
    if req.confirmed_priority is not None:
        ticket.confirmed_priority = req.confirmed_priority

    if req.status is not None and req.status != old_status:
        ticket.status = req.status
        if req.status == TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.now(timezone.utc)
        elif old_status == TicketStatus.RESOLVED and req.status != TicketStatus.RESOLVED:
            ticket.resolved_at = None

        history = TicketHistory(
            organization_id=ticket.organization_id,
            ticket_id=ticket.id,
            previous_status=old_status,
            new_status=req.status,
            changed_by_user_id=current_user.id,
            description="Ticket status updated",
            created_at=datetime.now(timezone.utc),
        )
        db.add(history)

    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return _build_ticket_response(ticket)


@router.post(
    "/{ticket_id}/route",
    response_model=TicketResponse,
    summary="Help Desk confirms routing and approves ticket for team queue",
)
def route_ticket(
    ticket_id: int,
    req: TicketRouteRequest,
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.HELP_DESK,
                UserRole.ORGANIZATION_ADMIN,
                UserRole.PLATFORM_OWNER,
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    # Validate department and support team belong to the ticket's organisation
    dept = (
        db.query(Department)
        .filter(
            Department.id == req.department_id,
            Department.organization_id == ticket.organization_id,
        )
        .first()
    )
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department not found in ticket's organisation",
        )

    team = (
        db.query(SupportTeam)
        .filter(
            SupportTeam.id == req.support_team_id,
            SupportTeam.organization_id == ticket.organization_id,
        )
        .first()
    )
    if not team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Support team not found in ticket's organisation",
        )

    old_status = ticket.status
    ticket.department_id = dept.id
    ticket.support_team_id = team.id

    if req.confirmed_priority:
        ticket.confirmed_priority = req.confirmed_priority
    if req.category_id:
        ticket.category_id = req.category_id

    # Optional direct assignment to an individual engineer during routing
    assigned_eng_name: str | None = None
    if req.assigned_engineer_id:
        engineer = (
            db.query(User)
            .filter(
                User.id == req.assigned_engineer_id,
                User.organization_id == ticket.organization_id,
                User.account_status == AccountStatus.ACTIVE,
            )
            .first()
        )
        if not engineer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned engineer does not exist or is inactive in this organisation",
            )
        if engineer.role not in (UserRole.SUPPORT_TEAM_MEMBER, UserRole.SUPPORT_TEAM_LEAD):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot assign ticket to user with role {engineer.role.value}",
            )
        if engineer.support_team_id and engineer.support_team_id != team.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned engineer does not belong to the selected support team",
            )
        ticket.assigned_engineer_id = engineer.id
        assigned_eng_name = engineer.full_name
        ticket.status = TicketStatus.ASSIGNED
    else:
        ticket.status = TicketStatus.APPROVED_FOR_ROUTING

    ticket.updated_at = datetime.now(timezone.utc)

    # Note & History
    note_text = f"Routed to {dept.name} / {team.name}"
    if assigned_eng_name:
        note_text += f", assigned to {assigned_eng_name}"
    if req.note:
        note_text += f": {req.note.strip()}"

    history = TicketHistory(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        previous_status=old_status,
        new_status=ticket.status,
        changed_by_user_id=current_user.id,
        description=note_text,
        created_at=datetime.now(timezone.utc),
    )
    db.add(history)

    if req.note:
        comment = TicketComment(
            organization_id=ticket.organization_id,
            ticket_id=ticket.id,
            user_id=current_user.id,
            comment=f"[Help Desk Note] {req.note.strip()}",
            is_internal=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(comment)

    db.commit()
    db.refresh(ticket)
    return _build_ticket_response(ticket)


@router.post(
    "/{ticket_id}/escalate",
    response_model=TicketResponse,
    summary="Escalate ticket to CRITICAL priority",
    description="Help Desk operator or Team Lead escalates an urgent ticket to CRITICAL with reason and audit trail.",
)
def escalate_ticket(
    ticket_id: int,
    req: TicketEscalateRequest,
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.HELP_DESK,
                UserRole.SUPPORT_TEAM_LEAD,
                UserRole.ORGANIZATION_ADMIN,
                UserRole.PLATFORM_OWNER,
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    old_priority = ticket.confirmed_priority or ticket.ai_predicted_priority
    ticket.confirmed_priority = TicketPriority.CRITICAL
    ticket.impact = "CRITICAL"
    ticket.urgency = "CRITICAL"
    ticket.updated_at = datetime.now(timezone.utc)

    # Record escalation explanation
    escalation_msg = f"[ESCALATED to CRITICAL by {current_user.full_name} ({current_user.role.value})]: {req.reason.strip()}"
    if ticket.ai_priority_explanation:
        ticket.ai_priority_explanation += f" | {escalation_msg}"
    else:
        ticket.ai_priority_explanation = escalation_msg

    # Audit history
    history = TicketHistory(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        previous_status=ticket.status,
        new_status=ticket.status,
        changed_by_user_id=current_user.id,
        description=f"Ticket escalated to CRITICAL priority: {req.reason.strip()}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(history)

    # Internal comment
    comment_text = f"[Help Desk Escalation] Priority elevated from {old_priority.value if old_priority else 'UNCONFIRMED'} to CRITICAL.\nReason: {req.reason.strip()}"
    if req.note:
        comment_text += f"\nNote: {req.note.strip()}"
    comment = TicketComment(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        user_id=current_user.id,
        comment=comment_text,
        is_internal=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(comment)

    db.commit()
    db.refresh(ticket)
    return _build_ticket_response(ticket)


@router.post(
    "/{ticket_id}/request-clarification",
    response_model=TicketResponse,
    summary="Send ticket back for clarification",
    description="Requests details from the user when submitted information is insufficient, transitioning status to WAITING_FOR_USER.",
)
def request_ticket_clarification(
    ticket_id: int,
    req: TicketClarificationRequest,
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.HELP_DESK,
                UserRole.SUPPORT_TEAM_LEAD,
                UserRole.SUPPORT_TEAM_MEMBER,
                UserRole.ORGANIZATION_ADMIN,
                UserRole.PLATFORM_OWNER,
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    old_status = ticket.status
    ticket.status = TicketStatus.WAITING_FOR_USER
    ticket.updated_at = datetime.now(timezone.utc)

    # Audit history
    history = TicketHistory(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        previous_status=old_status,
        new_status=TicketStatus.WAITING_FOR_USER,
        changed_by_user_id=current_user.id,
        description=f"Sent back for clarification by {current_user.full_name}: {req.question.strip()}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(history)

    # Public comment so the student/user can see what clarification is required
    comment = TicketComment(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        user_id=current_user.id,
        comment=f"[Clarification Requested by Help Desk] {req.question.strip()}",
        is_internal=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(comment)

    db.commit()
    db.refresh(ticket)
    return _build_ticket_response(ticket)


@router.post(
    "/{ticket_id}/reprocess-triage",
    response_model=TicketResponse,
    summary="Reprocess an existing ticket through the AI triage service",
    description="Re-runs AI classification, priority calculation, and duplicate detection without deleting history.",
)
def reprocess_ticket_triage(
    ticket_id: int,
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.HELP_DESK,
                UserRole.ORGANIZATION_ADMIN,
                UserRole.PLATFORM_OWNER,
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    run_ai_triage(db=db, ticket=ticket)
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return _build_ticket_response(ticket)


@router.post(
    "/reprocess-triage-all",
    summary="Reprocess existing tickets through the AI triage service",
    description="Batch re-runs AI triage on all organisation tickets that require updated triage.",
)
def reprocess_all_triage(
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.HELP_DESK,
                UserRole.ORGANIZATION_ADMIN,
                UserRole.PLATFORM_OWNER,
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    query = db.query(Ticket)
    if current_user.role != UserRole.PLATFORM_OWNER:
        query = query.filter(Ticket.organization_id == current_user.organization_id)

    tickets = query.all()
    count = 0
    for t in tickets:
        run_ai_triage(db=db, ticket=t)
        t.updated_at = datetime.now(timezone.utc)
        count += 1

    db.commit()
    return {
        "message": f"Successfully reprocessed {count} tickets through AI triage engine.",
        "count": count,
    }


@router.post(
    "/{ticket_id}/assign",
    response_model=TicketResponse,
    summary="Assigns ticket to an individual engineer",
)
def assign_ticket(
    ticket_id: int,
    req: TicketAssignRequest,
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.HELP_DESK,
                UserRole.SUPPORT_TEAM_LEAD,
                UserRole.ORGANIZATION_ADMIN,
                UserRole.PLATFORM_OWNER,
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    # Validate engineer belongs to same organisation and has technical role
    engineer = (
        db.query(User)
        .filter(
            User.id == req.assigned_engineer_id,
            User.organization_id == ticket.organization_id,
            User.account_status == AccountStatus.ACTIVE,
        )
        .first()
    )
    if not engineer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assigned engineer does not exist or is inactive in this organisation",
        )

    if engineer.role not in (UserRole.SUPPORT_TEAM_MEMBER, UserRole.SUPPORT_TEAM_LEAD):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign ticket to user with role {engineer.role.value}",
        )

    if ticket.support_team_id and engineer.support_team_id and engineer.support_team_id != ticket.support_team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assigned engineer does not belong to the ticket's support team",
        )

    if not ticket.support_team_id and engineer.support_team_id:
        ticket.support_team_id = engineer.support_team_id
        if engineer.department_id:
            ticket.department_id = engineer.department_id

    old_status = ticket.status
    ticket.assigned_engineer_id = engineer.id
    if ticket.status in (
        TicketStatus.SUBMITTED,
        TicketStatus.AWAITING_HELP_DESK_REVIEW,
        TicketStatus.APPROVED_FOR_ROUTING,
    ):
        ticket.status = TicketStatus.ASSIGNED

    ticket.updated_at = datetime.now(timezone.utc)

    desc = f"Assigned to {engineer.full_name}"
    if req.note:
        desc += f": {req.note.strip()}"

    history = TicketHistory(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        previous_status=old_status,
        new_status=ticket.status,
        changed_by_user_id=current_user.id,
        description=desc,
        created_at=datetime.now(timezone.utc),
    )
    db.add(history)

    db.commit()
    db.refresh(ticket)

    # Automatically index verified resolution into Qdrant vector store
    try:
        from app.ai.vector_store import vector_store
        vector_store.upsert_ticket(
            ticket_id=ticket.id,
            organization_id=ticket.organization_id,
            ticket_number=ticket.ticket_number,
            subject=ticket.subject,
            description=ticket.description,
            category=ticket.category.name if ticket.category else (ticket.ai_predicted_category or "General"),
            status=ticket.status.value,
            confirmed_priority=ticket.confirmed_priority.value if ticket.confirmed_priority else None,
            verified_resolution=ticket.verified_resolution,
            is_resolution_verified=ticket.is_resolution_verified,
            created_at_iso=ticket.created_at.isoformat() if ticket.created_at else None,
        )
    except Exception:
        pass

    return _build_ticket_response(ticket)


@router.post(
    "/{ticket_id}/status",
    response_model=TicketResponse,
    summary="Update ticket status lifecycle",
)
def update_status(
    ticket_id: int,
    req: TicketStatusUpdateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    # Regular users can only reopen or close their resolved tickets
    if current_user.role == UserRole.USER:
        if req.status not in (TicketStatus.CLOSED, TicketStatus.REOPENED):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Users can only close or reopen completed tickets",
            )

    old_status = ticket.status
    ticket.status = req.status
    if req.status == TicketStatus.RESOLVED:
        ticket.resolved_at = datetime.now(timezone.utc)
    elif old_status == TicketStatus.RESOLVED and req.status != TicketStatus.RESOLVED:
        ticket.resolved_at = None

    ticket.updated_at = datetime.now(timezone.utc)

    history = TicketHistory(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        previous_status=old_status,
        new_status=req.status,
        changed_by_user_id=current_user.id,
        description=req.note or f"Status changed from {old_status.value} to {req.status.value}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(history)

    db.commit()
    db.refresh(ticket)

    # Automatically index verified resolution into Qdrant vector store
    try:
        from app.ai.vector_store import vector_store
        vector_store.upsert_ticket(
            ticket_id=ticket.id,
            organization_id=ticket.organization_id,
            ticket_number=ticket.ticket_number,
            subject=ticket.subject,
            description=ticket.description,
            category=ticket.category.name if ticket.category else (ticket.ai_predicted_category or "General"),
            status=ticket.status.value,
            confirmed_priority=ticket.confirmed_priority.value if ticket.confirmed_priority else None,
            verified_resolution=ticket.verified_resolution,
            is_resolution_verified=ticket.is_resolution_verified,
            created_at_iso=ticket.created_at.isoformat() if ticket.created_at else None,
        )
    except Exception:
        pass

    return _build_ticket_response(ticket)


@router.post(
    "/{ticket_id}/resolve",
    response_model=TicketResponse,
    summary="Mark ticket as resolved with resolution explanation",
)
def resolve_ticket(
    ticket_id: int,
    req: TicketResolveRequest,
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.SUPPORT_TEAM_MEMBER,
                UserRole.SUPPORT_TEAM_LEAD,
                UserRole.HELP_DESK,
                UserRole.ORGANIZATION_ADMIN,
                UserRole.PLATFORM_OWNER,
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    old_status = ticket.status
    ticket.status = TicketStatus.RESOLVED
    ticket.verified_resolution = req.resolution.strip()
    ticket.is_resolution_verified = True
    ticket.resolved_at = datetime.now(timezone.utc)
    ticket.updated_at = datetime.now(timezone.utc)

    # Resolution comment visible to user
    res_comment = TicketComment(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        user_id=current_user.id,
        comment=f"Resolution: {req.resolution.strip()}",
        is_internal=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(res_comment)

    # Audit trail
    history = TicketHistory(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        previous_status=old_status,
        new_status=TicketStatus.RESOLVED,
        changed_by_user_id=current_user.id,
        description=f"Ticket marked as resolved: {req.resolution.strip()}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(history)

    db.commit()
    db.refresh(ticket)

    # Automatically index verified resolution into Qdrant vector store
    try:
        from app.ai.vector_store import vector_store
        vector_store.upsert_ticket(
            ticket_id=ticket.id,
            organization_id=ticket.organization_id,
            ticket_number=ticket.ticket_number,
            subject=ticket.subject,
            description=ticket.description,
            category=ticket.category.name if ticket.category else (ticket.ai_predicted_category or "General"),
            status=ticket.status.value,
            confirmed_priority=ticket.confirmed_priority.value if ticket.confirmed_priority else None,
            verified_resolution=ticket.verified_resolution,
            is_resolution_verified=ticket.is_resolution_verified,
            created_at_iso=ticket.created_at.isoformat() if ticket.created_at else None,
        )
    except Exception:
        pass

    return _build_ticket_response(ticket)


# ── Comments ───────────────────────────────────────────────────────────────────

@router.get(
    "/{ticket_id}/comments",
    response_model=List[CommentResponse],
    summary="Get threaded discussion and notes for a ticket",
)
def list_comments(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> List[CommentResponse]:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    query = db.query(TicketComment).filter(TicketComment.ticket_id == ticket_id)

    # Regular users CANNOT see internal staff notes
    if current_user.role == UserRole.USER:
        query = query.filter(TicketComment.is_internal == False)  # noqa: E712

    comments = query.order_by(TicketComment.created_at.asc()).all()

    return [
        CommentResponse(
            id=c.id,
            organization_id=c.organization_id,
            ticket_id=c.ticket_id,
            user_id=c.user_id,
            user_name=c.author.full_name if c.author else "Staff",
            user_role=c.author.role.value if c.author else "USER",
            comment=c.comment,
            is_internal=c.is_internal,
            created_at=c.created_at,
        )
        for c in comments
    ]


@router.post(
    "/{ticket_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment or internal staff note to a ticket",
)
def add_comment(
    ticket_id: int,
    req: CommentCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CommentResponse:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    # Regular users cannot post internal notes
    is_internal = req.is_internal
    if current_user.role == UserRole.USER:
        is_internal = False

    comment = TicketComment(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        user_id=current_user.id,
        comment=req.comment.strip(),
        is_internal=is_internal,
        created_at=datetime.now(timezone.utc),
    )
    db.add(comment)
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comment)

    return CommentResponse(
        id=comment.id,
        organization_id=comment.organization_id,
        ticket_id=comment.ticket_id,
        user_id=comment.user_id,
        user_name=current_user.full_name,
        user_role=current_user.role.value,
        comment=comment.comment,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
    )


# ── History ────────────────────────────────────────────────────────────────────

@router.get(
    "/{ticket_id}/history",
    response_model=List[HistoryResponse],
    summary="Get complete audit trail of ticket status transitions",
)
def list_history(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> List[HistoryResponse]:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    history = (
        db.query(TicketHistory)
        .filter(TicketHistory.ticket_id == ticket_id)
        .order_by(TicketHistory.created_at.asc())
        .all()
    )

    return [
        HistoryResponse(
            id=h.id,
            organization_id=h.organization_id,
            ticket_id=h.ticket_id,
            previous_status=h.previous_status,
            new_status=h.new_status,
            changed_by_user_id=h.changed_by_user_id,
            changed_by_name=h.changed_by.full_name if h.changed_by else None,
            description=h.description,
            created_at=h.created_at,
        )
        for h in history
    ]


# ── Attachments ────────────────────────────────────────────────────────────────

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))


@router.get(
    "/{ticket_id}/attachments",
    response_model=List[AttachmentResponse],
    summary="List files attached to a ticket",
)
def list_attachments(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> List[AttachmentResponse]:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    attachments = (
        db.query(TicketAttachment)
        .filter(TicketAttachment.ticket_id == ticket_id)
        .order_by(TicketAttachment.created_at.asc())
        .all()
    )

    return [
        AttachmentResponse(
            id=a.id,
            organization_id=a.organization_id,
            ticket_id=a.ticket_id,
            file_name=a.file_name,
            file_url=a.file_url,
            file_size=a.file_size,
            content_type=a.content_type,
            uploaded_by_user_id=a.uploaded_by_user_id,
            uploaded_by_name=a.uploaded_by.full_name if a.uploaded_by else None,
            created_at=a.created_at,
        )
        for a in attachments
    ]


@router.post(
    "/{ticket_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file attachment to a ticket",
)
def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> AttachmentResponse:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    _check_ticket_access(ticket, current_user)

    # Safe destination directory per org & ticket
    dest_dir = os.path.join(UPLOAD_DIR, str(ticket.organization_id), str(ticket.id))
    os.makedirs(dest_dir, exist_ok=True)
    safe_filename = os.path.basename(file.filename or "attachment.bin")
    file_path = os.path.join(dest_dir, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)
    relative_url = f"/api/v1/uploads/{ticket.organization_id}/{ticket.id}/{safe_filename}"

    attachment = TicketAttachment(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        file_name=safe_filename,
        file_url=relative_url,
        file_size=file_size,
        content_type=file.content_type,
        uploaded_by_user_id=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return AttachmentResponse(
        id=attachment.id,
        organization_id=attachment.organization_id,
        ticket_id=attachment.ticket_id,
        file_name=attachment.file_name,
        file_url=attachment.file_url,
        file_size=attachment.file_size,
        content_type=attachment.content_type,
        uploaded_by_user_id=attachment.uploaded_by_user_id,
        uploaded_by_name=current_user.full_name,
        created_at=attachment.created_at,
    )
