"""
Phase 3 — Authentication, Multi-Tenancy & RBAC Test Suite
=========================================================
Tests:
  1. Successful login (organisation user & platform owner)
  2. Incorrect password handling (401)
  3. Unknown organisation handling (401 without leakage)
  4. Inactive / suspended user handling (403)
  5. Expired and invalid JWT handling (401)
  6. Current user endpoint (/me) & logout
  7. All six roles authentication & profile inspection
  8. Role-based access control enforcement (403 for unauthorized roles)
  9. User accessing own organisation records (200)
 10. Cross-tenant access attempt (Org A user accesses Org B -> 403)
 11. Org admin attempting to create a Platform Owner (403 / 422 blocked)
 12. Duplicate email within same organisation (400)
 13. Public self-registration (locked strictly to USER role)

Run with:
    cd backend
    python -m pytest tests/test_phase3_auth.py -v
"""

import uuid
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.security import create_access_token, get_password_hash
from app.database.session import SessionLocal
from app.models import (
    AccountStatus,
    Organization,
    OrganizationType,
    User,
    UserRole,
)

client = TestClient(app)


# ── Helpers for test setup ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def seeded_db():
    """Ensure database has standard test tenants and seed accounts."""
    db: Session = SessionLocal()
    try:
        # 1. Organization A
        org_a = db.query(Organization).filter(Organization.code == "TEST-A").first()
        if not org_a:
            org_a = Organization(
                name="Test Organization Alpha",
                code="TEST-A",
                slug="test-alpha",
                org_type=OrganizationType.COLLEGE,
                contact_email="admin@test-alpha.edu",
                is_active=True,
            )
            db.add(org_a)
            db.flush()

        # 2. Organization B
        org_b = db.query(Organization).filter(Organization.code == "TEST-B").first()
        if not org_b:
            org_b = Organization(
                name="Test Organization Beta",
                code="TEST-B",
                slug="test-beta",
                org_type=OrganizationType.UNIVERSITY,
                contact_email="admin@test-beta.edu",
                is_active=True,
            )
            db.add(org_b)
            db.flush()

        # 3. Inactive Organization
        org_inactive = db.query(Organization).filter(Organization.code == "TEST-INACTIVE").first()
        if not org_inactive:
            org_inactive = Organization(
                name="Inactive Org",
                code="TEST-INACTIVE",
                slug="test-inactive",
                org_type=OrganizationType.OTHER,
                contact_email="inactive@test.edu",
                is_active=False,
            )
            db.add(org_inactive)
            db.flush()

        # 4. Create accounts for testing
        test_users = [
            # Platform Owner (no org)
            {"org_id": None, "email": "test_owner@qm.ai", "pw": "OwnerSecret!1", "role": UserRole.PLATFORM_OWNER, "status": AccountStatus.ACTIVE},
            # Org A Admin
            {"org_id": org_a.id, "email": "admin@alpha.edu", "pw": "AlphaAdmin!1", "role": UserRole.ORGANIZATION_ADMIN, "status": AccountStatus.ACTIVE},
            # Org A Help Desk
            {"org_id": org_a.id, "email": "helpdesk@alpha.edu", "pw": "HelpDesk!1", "role": UserRole.HELP_DESK, "status": AccountStatus.ACTIVE},
            # Org A Team Lead
            {"org_id": org_a.id, "email": "lead@alpha.edu", "pw": "TeamLead!1", "role": UserRole.SUPPORT_TEAM_LEAD, "status": AccountStatus.ACTIVE},
            # Org A Support Member
            {"org_id": org_a.id, "email": "support@alpha.edu", "pw": "SupportMember!1", "role": UserRole.SUPPORT_TEAM_MEMBER, "status": AccountStatus.ACTIVE},
            # Org A Student/User
            {"org_id": org_a.id, "email": "student@alpha.edu", "pw": "StudentPass!1", "role": UserRole.USER, "status": AccountStatus.ACTIVE},
            # Org A Inactive User
            {"org_id": org_a.id, "email": "suspended@alpha.edu", "pw": "Suspended!1", "role": UserRole.USER, "status": AccountStatus.SUSPENDED},
            # Org B User
            {"org_id": org_b.id, "email": "student@beta.edu", "pw": "BetaStudent!1", "role": UserRole.USER, "status": AccountStatus.ACTIVE},
            # Org B Admin
            {"org_id": org_b.id, "email": "admin@beta.edu", "pw": "BetaAdmin!1", "role": UserRole.ORGANIZATION_ADMIN, "status": AccountStatus.ACTIVE},
        ]

        for u in test_users:
            existing = db.query(User).filter(User.organization_id == u["org_id"], User.email == u["email"]).first()
            if not existing:
                user_obj = User(
                    organization_id=u["org_id"],
                    full_name=f"User {u['email']}",
                    email=u["email"],
                    hashed_password=get_password_hash(u["pw"]),
                    role=u["role"],
                    account_status=u["status"],
                )
                db.add(user_obj)

        db.commit()
        yield {"org_a": org_a, "org_b": org_b, "org_inactive": org_inactive}
    finally:
        db.close()


def get_token_for(email: str, password: str, org_code: str | None = None) -> str:
    """Helper to perform login and extract bearer token."""
    payload = {"email": email, "password": password}
    if org_code:
        payload["org_code"] = org_code
    resp = client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Successful Login
# ─────────────────────────────────────────────────────────────────────────────

def test_successful_login_org_user(seeded_db):
    """Organisation user can log in with valid org code, email, and password."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "org_code": "TEST-A",
            "email": "student@alpha.edu",
            "password": "StudentPass!1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "student@alpha.edu"
    assert data["user"]["role"] == "USER"
    assert data["user"]["organization_code"] == "TEST-A"


def test_successful_login_using_slug(seeded_db):
    """Users can log in using either organisation code or slug."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "org_code": "test-alpha",  # using slug instead of code
            "email": "student@alpha.edu",
            "password": "StudentPass!1",
        },
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "student@alpha.edu"


def test_successful_platform_owner_login(seeded_db):
    """Platform owner can log in without providing an organisation code."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test_owner@qm.ai",
            "password": "OwnerSecret!1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "PLATFORM_OWNER"
    assert data["user"]["organization_id"] is None


def test_dedicated_platform_login_endpoint(seeded_db):
    """Direct platform-login endpoint works for Platform Owners."""
    response = client.post(
        "/api/v1/auth/platform-login",
        json={
            "email": "test_owner@qm.ai",
            "password": "OwnerSecret!1",
        },
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "PLATFORM_OWNER"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Incorrect Password
# ─────────────────────────────────────────────────────────────────────────────

def test_login_incorrect_password(seeded_db):
    """Incorrect password returns 401 Unauthorized."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "org_code": "TEST-A",
            "email": "student@alpha.edu",
            "password": "WrongPassword!999",
        },
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Unknown Organisation
# ─────────────────────────────────────────────────────────────────────────────

def test_login_unknown_organisation(seeded_db):
    """Unknown organisation code returns 401 without revealing email status."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "org_code": "NONEXISTENT-ORG-999",
            "email": "student@alpha.edu",
            "password": "StudentPass!1",
        },
    )
    assert response.status_code == 401
    assert "Invalid organisation code" in response.json()["detail"]


def test_login_inactive_organisation(seeded_db):
    """Attempting to log in to an inactive organisation returns 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "org_code": "TEST-INACTIVE",
            "email": "student@alpha.edu",
            "password": "StudentPass!1",
        },
    )
    assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 4. Inactive User
# ─────────────────────────────────────────────────────────────────────────────

def test_login_inactive_user(seeded_db):
    """Suspended or inactive account returns 403 Forbidden."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "org_code": "TEST-A",
            "email": "suspended@alpha.edu",
            "password": "Suspended!1",
        },
    )
    assert response.status_code == 403
    assert "suspended" in response.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Expired or Invalid JWT
# ─────────────────────────────────────────────────────────────────────────────

def test_auth_me_missing_token():
    """Requesting protected endpoint without token returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "missing" in response.json()["detail"].lower()


def test_auth_me_invalid_token():
    """Requesting protected endpoint with garbage token returns 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt-token"},
    )
    assert response.status_code == 401
    assert "credentials" in response.json()["detail"].lower()


def test_auth_me_expired_token(seeded_db):
    """Token that has expired returns 401 with explicit expiration detail."""
    db = SessionLocal()
    user = db.query(User).filter(User.email == "student@alpha.edu").first()
    db.close()

    # Create expired token (-10 minutes)
    expired_token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=-10),
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Current User (/me) and Logout
# ─────────────────────────────────────────────────────────────────────────────

def test_auth_me_success(seeded_db):
    """Valid token allows retrieving current user profile."""
    token = get_token_for("student@alpha.edu", "StudentPass!1", "TEST-A")
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "student@alpha.edu"
    assert data["role"] == "USER"
    assert data["organization_code"] == "TEST-A"


def test_logout_endpoint(seeded_db):
    """Logout endpoint completes successfully."""
    token = get_token_for("student@alpha.edu", "StudentPass!1", "TEST-A")
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "successfully" in response.json()["message"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# 7. Each of the Six Roles
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "email,pw,org_code,expected_role",
    [
        ("student@alpha.edu", "StudentPass!1", "TEST-A", "USER"),
        ("helpdesk@alpha.edu", "HelpDesk!1", "TEST-A", "HELP_DESK"),
        ("support@alpha.edu", "SupportMember!1", "TEST-A", "SUPPORT_TEAM_MEMBER"),
        ("lead@alpha.edu", "TeamLead!1", "TEST-A", "SUPPORT_TEAM_LEAD"),
        ("admin@alpha.edu", "AlphaAdmin!1", "TEST-A", "ORGANIZATION_ADMIN"),
        ("test_owner@qm.ai", "OwnerSecret!1", None, "PLATFORM_OWNER"),
    ],
)
def test_all_six_roles_authentication(seeded_db, email, pw, org_code, expected_role):
    """All 6 roles can log in and have their role accurately returned."""
    payload = {"email": email, "password": pw}
    if org_code:
        payload["org_code"] = org_code

    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    assert response.json()["user"]["role"] == expected_role


# ─────────────────────────────────────────────────────────────────────────────
# 8. Role-Based Endpoint Access Control
# ─────────────────────────────────────────────────────────────────────────────

def test_user_cannot_access_user_list(seeded_db):
    """Regular USER cannot list users (403 Forbidden)."""
    token = get_token_for("student@alpha.edu", "StudentPass!1", "TEST-A")
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_user_cannot_create_users(seeded_db):
    """Regular USER cannot create new users (403 Forbidden)."""
    token = get_token_for("student@alpha.edu", "StudentPass!1", "TEST-A")
    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Unauthorized User",
            "email": "unauth@alpha.edu",
            "password": "Password!123",
            "role": "USER",
        },
    )
    assert response.status_code == 403


def test_org_admin_cannot_create_organizations(seeded_db):
    """Only PLATFORM_OWNER can create organisations; Org Admin gets 403."""
    token = get_token_for("admin@alpha.edu", "AlphaAdmin!1", "TEST-A")
    response = client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Forbidden University",
            "code": "FORBID-01",
            "slug": "forbid-uni",
            "contact_email": "admin@forbid.edu",
        },
    )
    assert response.status_code == 403


def test_platform_owner_can_create_organization(seeded_db):
    """PLATFORM_OWNER can create new tenant organisations."""
    uid = uuid.uuid4().hex[:6].upper()
    token = get_token_for("test_owner@qm.ai", "OwnerSecret!1")
    response = client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"Gamma State University {uid}",
            "code": f"GAMMA-{uid}",
            "slug": f"gamma-{uid.lower()}",
            "org_type": "UNIVERSITY",
            "contact_email": f"admin@gamma-{uid.lower()}.edu",
        },
    )
    assert response.status_code == 201
    assert response.json()["code"] == f"GAMMA-{uid}"


# ─────────────────────────────────────────────────────────────────────────────
# 9. User Accessing Own Organisation Records
# ─────────────────────────────────────────────────────────────────────────────

def test_user_accessing_own_org_records(seeded_db):
    """User in Org A can read Org A's details."""
    org_a = seeded_db["org_a"]
    token = get_token_for("student@alpha.edu", "StudentPass!1", "TEST-A")
    response = client.get(
        f"/api/v1/organizations/{org_a.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == org_a.id
    assert response.json()["code"] == "TEST-A"


# ─────────────────────────────────────────────────────────────────────────────
# 10. Multi-Tenant Isolation (Org A User Accesses Org B -> 403)
# ─────────────────────────────────────────────────────────────────────────────

def test_cross_tenant_access_denied(seeded_db):
    """
    A user from Organisation A attempting to access Organisation B's records
    must be blocked with 403 Forbidden.
    """
    org_b = seeded_db["org_b"]
    token_a = get_token_for("student@alpha.edu", "StudentPass!1", "TEST-A")

    response = client.get(
        f"/api/v1/organizations/{org_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 403
    assert "another organisation" in response.json()["detail"].lower()


def test_org_admin_list_users_isolated(seeded_db):
    """Organisation Admin only sees users within their own organisation."""
    token_a = get_token_for("admin@alpha.edu", "AlphaAdmin!1", "TEST-A")
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 200
    users = response.json()
    # Confirm every user returned belongs to Org A
    org_a = seeded_db["org_a"]
    for u in users:
        assert u["organization_id"] == org_a.id
        assert not u["email"].endswith("@beta.edu")


# ─────────────────────────────────────────────────────────────────────────────
# 11. Org Admin Cannot Create Platform Owner
# ─────────────────────────────────────────────────────────────────────────────

def test_org_admin_cannot_create_platform_owner(seeded_db):
    """
    An Organisation Administrator must NOT be able to provision a
    PLATFORM_OWNER account.
    """
    token = get_token_for("admin@alpha.edu", "AlphaAdmin!1", "TEST-A")
    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Rogue Admin",
            "email": "rogue@alpha.edu",
            "password": "Password!123",
            "role": "PLATFORM_OWNER",
        },
    )
    # Blocked by Pydantic validator (422) or route logic (403)
    assert response.status_code in [403, 422]


# ─────────────────────────────────────────────────────────────────────────────
# 12. Duplicate Email Within Same Organisation
# ─────────────────────────────────────────────────────────────────────────────

def test_duplicate_email_same_org_rejected(seeded_db):
    """Attempting to register a duplicate email in the same organisation returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "org_code": "TEST-A",
            "full_name": "Duplicate Student",
            "email": "student@alpha.edu",  # already exists in TEST-A
            "password": "NewPassword!1",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_same_email_in_different_org_allowed(seeded_db):
    """
    Multi-tenant isolation: The exact same email address CAN exist
    in two different organisations without collision.
    """
    uid = uuid.uuid4().hex[:6]
    shared_email = f"shared_{uid}@crosscampus.edu"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "org_code": "TEST-B",  # In Org B
            "full_name": "Student in Beta",
            "email": shared_email,
            "password": "Password!123",
        },
    )
    assert response.status_code == 201

    response2 = client.post(
        "/api/v1/auth/register",
        json={
            "org_code": "TEST-A",  # In Org A
            "full_name": "Student in Alpha",
            "email": shared_email,
            "password": "Password!123",
        },
    )
    assert response2.status_code == 201
    assert response.json()["organization_id"] != response2.json()["organization_id"]


# ─────────────────────────────────────────────────────────────────────────────
# 13. Public Self-Registration
# ─────────────────────────────────────────────────────────────────────────────

def test_public_registration_success(seeded_db):
    """Public registration creates a standard USER in the specified organisation."""
    uid = uuid.uuid4().hex[:6]
    fresh_email = f"fresh_{uid}@alpha.edu"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "org_code": "TEST-A",
            "full_name": "New Enrolled Student",
            "email": fresh_email,
            "password": "FreshPassword!1",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "USER"
    assert data["email"] == fresh_email
    assert data["organization_code"] == "TEST-A"
