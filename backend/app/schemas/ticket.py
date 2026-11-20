"""
Pydantic schemas for Ticket Management, Comments, History, and Attachments.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.ticket import TicketPriority, TicketSource, TicketStatus


class AttachmentCreate(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    file_url: str = Field(..., min_length=1, max_length=1000)
    file_size: int = Field(default=0, ge=0)
    content_type: Optional[str] = None


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    ticket_id: int
    file_name: str
    file_url: str
    file_size: int
    content_type: Optional[str] = None
    uploaded_by_user_id: int
    uploaded_by_name: Optional[str] = None
    created_at: datetime


class CommentCreate(BaseModel):
    comment: str = Field(..., min_length=1, max_length=5000)
    is_internal: bool = Field(
        default=False,
        description="Whether this is an internal staff note invisible to the regular user"
    )


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    ticket_id: int
    user_id: int
    user_name: str
    user_role: str
    comment: str
    is_internal: bool
    created_at: datetime


class HistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    ticket_id: int
    previous_status: Optional[TicketStatus] = None
    new_status: TicketStatus
    changed_by_user_id: Optional[int] = None
    changed_by_name: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=500, description="Ticket title or summary")
    description: str = Field(..., min_length=5, description="Detailed problem description")
    category_id: Optional[int] = Field(None, description="Selected issue category ID")
    subcategory: Optional[str] = Field(None, max_length=255, description="Optional subcategory")
    impact: Optional[str] = Field(None, max_length=50, description="Impact level: CRITICAL, HIGH, MEDIUM, LOW")
    urgency: Optional[str] = Field(None, max_length=50, description="Urgency level: CRITICAL, HIGH, MEDIUM, LOW")
    priority: Optional[TicketPriority] = Field(
        default=TicketPriority.MEDIUM,
        description="User requested priority level"
    )
    source: TicketSource = Field(default=TicketSource.WEB)
    attachment_names: Optional[List[str]] = Field(default=None, description="Optional supporting file names")


class TicketUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=3, max_length=500)
    description: Optional[str] = Field(None, min_length=5)
    category_id: Optional[int] = None
    subcategory: Optional[str] = None
    confirmed_priority: Optional[TicketPriority] = None
    status: Optional[TicketStatus] = None


class TicketRouteRequest(BaseModel):
    department_id: int = Field(..., description="Target department ID")
    support_team_id: int = Field(..., description="Target support team ID")
    confirmed_priority: Optional[TicketPriority] = Field(None, description="Confirmed priority by Help Desk")
    category_id: Optional[int] = Field(None, description="Confirmed or adjusted category")
    assigned_engineer_id: Optional[int] = Field(None, description="Optionally assign to a specific engineer during routing")
    note: Optional[str] = Field(None, description="Routing review note")


class TicketAssignRequest(BaseModel):
    assigned_engineer_id: int = Field(..., description="User ID of the assigned support engineer")
    note: Optional[str] = Field(None, description="Assignment note")


class TicketResolveRequest(BaseModel):
    resolution: str = Field(..., min_length=5, description="Resolution details explaining how the issue was fixed")


class TicketStatusUpdateRequest(BaseModel):
    status: TicketStatus
    note: Optional[str] = Field(None, description="Reason or note for status transition")


class TicketEscalateRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Reason for escalation")
    note: Optional[str] = Field(None, description="Additional internal notes for support team")


class TicketClarificationRequest(BaseModel):
    question: str = Field(..., min_length=5, description="Clarification question for the user/student")


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    ticket_number: str
    user_id: int
    submitted_by_name: Optional[str] = None
    submitted_by_email: Optional[str] = None

    category_id: Optional[int] = None
    category_name: Optional[str] = None
    subcategory: Optional[str] = None

    subject: str
    description: str
    source: TicketSource

    # AI Analysis & Recommendations
    ai_predicted_category: Optional[str] = None
    ai_predicted_priority: Optional[TicketPriority] = None
    ai_priority_score: Optional[float] = None
    ai_priority_explanation: Optional[str] = None
    ai_recommended_department_id: Optional[int] = None
    ai_recommended_department_name: Optional[str] = None
    ai_recommended_support_team_id: Optional[int] = None
    ai_recommended_support_team_name: Optional[str] = None
    ai_duplicate_ticket_id: Optional[int] = None
    ai_duplicate_ticket_number: Optional[str] = None
    ai_duplicate_score: Optional[float] = None
    ai_analysis_status: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    ai_evidence_json: Optional[str] = None

    confirmed_priority: Optional[TicketPriority] = None

    department_id: Optional[int] = None
    department_name: Optional[str] = None
    support_team_id: Optional[int] = None
    support_team_name: Optional[str] = None
    assigned_engineer_id: Optional[int] = None
    assigned_engineer_name: Optional[str] = None

    status: TicketStatus
    impact: Optional[str] = None
    urgency: Optional[str] = None

    related_incident_id: Optional[int] = None
    incident_cluster_id: Optional[int] = None
    verified_resolution: Optional[str] = None
    is_resolution_verified: bool = False

    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    # Counts
    comments_count: int = 0
    attachments_count: int = 0
