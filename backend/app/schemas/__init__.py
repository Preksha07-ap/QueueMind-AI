"""Pydantic data validation schemas."""

from app.schemas.health import (
    DatabaseHealthDetail,
    DatabaseHealthResponse,
    HealthCheckResponse,
)
from app.schemas.auth import (
    LoginRequest,
    PlatformLoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserCreateByAdminRequest,
    OrganizationResponse,
    OrganizationCreateRequest,
)
from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketRouteRequest,
    TicketAssignRequest,
    TicketResolveRequest,
    TicketStatusUpdateRequest,
    CommentCreate,
    CommentResponse,
    HistoryResponse,
    AttachmentCreate,
    AttachmentResponse,
)
from app.schemas.metadata import (
    CategoryResponse,
    DepartmentResponse,
    SupportTeamResponse,
    StaffMemberResponse,
)

__all__ = [
    "HealthCheckResponse",
    "DatabaseHealthDetail",
    "DatabaseHealthResponse",
    "LoginRequest",
    "PlatformLoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    "UserCreateByAdminRequest",
    "OrganizationResponse",
    "OrganizationCreateRequest",
    "TicketCreate",
    "TicketUpdate",
    "TicketResponse",
    "TicketRouteRequest",
    "TicketAssignRequest",
    "TicketResolveRequest",
    "TicketStatusUpdateRequest",
    "CommentCreate",
    "CommentResponse",
    "HistoryResponse",
    "AttachmentCreate",
    "AttachmentResponse",
    "CategoryResponse",
    "DepartmentResponse",
    "SupportTeamResponse",
    "StaffMemberResponse",
]
