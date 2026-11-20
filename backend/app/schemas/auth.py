"""
Pydantic schemas for Authentication, Registration, and User Management.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.organization import OrganizationType
from app.models.user import AccountStatus, UserRole


# ── Login & Registration Schemas ───────────────────────────────────────────────

class LoginRequest(BaseModel):
    """
    Credentials for login.
    org_code can be an organisation code (e.g. 'JSS-01') or slug (e.g. 'jss-ate').
    For Platform Owner accounts, org_code can be omitted or blank.
    """
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="Account password")
    org_code: Optional[str] = Field(
        None,
        description="Organisation code or slug. Optional for Platform Owners."
    )


class PlatformLoginRequest(BaseModel):
    """Platform Owner specific login (no organisation membership required)."""
    email: EmailStr = Field(..., description="Platform Owner email address")
    password: str = Field(..., min_length=1, description="Account password")


class RegisterRequest(BaseModel):
    """
    Public registration for regular organisation users (students / staff).
    Always assigns role 'USER'. Never allows setting privileged roles.
    """
    org_code: str = Field(..., min_length=2, max_length=50, description="Organisation code or slug")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    email: EmailStr = Field(..., description="Email address within the organisation")
    password: str = Field(..., min_length=6, max_length=128, description="Password (min 6 chars)")


# ── User Profile Schemas ───────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Safe user profile response (never exposes hashed_password)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    organization_code: Optional[str] = None
    full_name: str
    email: str
    role: UserRole
    department_id: Optional[int] = None
    account_status: AccountStatus
    created_at: datetime


class TokenResponse(BaseModel):
    """OAuth2 / JWT Bearer token response with profile payload."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifespan in seconds")
    user: UserResponse


# ── Admin User Creation Schemas ────────────────────────────────────────────────

class UserCreateByAdminRequest(BaseModel):
    """
    Used by Organisation Administrators to provision staff and members
    within their own organisation.
    """
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = Field(
        default=UserRole.USER,
        description="Role to assign. Cannot be PLATFORM_OWNER."
    )
    department_id: Optional[int] = None

    @field_validator("role")
    @classmethod
    def validate_role_not_platform_owner(cls, v: UserRole) -> UserRole:
        if v == UserRole.PLATFORM_OWNER:
            raise ValueError("Organisation administrators cannot create PLATFORM_OWNER accounts.")
        return v


# ── Organisation Schemas ───────────────────────────────────────────────────────

class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    slug: str
    org_type: OrganizationType
    description: Optional[str] = None
    contact_email: str
    is_active: bool
    created_at: datetime


class OrganizationCreateRequest(BaseModel):
    """Used by Platform Owner to create new tenant organisations."""
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    slug: str = Field(..., min_length=2, max_length=50)
    org_type: OrganizationType = OrganizationType.UNIVERSITY
    description: Optional[str] = None
    contact_email: EmailStr
