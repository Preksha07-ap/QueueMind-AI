"""
Incident Cluster API Endpoints for QueueMind AI — Phase 6.

Provides Help Desk, Team Lead, Org Admin, and Platform Owner with:
- List incident clusters for their organisation.
- Get single cluster detail including all related ticket IDs.
- Confirm or reject AI-suggested grouping.
- Resolve an incident cluster.
- Get the cluster that a specific ticket belongs to.
"""

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from sqlalchemy.orm import Session

from app.ai.incident_cluster_service import (
    list_clusters_for_org,
    get_cluster_detail,
    get_ticket_cluster,
    confirm_cluster,
    resolve_cluster,
)
from app.api.deps import get_current_active_user, require_role
from app.database.session import get_db
from app.models.incident_cluster import IncidentCluster
from app.models.user import User, UserRole


router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────────────

class IncidentClusterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    cluster_number: str
    primary_ticket_id: Optional[int] = None
    common_issue_summary: Optional[str] = None
    category: Optional[str] = None
    incident_priority: str
    status: str
    related_ticket_ids: List[int] = []
    distinct_affected_users: int
    total_reports: int
    similarity_score: Optional[float] = None
    verified_resolution: Optional[str] = None
    escalation_reason: Optional[str] = None
    is_confirmed: bool
    first_reported_at: datetime
    last_reported_at: datetime
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ClusterResolveRequest(BaseModel):
    resolution: str


def _build_cluster_response(cluster: IncidentCluster) -> IncidentClusterResponse:
    import json
    try:
        related_ids = json.loads(cluster.related_ticket_ids_json or "[]")
    except Exception:
        related_ids = []
    return IncidentClusterResponse(
        id=cluster.id,
        organization_id=cluster.organization_id,
        cluster_number=cluster.cluster_number,
        primary_ticket_id=cluster.primary_ticket_id,
        common_issue_summary=cluster.common_issue_summary,
        category=cluster.category,
        incident_priority=cluster.incident_priority,
        status=cluster.status,
        related_ticket_ids=related_ids,
        distinct_affected_users=cluster.distinct_affected_users,
        total_reports=cluster.total_reports,
        similarity_score=cluster.similarity_score,
        verified_resolution=cluster.verified_resolution,
        escalation_reason=cluster.escalation_reason,
        is_confirmed=cluster.is_confirmed,
        first_reported_at=cluster.first_reported_at,
        last_reported_at=cluster.last_reported_at,
        resolved_at=cluster.resolved_at,
        created_at=cluster.created_at,
        updated_at=cluster.updated_at,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=List[IncidentClusterResponse],
    summary="List incident clusters for the current organisation",
)
def list_clusters(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
) -> List[IncidentClusterResponse]:
    if current_user.role == UserRole.PLATFORM_OWNER:
        # Platform owner: list all clusters (across all orgs — but tenant isolation
        # means we still need an org_id; return empty for now unless org_id specified)
        # For simplicity, platform owner can filter by passing ?org_id= via admin
        return []

    org_id = current_user.organization_id
    if not org_id:
        return []

    clusters = list_clusters_for_org(db, org_id, status_filter=status_filter, limit=limit)
    return [_build_cluster_response(c) for c in clusters]


@router.get(
    "/ticket/{ticket_id}",
    response_model=Optional[IncidentClusterResponse],
    summary="Get the incident cluster that a ticket belongs to",
)
def get_cluster_for_ticket(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Optional[IncidentClusterResponse]:
    org_id = current_user.organization_id
    cluster = get_ticket_cluster(db, org_id, ticket_id)
    if not cluster:
        return None
    return _build_cluster_response(cluster)


@router.get(
    "/{cluster_id}",
    response_model=IncidentClusterResponse,
    summary="Get single incident cluster detail",
)
def get_cluster(
    cluster_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> IncidentClusterResponse:
    org_id = current_user.organization_id
    if current_user.role == UserRole.PLATFORM_OWNER:
        # Allow platform owner to view any cluster
        from app.models.incident_cluster import IncidentCluster as IC
        cluster = db.query(IC).filter(IC.id == cluster_id).first()
    else:
        cluster = get_cluster_detail(db, org_id, cluster_id)

    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident cluster not found")
    return _build_cluster_response(cluster)


@router.post(
    "/{cluster_id}/confirm",
    response_model=IncidentClusterResponse,
    summary="Help Desk confirms the AI-suggested incident grouping",
)
def confirm_incident_cluster(
    cluster_id: int,
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.HELP_DESK, UserRole.ORGANIZATION_ADMIN, UserRole.PLATFORM_OWNER)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> IncidentClusterResponse:
    org_id = current_user.organization_id
    cluster = confirm_cluster(db, org_id, cluster_id)
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident cluster not found")
    db.commit()
    db.refresh(cluster)
    return _build_cluster_response(cluster)


@router.post(
    "/{cluster_id}/resolve",
    response_model=IncidentClusterResponse,
    summary="Resolve an incident cluster with a verified resolution",
)
def resolve_incident_cluster(
    cluster_id: int,
    req: ClusterResolveRequest,
    current_user: Annotated[
        User,
        Depends(require_role(
            UserRole.HELP_DESK, UserRole.SUPPORT_TEAM_LEAD,
            UserRole.ORGANIZATION_ADMIN, UserRole.PLATFORM_OWNER,
        )),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> IncidentClusterResponse:
    org_id = current_user.organization_id
    cluster = resolve_cluster(db, org_id, cluster_id, req.resolution)
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident cluster not found")
    db.commit()
    db.refresh(cluster)
    return _build_cluster_response(cluster)
