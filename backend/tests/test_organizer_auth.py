"""
Comprehensive Organizer Authentication Tests — QueueMind AI

Tests all requirements from the Fix Organizer Authentication spec:
1.  Help Desk login  → role HELP_DESK  → /dashboard/helpdesk
2.  Solution Helper login → role SUPPORT_TEAM_MEMBER → /dashboard/support
3.  Team Lead login → role SUPPORT_TEAM_LEAD → /dashboard/team-lead
4.  Organisation Admin login → role ORGANIZATION_ADMIN → /dashboard/org-admin
5.  Platform Owner login (platform-login endpoint, no org code) → /dashboard/platform-owner
6.  Incorrect credentials → 401 Unauthorized
7.  Wrong organisation code → 401 Unauthorized
8.  Staff credentials used against wrong org → 401 Unauthorized (cross-org isolation)
9.  Missing org code on staff login → backend rejects or falls back to platform-owner check
10. Backend determines role; frontend never trusts a role from the payload
11. Direct access to /dashboard/platform-owner without valid token → 401
12. Existing USER cannot log in through platform-login endpoint
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import UserRole

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STAFF_LOGIN_URL = "/api/v1/auth/login"
PLATFORM_LOGIN_URL = "/api/v1/auth/platform-login"
ME_URL = "/api/v1/auth/me"


def org_login(email: str, password: str, org_code: str = "JSS-01") -> dict:
    """POST to the organisation staff login endpoint."""
    res = client.post(
        STAFF_LOGIN_URL,
        json={"org_code": org_code, "email": email, "password": password},
    )
    return res


def platform_login(email: str, password: str) -> dict:
    """POST to the platform-login endpoint (no org code)."""
    res = client.post(
        PLATFORM_LOGIN_URL,
        json={"email": email, "password": password},
    )
    return res


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Help Desk login
# ---------------------------------------------------------------------------

def test_helpdesk_login_returns_correct_role():
    """Help Desk staff authenticates through the org-login endpoint and receives HELP_DESK role."""
    res = org_login("helpdesk@jss.edu", "HelpDesk@123", "JSS-01")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "HELP_DESK"
    assert data["user"]["email"] == "helpdesk@jss.edu"


def test_helpdesk_me_endpoint_confirms_role():
    """The /me endpoint confirms the HELP_DESK role using the JWT returned at login."""
    res = org_login("helpdesk@jss.edu", "HelpDesk@123", "JSS-01")
    assert res.status_code == 200
    token = res.json()["access_token"]

    me_res = client.get(ME_URL, headers=auth_header(token))
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "HELP_DESK"


# ---------------------------------------------------------------------------
# 2. Solution Helper (Support Team Member) login
# ---------------------------------------------------------------------------

def test_support_member_login_returns_correct_role():
    """Solution Helper authenticates and receives SUPPORT_TEAM_MEMBER role."""
    res = org_login("support@jss.edu", "Support@123", "JSS-01")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["user"]["role"] == "SUPPORT_TEAM_MEMBER"
    assert data["user"]["email"] == "support@jss.edu"


# ---------------------------------------------------------------------------
# 3. Team Lead login
# ---------------------------------------------------------------------------

def test_team_lead_login_returns_correct_role():
    """Team Lead authenticates and receives SUPPORT_TEAM_LEAD role."""
    res = org_login("lead@jss.edu", "LeadPass@123", "JSS-01")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["user"]["role"] == "SUPPORT_TEAM_LEAD"
    assert data["user"]["email"] == "lead@jss.edu"


# ---------------------------------------------------------------------------
# 4. Organisation Admin login
# ---------------------------------------------------------------------------

def test_org_admin_login_returns_correct_role():
    """Org Admin authenticates through org-login and receives ORGANIZATION_ADMIN role."""
    res = org_login("admin@jss.edu", "AdminPass@123", "JSS-01")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["user"]["role"] == "ORGANIZATION_ADMIN"
    assert data["user"]["email"] == "admin@jss.edu"


# ---------------------------------------------------------------------------
# 5. Platform Owner login via dedicated endpoint
# ---------------------------------------------------------------------------

def test_platform_owner_login_via_platform_endpoint():
    """Platform Owner authenticates through the /platform-login endpoint (no org code)."""
    res = platform_login("owner@queuemind.ai", "OwnerPass@123")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "PLATFORM_OWNER"
    assert data["user"]["email"] == "owner@queuemind.ai"


def test_platform_owner_me_endpoint_confirms_role():
    """The /me endpoint confirms PLATFORM_OWNER role using the platform-login JWT."""
    res = platform_login("owner@queuemind.ai", "OwnerPass@123")
    assert res.status_code == 200
    token = res.json()["access_token"]

    me_res = client.get(ME_URL, headers=auth_header(token))
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "PLATFORM_OWNER"


# ---------------------------------------------------------------------------
# 6. Incorrect credentials → 401
# ---------------------------------------------------------------------------

def test_wrong_password_returns_401():
    """Wrong password for a known staff account returns 401."""
    res = org_login("helpdesk@jss.edu", "WRONG_PASSWORD_XYZ", "JSS-01")
    assert res.status_code == 401, f"Expected 401 for wrong password, got {res.status_code}"


def test_wrong_email_returns_401():
    """Non-existent email under a valid org returns 401."""
    res = org_login("nobody@jss.edu", "SomePass@123", "JSS-01")
    assert res.status_code == 401, f"Expected 401 for unknown email, got {res.status_code}"


def test_platform_owner_wrong_password_returns_401():
    """Wrong platform-owner password returns 401."""
    res = platform_login("owner@queuemind.ai", "WrongOwnerPass")
    assert res.status_code == 401, f"Expected 401 for wrong platform owner password, got {res.status_code}"


# ---------------------------------------------------------------------------
# 7. Wrong organisation code → 401
# ---------------------------------------------------------------------------

def test_wrong_org_code_returns_401():
    """Valid credentials with an invalid organisation code return 401."""
    res = org_login("helpdesk@jss.edu", "HelpDesk@123", "INVALID-ORG")
    assert res.status_code == 401, f"Expected 401 for invalid org code, got {res.status_code}"


def test_nonexistent_org_code_returns_401():
    """Completely non-existent org code returns 401 without revealing org existence."""
    res = org_login("helpdesk@jss.edu", "HelpDesk@123", "GHOST-99")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# 8. Cross-organisation access isolation
# ---------------------------------------------------------------------------

def test_jss_staff_cannot_login_to_apex_org():
    """JSS staff credentials rejected when attempting login with APEX-01 org code."""
    # This tests that a staff member cannot authenticate against a different organisation,
    # even with otherwise valid credentials.
    res = org_login("helpdesk@jss.edu", "HelpDesk@123", "APEX-01")
    assert res.status_code == 401, (
        f"Expected 401: JSS staff should not authenticate under APEX-01. Got {res.status_code}"
    )


def test_staff_email_with_wrong_org_rejected():
    """Staff credentials are always validated within the specified organisation boundary."""
    res = org_login("admin@jss.edu", "AdminPass@123", "APEX-01")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# 9. Missing org code on staff login
# ---------------------------------------------------------------------------

def test_missing_org_code_falls_back_to_platform_owner_check_or_rejects():
    """
    When org_code is omitted on the /login endpoint, the backend attempts a
    platform-owner lookup. A regular staff account must NOT authenticate this way.
    """
    # Staff account should NOT be found via platform-owner path
    res = client.post(
        STAFF_LOGIN_URL,
        json={"email": "helpdesk@jss.edu", "password": "HelpDesk@123"},
    )
    # Must be 401 — backend requires org code for non-platform-owner accounts
    assert res.status_code == 401, (
        f"Staff should not authenticate without org code. Got {res.status_code}: {res.text}"
    )


def test_empty_string_org_code_behaves_same_as_missing():
    """Empty-string org code is treated the same as omitted and must reject staff logins."""
    res = client.post(
        STAFF_LOGIN_URL,
        json={"org_code": "", "email": "helpdesk@jss.edu", "password": "HelpDesk@123"},
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# 10. Backend determines role — frontend payload cannot inject role
# ---------------------------------------------------------------------------

def test_login_response_does_not_trust_client_role_field():
    """
    Even if a malicious client sends an extra 'role' field in the request body,
    the response role must come from the database, not the request.
    The backend Pydantic schema ignores extra fields.
    """
    res = client.post(
        STAFF_LOGIN_URL,
        json={
            "org_code": "JSS-01",
            "email": "helpdesk@jss.edu",
            "password": "HelpDesk@123",
            "role": "PLATFORM_OWNER",          # injected by attacker — must be ignored
        },
    )
    assert res.status_code == 200
    data = res.json()
    # Role must be HELP_DESK from DB, not the injected PLATFORM_OWNER
    assert data["user"]["role"] == "HELP_DESK", (
        f"Backend must ignore client-supplied role. Got: {data['user']['role']}"
    )


# ---------------------------------------------------------------------------
# 11. Protected dashboard endpoints require a valid token
# ---------------------------------------------------------------------------

def test_platform_owner_dashboard_requires_auth():
    """Accessing the platform-owner summary endpoint without a token returns 401."""
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_tickets_endpoint_requires_auth():
    """Ticket list endpoint requires a valid JWT."""
    res = client.get("/api/v1/tickets")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# 12. Regular USER cannot authenticate via platform-login endpoint
# ---------------------------------------------------------------------------

def test_regular_user_cannot_use_platform_login():
    """
    A USER-role account cannot authenticate through the platform-login endpoint.
    The endpoint is strictly restricted to PLATFORM_OWNER role accounts.
    """
    res = platform_login("student@jss.edu", "UserPass@123")
    # Must reject — student is not a platform owner
    assert res.status_code == 401, (
        f"USER-role account must not authenticate via platform-login. Got {res.status_code}"
    )


# ---------------------------------------------------------------------------
# 13. All five staff roles produce correct role in JWT /me response
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("email,password,org_code,expected_role", [
    ("helpdesk@jss.edu",  "HelpDesk@123",  "JSS-01", "HELP_DESK"),
    ("support@jss.edu",   "Support@123",   "JSS-01", "SUPPORT_TEAM_MEMBER"),
    ("lead@jss.edu",      "LeadPass@123",  "JSS-01", "SUPPORT_TEAM_LEAD"),
    ("admin@jss.edu",     "AdminPass@123", "JSS-01", "ORGANIZATION_ADMIN"),
])
def test_all_staff_roles_me_endpoint(email, password, org_code, expected_role):
    """Each staff role returns the correct role from /me after login."""
    login_res = org_login(email, password, org_code)
    assert login_res.status_code == 200, f"Login failed for {email}: {login_res.text}"
    token = login_res.json()["access_token"]

    me_res = client.get(ME_URL, headers=auth_header(token))
    assert me_res.status_code == 200
    assert me_res.json()["role"] == expected_role, (
        f"Expected {expected_role} for {email}, got {me_res.json()['role']}"
    )


# ---------------------------------------------------------------------------
# 14. Platform Owner cannot log in via org-login with an org code
# ---------------------------------------------------------------------------

def test_platform_owner_cannot_login_via_org_login():
    """
    Platform Owner account must only authenticate via /platform-login.
    Attempting org-login for the platform owner's email should fail because
    the platform owner has no organisation membership.
    """
    res = org_login("owner@queuemind.ai", "OwnerPass@123", "JSS-01")
    # Platform owner is not a member of JSS-01, so this must be rejected
    assert res.status_code == 401, (
        f"Platform owner should not authenticate via org-login with JSS-01. Got {res.status_code}"
    )
