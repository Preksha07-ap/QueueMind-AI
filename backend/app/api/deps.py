"""
FastAPI dependencies for authentication, role-based access control,
and multi-tenant isolation.
"""

from typing import Annotated, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import AccountStatus, User, UserRole

# HTTP Bearer scheme: auto_error=False so we can provide clean, specific error messages
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Validates the JWT access token from the Authorization header and
    returns the authenticated User from the database.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = int(user_id_str)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token does not exist",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.account_status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is {user.account_status.value.lower()}",
        )

    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Convenience alias ensuring active status."""
    return current_user


class RequireRoles:
    """
    Dependency callable that restricts route access to specified roles.
    Raises 403 Forbidden if the authenticated user's role is not authorized.
    """
    def __init__(self, *allowed_roles: UserRole):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in self.allowed_roles:
            role_names = ", ".join(r.value for r in self.allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: [{role_names}]. Current role: {current_user.role.value}",
            )
        return current_user


def require_role(*roles: UserRole) -> RequireRoles:
    """Factory function for role enforcement."""
    return RequireRoles(*roles)


def verify_tenant_access(current_user: User, target_organization_id: int) -> None:
    """
    Enforce organisation boundary on multi-tenant records.
    PLATFORM_OWNER has cross-tenant oversight.
    All other roles must match the target organisation ID exactly.
    """
    if current_user.role == UserRole.PLATFORM_OWNER:
        return

    if current_user.organization_id != target_organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to data from another organisation is forbidden",
        )
