"""
Organisation endpoints with multi-tenant enforcement.
"""

from datetime import datetime, timezone
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role, verify_tenant_access
from app.database.session import get_db
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.auth import OrganizationCreateRequest, OrganizationResponse

router = APIRouter()


@router.get(
    "",
    response_model=List[OrganizationResponse],
    summary="List Organisations",
    description=(
        "Lists organisations. Platform Owners see all organisations; "
        "Organisation users only see their own active organisation."
    ),
)
def list_organizations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> List[OrganizationResponse]:
    if current_user.role == UserRole.PLATFORM_OWNER:
        orgs = db.query(Organization).order_by(Organization.name).all()
    else:
        if current_user.organization_id is None:
            return []
        orgs = (
            db.query(Organization)
            .filter(Organization.id == current_user.organization_id)
            .all()
        )
    return [OrganizationResponse.model_validate(o) for o in orgs]


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Organisation (Platform Owner Only)",
    description="Provisions a new tenant organisation on QueueMind AI.",
)
def create_organization(
    req: OrganizationCreateRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.PLATFORM_OWNER))],
    db: Annotated[Session, Depends(get_db)],
) -> OrganizationResponse:
    # Check duplicate code or slug or contact_email
    clean_code = req.code.strip().upper()
    clean_slug = req.slug.strip().lower()

    existing = (
        db.query(Organization)
        .filter(
            (Organization.code == clean_code)
            | (Organization.slug == clean_slug)
            | (Organization.contact_email == req.contact_email.strip().lower())
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organisation with this code, slug, or contact email already exists",
        )

    org = Organization(
        name=req.name.strip(),
        code=clean_code,
        slug=clean_slug,
        org_type=req.org_type,
        description=req.description,
        contact_email=req.contact_email.strip().lower(),
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    return OrganizationResponse.model_validate(org)


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Get Organisation Details",
    description="Retrieves organisation information with strict tenant isolation.",
)
def get_organization_by_id(
    org_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OrganizationResponse:
    verify_tenant_access(current_user, org_id)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found",
        )
    return OrganizationResponse.model_validate(org)
