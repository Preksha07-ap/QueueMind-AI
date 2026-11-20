"""
Metadata endpoints for Categories, Departments, Support Teams, and Staff Engineers.
Enforces multi-tenancy and active status checks.
"""

from typing import Annotated, Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.category_config import get_organization_weights, set_organization_weights
from app.database.session import get_db
from app.models.department import Department
from app.models.issue_category import IssueCategory
from app.models.support_team import SupportTeam
from app.models.user import AccountStatus, User, UserRole
from app.schemas.metadata import (
    CategoryResponse,
    DepartmentResponse,
    StaffMemberResponse,
    SupportTeamResponse,
)

router = APIRouter()


@router.get(
    "/categories",
    response_model=List[CategoryResponse],
    summary="List active issue categories for current organisation",
)
def list_categories(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    department_id: Optional[int] = Query(None),
) -> List[CategoryResponse]:
    query = db.query(IssueCategory).filter(IssueCategory.is_active == True)  # noqa: E712
    if current_user.role != UserRole.PLATFORM_OWNER:
        query = query.filter(IssueCategory.organization_id == current_user.organization_id)
    if department_id:
        query = query.filter(IssueCategory.department_id == department_id)

    return query.order_by(IssueCategory.name.asc()).all()


@router.get(
    "/departments",
    response_model=List[DepartmentResponse],
    summary="List active departments for current organisation",
)
def list_departments(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> List[DepartmentResponse]:
    query = db.query(Department).filter(Department.is_active == True)  # noqa: E712
    if current_user.role != UserRole.PLATFORM_OWNER:
        query = query.filter(Department.organization_id == current_user.organization_id)

    return query.order_by(Department.name.asc()).all()


@router.get(
    "/support-teams",
    response_model=List[SupportTeamResponse],
    summary="List active support teams for current organisation",
)
def list_support_teams(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    department_id: Optional[int] = Query(None),
) -> List[SupportTeamResponse]:
    query = db.query(SupportTeam).filter(SupportTeam.is_active == True)  # noqa: E712
    if current_user.role != UserRole.PLATFORM_OWNER:
        query = query.filter(SupportTeam.organization_id == current_user.organization_id)
    if department_id:
        query = query.filter(SupportTeam.department_id == department_id)

    return query.order_by(SupportTeam.name.asc()).all()


@router.get(
    "/engineers",
    response_model=List[StaffMemberResponse],
    summary="List active support engineers in organisation or team",
)
def list_engineers(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    team_id: Optional[int] = Query(None),
) -> List[StaffMemberResponse]:
    query = (
        db.query(User)
        .filter(
            User.account_status == AccountStatus.ACTIVE,
            User.role.in_([UserRole.SUPPORT_TEAM_MEMBER, UserRole.SUPPORT_TEAM_LEAD]),
        )
    )
    if current_user.role != UserRole.PLATFORM_OWNER:
        query = query.filter(User.organization_id == current_user.organization_id)
    if team_id:
        query = query.filter(User.support_team_id == team_id)

    users = query.order_by(User.full_name.asc()).all()
    return [
        StaffMemberResponse(
            id=u.id,
            full_name=u.full_name,
            email=u.email,
            role=u.role,
            department_id=u.department_id,
            support_team_id=u.support_team_id,
        )
        for u in users
    ]


@router.get(
    "/category-weights",
    response_model=Dict[str, int],
    summary="Get category priority weights for current organisation",
)
def get_category_weights(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Dict[str, int]:
    org_id = current_user.organization_id or 1
    return get_organization_weights(org_id)


@router.put(
    "/category-weights",
    response_model=Dict[str, int],
    summary="Update category priority weights for current organisation (Org Admin / Platform Owner)",
)
def update_category_weights(
    weights: Dict[str, int],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Dict[str, int]:
    if current_user.role not in [UserRole.ORGANIZATION_ADMIN, UserRole.PLATFORM_OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Organization Admins can customize category priority weights",
        )
    org_id = current_user.organization_id or 1
    # Validate weights are in reasonable range 1..100
    cleaned: Dict[str, int] = {}
    for cat, wt in weights.items():
        if isinstance(wt, int) and 1 <= wt <= 100:
            cleaned[cat] = wt
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Weight for '{cat}' must be an integer between 1 and 100",
            )
    return set_organization_weights(org_id, cleaned)
