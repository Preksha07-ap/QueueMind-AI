"""
Safe demo database seeding script for QueueMind AI.
Creates demonstration organisations, departments, support teams, and
demo accounts for all six roles with dummy credentials.

Run with:
    cd backend
    python scripts/seed_demo_data.py
"""

import sys
import os

# Ensure the backend directory is in the Python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.database.session import SessionLocal, engine
from app.database.base import Base, import_all_models
from app.core.security import get_password_hash
from app.models import (
    Organization,
    OrganizationType,
    Department,
    SupportTeam,
    IssueCategory,
    User,
    UserRole,
    AccountStatus,
)

import_all_models()


def seed_data():
    db: Session = SessionLocal()
    try:
        print("[*] Checking / Seeding Demo Organisations...")

        # 1. Primary Organization: JSS Academy
        jss_org = (
            db.query(Organization)
            .filter(Organization.code == "JSS-01")
            .first()
        )
        if not jss_org:
            jss_org = Organization(
                name="JSS Academy of Technical Education",
                code="JSS-01",
                slug="jss-ate",
                org_type=OrganizationType.COLLEGE,
                description="Engineering and technology campus helpdesk demo tenant",
                contact_email="helpdesk-admin@jss.edu",
                is_active=True,
            )
            db.add(jss_org)
            db.flush()
            print("    [+] Created Organization: JSS Academy (code: JSS-01, slug: jss-ate)")
        else:
            print("    [=] Organization JSS-01 already exists.")

        # 2. Secondary Organization for Multi-Tenant Isolation Testing: Apex Institute
        apex_org = (
            db.query(Organization)
            .filter(Organization.code == "APEX-01")
            .first()
        )
        if not apex_org:
            apex_org = Organization(
                name="Apex Institute of Technology",
                code="APEX-01",
                slug="apex-tech",
                org_type=OrganizationType.UNIVERSITY,
                description="Secondary tenant for multi-tenancy testing",
                contact_email="contact@apex.edu",
                is_active=True,
            )
            db.add(apex_org)
            db.flush()
            print("    [+] Created Organization: Apex Institute (code: APEX-01, slug: apex-tech)")
        else:
            print("    [=] Organization APEX-01 already exists.")

        # 3. Department for JSS
        dept = (
            db.query(Department)
            .filter(Department.organization_id == jss_org.id, Department.name == "IT Department")
            .first()
        )
        if not dept:
            dept = Department(
                organization_id=jss_org.id,
                name="IT Department",
                description="Information Technology & Campus Systems",
                is_active=True,
            )
            db.add(dept)
            db.flush()
            print("    [+] Created Department: IT Department")

        # 4. Support Team for JSS
        team = (
            db.query(SupportTeam)
            .filter(SupportTeam.organization_id == jss_org.id, SupportTeam.name == "Network Support")
            .first()
        )
        if not team:
            team = SupportTeam(
                organization_id=jss_org.id,
                department_id=dept.id,
                name="Network Support",
                description="Handles campus WiFi, LAN, and firewall connectivity",
                is_active=True,
            )
            db.add(team)
            db.flush()
            print("    [+] Created Support Team: Network Support")

        # 4b. Seed Issue Categories for JSS
        standard_categories = [
            ("Technical issues", "General technical and hardware/software assistance"),
            ("Examination issues", "Admit card, exam portal, marks, and hall ticket queries"),
            ("Admission issues", "Counseling, document submission, and enrollment status"),
            ("Fee and payment issues", "Tuition, hostel fees, refund, and payment gateway issues"),
            ("Network issues", "Campus Wi-Fi, Ethernet, VPN, and firewall connectivity"),
            ("Hardware issues", "Lab computer, projector, printer, and terminal malfunctions"),
            ("Software issues", "Academic software, licenses, OS installation, and development tools"),
            ("Account and access issues", "Student portal, email password resets, and LMS login issues"),
            ("Other organisational issues", "General administrative and facility inquiries"),
        ]
        for cat_name, cat_desc in standard_categories:
            existing_cat = (
                db.query(IssueCategory)
                .filter(IssueCategory.organization_id == jss_org.id, IssueCategory.name == cat_name)
                .first()
            )
            if not existing_cat:
                new_cat = IssueCategory(
                    organization_id=jss_org.id,
                    name=cat_name,
                    description=cat_desc,
                    department_id=dept.id,
                    support_team_id=team.id,
                    is_active=True,
                )
                db.add(new_cat)
                print(f"    [+] Created Issue Category: {cat_name}")

        # 5. Accounts for all six roles
        demo_accounts = [
            {
                "org_id": None,  # Platform Owner has no organisation
                "email": "owner@queuemind.ai",
                "password": "OwnerPass@123",
                "full_name": "Platform Master Admin",
                "role": UserRole.PLATFORM_OWNER,
                "dept_id": None,
                "team_id": None,
            },
            {
                "org_id": jss_org.id,
                "email": "admin@jss.edu",
                "password": "AdminPass@123",
                "full_name": "Organisation Admin",
                "role": UserRole.ORGANIZATION_ADMIN,
                "dept_id": dept.id,
                "team_id": None,
            },
            {
                "org_id": jss_org.id,
                "email": "helpdesk@jss.edu",
                "password": "HelpDesk@123",
                "full_name": "Priya Sharma",
                "role": UserRole.HELP_DESK,
                "dept_id": dept.id,
                "team_id": None,
            },
            {
                "org_id": jss_org.id,
                "email": "lead@jss.edu",
                "password": "LeadPass@123",
                "full_name": "Team Lead",
                "role": UserRole.SUPPORT_TEAM_LEAD,
                "dept_id": dept.id,
                "team_id": team.id,
            },
            {
                "org_id": jss_org.id,
                "email": "ananya@jss.edu",
                "password": "Ananya@123",
                "full_name": "Ananya Roy",
                "role": UserRole.SUPPORT_TEAM_MEMBER,
                "dept_id": dept.id,
                "team_id": team.id,
            },
            {
                "org_id": jss_org.id,
                "email": "vikram@jss.edu",
                "password": "Vikram@123",
                "full_name": "Vikram",
                "role": UserRole.SUPPORT_TEAM_MEMBER,
                "dept_id": dept.id,
                "team_id": team.id,
            },
            {
                "org_id": jss_org.id,
                "email": "support@jss.edu",
                "password": "Support@123",
                "full_name": "Generic Support Engineer",
                "role": UserRole.SUPPORT_TEAM_MEMBER,
                "dept_id": dept.id,
                "team_id": team.id,
            },
            {
                "org_id": jss_org.id,
                "email": "student@jss.edu",
                "password": "UserPass@123",
                "full_name": "Rahul Verma (Student)",
                "role": UserRole.USER,
                "dept_id": None,
                "team_id": None,
            },
            # Apex Institute User & Admin for cross-tenant verification
            {
                "org_id": apex_org.id,
                "email": "admin@apex.edu",
                "password": "ApexAdmin@123",
                "full_name": "Apex Org Administrator",
                "role": UserRole.ORGANIZATION_ADMIN,
                "dept_id": None,
                "team_id": None,
            },
            {
                "org_id": apex_org.id,
                "email": "student@apex.edu",
                "password": "ApexUser@123",
                "full_name": "Suresh Kumar (Apex Student)",
                "role": UserRole.USER,
                "dept_id": None,
                "team_id": None,
            },
        ]

        print("[*] Seeding Demo User Accounts for All 6 Roles...")
        for acc in demo_accounts:
            existing_user = (
                db.query(User)
                .filter(
                    User.organization_id == acc["org_id"],
                    User.email == acc["email"],
                )
                .first()
            )
            if not existing_user:
                new_user = User(
                    organization_id=acc["org_id"],
                    full_name=acc["full_name"],
                    email=acc["email"],
                    hashed_password=get_password_hash(acc["password"]),
                    role=acc["role"],
                    department_id=acc["dept_id"],
                    support_team_id=acc.get("team_id"),
                    account_status=AccountStatus.ACTIVE,
                )
                db.add(new_user)
                print(f"    [+] Created: {acc['email']} | Role: {acc['role'].value} | Org: {acc['org_id']}")
            else:
                if acc.get("team_id") and existing_user.support_team_id != acc.get("team_id"):
                    existing_user.support_team_id = acc.get("team_id")
                    print(f"    [~] Updated team for {acc['email']}: {acc.get('team_id')}")
                print(f"    [=] User already exists: {acc['email']}")

        db.commit()
        print("\n[SUCCESS] Demo seeding complete! All 6 roles are ready for testing.")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Failed to seed demo data: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
