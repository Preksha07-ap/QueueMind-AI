"""
Pydantic schemas for Categories, Departments, Support Teams, and Staff Members.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.user import UserRole


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    name: str
    description: Optional[str] = None
    department_id: Optional[int] = None
    support_team_id: Optional[int] = None
    is_active: bool


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    name: str
    description: Optional[str] = None
    is_active: bool


class SupportTeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    department_id: int
    name: str
    description: Optional[str] = None
    is_active: bool


class StaffMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: UserRole
    department_id: Optional[int] = None
    support_team_id: Optional[int] = None
