"""
User management endpoints for Organisation Admins and Platform Owners.
"""

from datetime import datetime, timezone
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role, verify_tenant_access
from app.core.security import get_password_hash
from app.database.session import get_db
from app.models.organization import Organization
from app.models.user import AccountStatus, User, UserRole
from app.schemas.auth import UserCreateByAdminRequest, UserResponse

router = APIRouter()


def _build_user_response(user: User) -> UserResponse:
    org_name = user.organization.name if user.organization else None
    org_code = user.organization.code if user.organization else None
    return UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        organization_name=org_name,
        organization_code=org_code,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        department_id=user.department_id,
        account_status=user.account_status,
        created_at=user.created_at,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision New User (Admin)",
    description=(
        "Allows Organisation Admins to create users within their organisation. "
        "Strictly prevents creating Platform Owner accounts or targeting another organisation."
    ),
)
def create_user(
    req: UserCreateByAdminRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.ORGANIZATION_ADMIN, UserRole.PLATFORM_OWNER))],
    db: Annotated[Session, Depends(get_db)],
    target_organization_id: Optional[int] = Query(None, description="Target org ID (Platform Owner only)"),
) -> UserResponse:
    # 1. Determine target organisation
    if current_user.role == UserRole.ORGANIZATION_ADMIN:
        # Organisation Admin can ONLY create in their own organisation
        assigned_org_id = current_user.organization_id
        if assigned_org_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin account is not linked to any organisation",
            )
        # Strictly forbid creating PLATFORM_OWNER
        if req.role == UserRole.PLATFORM_OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organisation administrators are not authorised to create Platform Owner accounts",
            )
    else:
        # Platform Owner
        assigned_org_id = target_organization_id

    # 2. Verify target organisation exists if specified
    if assigned_org_id is not None:
        org = db.query(Organization).filter(Organization.id == assigned_org_id).first()
        if not org or not org.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target organisation not found or inactive",
            )

    # 3. Check for duplicate email in that organisation
    normalized_email = req.email.strip().lower()
    existing = (
        db.query(User)
        .filter(
            User.organization_id == assigned_org_id,
            User.email == normalized_email,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists in this organisation",
        )

    # 4. Create user
    user = User(
        organization_id=assigned_org_id,
        full_name=req.full_name.strip(),
        email=normalized_email,
        hashed_password=get_password_hash(req.password),
        role=req.role,
        department_id=req.department_id,
        account_status=AccountStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _build_user_response(user)


@router.get(
    "",
    response_model=List[UserResponse],
    summary="List Users with Multi-Tenant Scoping",
    description="Organisation staff view users in their own organisation; Platform Owners view all or filter by org.",
)
def list_users(
    current_user: Annotated[
        User,
        Depends(
            require_role(
                UserRole.ORGANIZATION_ADMIN,
                UserRole.PLATFORM_OWNER,
                UserRole.HELP_DESK,
                UserRole.SUPPORT_TEAM_LEAD,
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
    organization_id: Optional[int] = Query(None, description="Filter by org (Platform Owner only)"),
) -> List[UserResponse]:
    query = db.query(User)

    if current_user.role != UserRole.PLATFORM_OWNER:
        # Enforce organisation boundary
        query = query.filter(User.organization_id == current_user.organization_id)
    else:
        # Platform Owner can optionally filter
        if organization_id is not None:
            query = query.filter(User.organization_id == organization_id)

    users = query.order_by(User.created_at.desc()).all()
    return [_build_user_response(u) for u in users]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get User Details",
    description="Retrieves a user profile with organisation boundary check.",
)
def get_user_by_id(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Self-access is always allowed
    if current_user.id != user.id:
        # Otherwise verify tenant access
        if user.organization_id is not None:
            verify_tenant_access(current_user, user.organization_id)
        elif current_user.role != UserRole.PLATFORM_OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    return _build_user_response(user)
