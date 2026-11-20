"""
Authentication Endpoints: Login, Platform Login, Public Registration, Me, Logout.
"""

from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.database.session import get_db
from app.models.organization import Organization
from app.models.user import AccountStatus, User, UserRole
from app.schemas.auth import (
    LoginRequest,
    PlatformLoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()


def _build_user_response(user: User) -> UserResponse:
    """Helper to transform ORM User into UserResponse including org info."""
    org_name: Optional[str] = None
    org_code: Optional[str] = None
    if user.organization:
        org_name = user.organization.name
        org_code = user.organization.code

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
    "/login",
    response_model=TokenResponse,
    summary="Unified Login for Organisation Members and Platform Owners",
    description=(
        "Authenticates a user against their organisation using organisation code/slug, "
        "email, and password. Platform Owners may omit the organisation code."
    ),
)
def login(
    req: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user: Optional[User] = None

    # Case 1: An organisation code or slug is provided
    if req.org_code and req.org_code.strip():
        search_code = req.org_code.strip().lower()
        org = (
            db.query(Organization)
            .filter(
                (Organization.code.ilike(search_code))
                | (Organization.slug.ilike(search_code))
            )
            .first()
        )
        if not org or not org.is_active:
            # Generic error to prevent organisation existence harvesting
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid organisation code or credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Look up user specifically within that organisation
        user = (
            db.query(User)
            .filter(
                User.organization_id == org.id,
                User.email == req.email.strip().lower(),
            )
            .first()
        )
    else:
        # Case 2: No organisation code provided — attempt Platform Owner login
        user = (
            db.query(User)
            .filter(
                User.email == req.email.strip().lower(),
                User.role == UserRole.PLATFORM_OWNER,
            )
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Organisation code is required for organisation accounts",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Validate user existence and password
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check account status
    if user.account_status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is {user.account_status.value.lower()}. Please contact your administrator.",
        )

    # Generate JWT
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(
        subject=user.id,
        claims={
            "role": user.role.value,
            "org_id": user.organization_id,
            "email": user.email,
        },
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=_build_user_response(user),
    )





@router.post(
    "/platform-login",
    response_model=TokenResponse,
    summary="Platform Owner Login",
    description="Explicit login for Platform Owners without an organisation membership.",
)
def platform_login(
    req: PlatformLoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user = (
        db.query(User)
        .filter(
            User.email == req.email.strip().lower(),
            User.role == UserRole.PLATFORM_OWNER,
        )
        .first()
    )

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid platform owner credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.account_status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is {user.account_status.value.lower()}",
        )

    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(
        subject=user.id,
        claims={
            "role": user.role.value,
            "org_id": None,
            "email": user.email,
        },
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=_build_user_response(user),
    )


@router.post(
    "/organizer-login",
    response_model=TokenResponse,
    summary="Organizer Login (Alias for unified login)",
    description="Authenticates staff using organisation code, email, and password.",
)
def organizer_login(
    req: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    return login(req, db)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Public User Registration",
    description=(
        "Registers a regular user (student or staff) within a specified organisation. "
        "Strictly assigns role 'USER'. Privileged roles cannot be self-assigned."
    ),
)
def register(
    req: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    # 1. Resolve and verify organisation
    search_code = req.org_code.strip().lower()
    org = (
        db.query(Organization)
        .filter(
            (Organization.code.ilike(search_code))
            | (Organization.slug.ilike(search_code))
        )
        .first()
    )
    if not org or not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found or is currently inactive",
        )

    # 2. Check for duplicate email in this organisation
    normalized_email = req.email.strip().lower()
    existing = (
        db.query(User)
        .filter(
            User.organization_id == org.id,
            User.email == normalized_email,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists in this organisation",
        )

    # 3. Create regular user
    user = User(
        organization_id=org.id,
        full_name=req.full_name.strip(),
        email=normalized_email,
        hashed_password=get_password_hash(req.password),
        role=UserRole.USER,  # Strictly locked to standard USER
        department_id=None,
        account_status=AccountStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _build_user_response(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User Profile",
    description="Returns the authenticated user's profile and organisation context.",
)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return _build_user_response(current_user)


@router.post(
    "/logout",
    summary="Logout Current User",
    description="Stateless token logout confirmation.",
)
def logout(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    return {"message": "Logged out successfully", "user_id": current_user.id}
