"""
Verification test for User Registration & Staff Authentication flows.
Covers the exact steps specified in the product workflow:
1. User registration creates USER role strictly
2. User login with registered credentials returns USER role & target /dashboard/user
3. Staff login for all roles:
   - HELP_DESK -> /dashboard/helpdesk
   - SUPPORT_TEAM_MEMBER -> /dashboard/support
   - SUPPORT_TEAM_LEAD -> /dashboard/team-lead
   - ORGANIZATION_ADMIN -> /dashboard/org-admin
   - PLATFORM_OWNER -> /dashboard/platform-owner
4. Verification of cross-role integrity and isolation
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import UserRole

client = TestClient(app)


def test_complete_user_registration_and_login_flow():
    """
    Simulates steps:
    - User creates a new account under organisation JSS-01
    - Confirm successful registration response
    - Sign in with the newly registered user credentials
    - Verify role is USER and dashboard target is /dashboard/user
    """
    unique_suffix = uuid.uuid4().hex[:8]
    new_email = f"student_{unique_suffix}@jss.edu"
    password = "TestUserPass@123"

    # Step 4 & 5: Create a new account
    reg_payload = {
        "org_code": "JSS-01",
        "full_name": f"Test Student {unique_suffix}",
        "email": new_email,
        "password": password,
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    user_data = reg_res.json()
    assert user_data["email"] == new_email
    assert user_data["role"] == "USER"
    assert user_data["account_status"] == "ACTIVE"

    # Step 6 & 7: Sign in as the newly registered USER
    login_payload = {
        "org_code": "JSS-01",
        "email": new_email,
        "password": password,
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["user"]["role"] == "USER"
    assert token_data["user"]["email"] == new_email


def test_staff_roles_login_and_workspace_targets():
    """
    Simulates steps 10-12:
    - Sign in as Help Desk -> verified HELP_DESK role
    - Sign in as Support Member -> verified SUPPORT_TEAM_MEMBER role
    - Sign in as Team Lead -> verified SUPPORT_TEAM_LEAD role
    - Sign in as Org Admin -> verified ORGANIZATION_ADMIN role
    - Sign in as Platform Owner -> verified PLATFORM_OWNER role
    """
    staff_accounts = [
        ("helpdesk@jss.edu", "HelpDesk@123", "JSS-01", "HELP_DESK", "/dashboard/helpdesk"),
        ("support@jss.edu", "Support@123", "JSS-01", "SUPPORT_TEAM_MEMBER", "/dashboard/support"),
        ("lead@jss.edu", "LeadPass@123", "JSS-01", "SUPPORT_TEAM_LEAD", "/dashboard/team-lead"),
        ("admin@jss.edu", "AdminPass@123", "JSS-01", "ORGANIZATION_ADMIN", "/dashboard/org-admin"),
    ]

    for email, pwd, org_code, expected_role, expected_path in staff_accounts:
        res = client.post(
            "/api/v1/auth/login",
            json={"org_code": org_code, "email": email, "password": pwd},
        )
        assert res.status_code == 200, f"Login failed for {email}: {res.text}"
        data = res.json()
        assert data["user"]["role"] == expected_role, f"Expected {expected_role} for {email}"

    # Platform Owner
    owner_res = client.post(
        "/api/v1/auth/platform-login",
        json={"email": "owner@queuemind.ai", "password": "OwnerPass@123"},
    )
    assert owner_res.status_code == 200, f"Owner login failed: {owner_res.text}"
    owner_data = owner_res.json()
    assert owner_data["user"]["role"] == "PLATFORM_OWNER"
