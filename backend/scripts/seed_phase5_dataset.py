"""
Phase 5 Dataset Seeder for QueueMind AI.
Builds a realistic multi-tenant dataset for 8 organizations:
1. SJC (SJC-01)
2. VBC (VBC-01)
3. GSSSIETW (GSSSIETW-01)
4. MIT (MIT-01)
5. Meesho (MEESHO-01)
6. Freshworks (FRESHWORKS-01)
7. Razorpay (RAZORPAY-01)
8. Zepto (ZEPTO-01)

Ensures:
- Idempotent execution (can be run repeatedly safely).
- Strict multi-tenant isolation.
- Realistic departments, support teams, categories, staff, users, tickets, and KB articles.
- Marks all seeded demo entities with is_demo = True.
- Ingests all KB articles and verified historical tickets into Qdrant vector store.
"""

import os
import sys
import json
from datetime import datetime, timedelta, timezone

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.database.base import import_all_models
from app.core.security import get_password_hash
from app.models.organization import Organization, OrganizationType
from app.models.department import Department
from app.models.support_team import SupportTeam
from app.models.issue_category import IssueCategory
from app.models.user import User, UserRole, AccountStatus
from app.models.ticket import Ticket, TicketPriority, TicketSource, TicketStatus
from app.models.ticket_comment import TicketComment
from app.models.ticket_history import TicketHistory
from app.models.knowledge_base import KnowledgeBase, KBApprovalStatus
from app.ai.vector_store import vector_store

import_all_models()

DEFAULT_PASSWORD = "Demo@123"

# ─────────────────────────────────────────────────────────────────────────────
# 1. Organization Definitions
# ─────────────────────────────────────────────────────────────────────────────
ORGANIZATIONS = [
    {
        "name": "SJC",
        "code": "SJC-01",
        "slug": "sjc",
        "org_type": OrganizationType.COLLEGE,
        "description": "SJC Institute of Technology campus helpdesk",
        "contact_email": "admin@sjc.edu",
        "domain": "sjc.edu",
        "is_college": True,
    },
    {
        "name": "VBC",
        "code": "VBC-01",
        "slug": "vbc",
        "org_type": OrganizationType.COLLEGE,
        "description": "Vidya Bharathi College academic and administrative helpdesk",
        "contact_email": "admin@vbc.edu",
        "domain": "vbc.edu",
        "is_college": True,
    },
    {
        "name": "GSSSIETW",
        "code": "GSSSIETW-01",
        "slug": "gsssietw",
        "org_type": OrganizationType.COLLEGE,
        "description": "GSSS Institute of Engineering & Technology for Women support portal",
        "contact_email": "admin@gsssietw.edu",
        "domain": "gsssietw.edu",
        "is_college": True,
    },
    {
        "name": "MIT",
        "code": "MIT-01",
        "slug": "mit",
        "org_type": OrganizationType.UNIVERSITY,
        "description": "Mysore Institute of Technology central IT helpdesk",
        "contact_email": "admin@mit.edu",
        "domain": "mit.edu",
        "is_college": True,
    },
    {
        "name": "Meesho",
        "code": "MEESHO-01",
        "slug": "meesho",
        "org_type": OrganizationType.ENTERPRISE,
        "description": "Meesho e-commerce platform and internal IT operations",
        "contact_email": "admin@meesho.com",
        "domain": "meesho.com",
        "is_college": False,
    },
    {
        "name": "Freshworks",
        "code": "FRESHWORKS-01",
        "slug": "freshworks",
        "org_type": OrganizationType.ENTERPRISE,
        "description": "Freshworks SaaS product engineering and corporate IT desk",
        "contact_email": "admin@freshworks.com",
        "domain": "freshworks.com",
        "is_college": False,
    },
    {
        "name": "Razorpay",
        "code": "RAZORPAY-01",
        "slug": "razorpay",
        "org_type": OrganizationType.ENTERPRISE,
        "description": "Razorpay payments infra and engineering operations desk",
        "contact_email": "admin@razorpay.com",
        "domain": "razorpay.com",
        "is_college": False,
    },
    {
        "name": "Zepto",
        "code": "ZEPTO-01",
        "slug": "zepto",
        "org_type": OrganizationType.ENTERPRISE,
        "description": "Zepto quick-commerce delivery infra and dark store IT",
        "contact_email": "admin@zepto.com",
        "domain": "zepto.com",
        "is_college": False,
    },
]

STAFF_NAMES = [
    "Aarav Sharma",
    "Diya Patel",
    "Kavya Rao",
    "Rohan Gupta",
    "Neha Singh",
    "Aditya Verma",
    "Meera Iyer",
    "Karan Nair",
    "Pooja Joshi",
    "Siddharth Jain",
]


def seed_departments_and_teams(db: Session, org: Organization, is_college: bool):
    """Creates standard departments and support teams for an organisation."""
    if is_college:
        dept_defs = [
            ("IT & Systems", "Campus network, servers, and computer labs", ["Network Support", "Hardware Maintenance", "ERP Support"]),
            ("Academic & Examinations", "Curriculum, timetables, and exam operations", ["Examination Cell"]),
            ("Finance & Accounts", "Fee collections, payroll, and refunds", ["Fee & Accounts Desk"]),
            ("Admissions & Registrar", "Student enrollment and certificates", ["Admissions Support"]),
            ("Campus Facilities", "Hostels, power, and physical infrastructure", ["Facilities Helpdesk"]),
        ]
        cat_defs = [
            ("Examination issues", "Admit card, exam portal, marks, and hall ticket queries", "Academic & Examinations", "Examination Cell"),
            ("Fee and payment issues", "Tuition, hostel fees, refund, and payment gateway issues", "Finance & Accounts", "Fee & Accounts Desk"),
            ("Admission issues", "Counseling, document submission, and enrollment status", "Admissions & Registrar", "Admissions Support"),
            ("Network issues", "Campus Wi-Fi, Ethernet, VPN, and firewall connectivity", "IT & Systems", "Network Support"),
            ("Account and access issues", "Student portal, email password resets, and LMS login issues", "IT & Systems", "ERP Support"),
            ("Software issues", "Academic software, licenses, OS installation, and development tools", "IT & Systems", "ERP Support"),
            ("Technical issues", "General technical and hardware/software assistance", "IT & Systems", "Hardware Maintenance"),
            ("Hardware issues", "Lab computer, projector, printer, and terminal malfunctions", "IT & Systems", "Hardware Maintenance"),
            ("Other organisational issues", "General administrative and facility inquiries", "Campus Facilities", "Facilities Helpdesk"),
        ]
    else:
        dept_defs = [
            ("Engineering & Infrastructure", "Cloud platforms, microservices, and databases", ["SRE & Cloud Infra", "Platform Operations"]),
            ("Core Platform & Payments", "Transaction pipelines, checkout, and gateway APIs", ["Payment Gateway Support"]),
            ("DevOps & Security", "CI/CD, IAM, and corporate information security", ["Security & IAM"]),
            ("Workplace IT & Facilities", "Employee laptops, office networks, and SaaS access", ["Workplace IT Support"]),
            ("Operations & Logistics", "Dark store systems, seller tools, and fulfillment", ["Operations Tech Desk"]),
        ]
        cat_defs = [
            ("Critical Service Outages", "Production service degradation, P0 outages, and API downtime", "Engineering & Infrastructure", "SRE & Cloud Infra"),
            ("Payment Gateway Issues", "Payment webhook failures, checkout drop-offs, and refund latency", "Core Platform & Payments", "Payment Gateway Support"),
            ("Cloud Infrastructure", "Kubernetes pods, Redis clusters, AWS/GCP connectivity", "Engineering & Infrastructure", "SRE & Cloud Infra"),
            ("Network & VPN", "Corporate VPN, Zscaler, office Wi-Fi, and SD-WAN issues", "Workplace IT & Facilities", "Workplace IT Support"),
            ("SSO & Access Control", "Okta SAML, Google Workspace, GitHub org permissions", "DevOps & Security", "Security & IAM"),
            ("Developer Tooling", "CI/CD runner timeouts, Docker registry, dev environments", "Engineering & Infrastructure", "Platform Operations"),
            ("Hardware & Workstation", "MacBook MDM enrollment, monitor peripherals, dock issues", "Workplace IT & Facilities", "Workplace IT Support"),
            ("General Inquiries", "Internal IT asset policies, software licensing requests", "Operations & Logistics", "Operations Tech Desk"),
        ]

    created_depts = {}
    created_teams = {}

    for d_name, d_desc, team_names in dept_defs:
        dept = db.query(Department).filter(
            Department.organization_id == org.id,
            Department.name == d_name,
        ).first()
        if not dept:
            dept = Department(
                organization_id=org.id,
                name=d_name,
                description=d_desc,
                is_active=True,
            )
            db.add(dept)
            db.flush()
        created_depts[d_name] = dept

        for t_name in team_names:
            team = db.query(SupportTeam).filter(
                SupportTeam.organization_id == org.id,
                SupportTeam.name == t_name,
            ).first()
            if not team:
                team = SupportTeam(
                    organization_id=org.id,
                    department_id=dept.id,
                    name=t_name,
                    description=f"Handles {t_name} issues for {org.name}",
                    is_active=True,
                )
                db.add(team)
                db.flush()
            created_teams[t_name] = team

    # Create Categories
    for c_name, c_desc, target_dept_name, target_team_name in cat_defs:
        cat = db.query(IssueCategory).filter(
            IssueCategory.organization_id == org.id,
            IssueCategory.name == c_name,
        ).first()
        dept_id = created_depts.get(target_dept_name).id if target_dept_name in created_depts else None
        team_id = created_teams.get(target_team_name).id if target_team_name in created_teams else None

        if not cat:
            cat = IssueCategory(
                organization_id=org.id,
                name=c_name,
                description=c_desc,
                department_id=dept_id,
                support_team_id=team_id,
                is_active=True,
            )
            db.add(cat)
            db.flush()

    return created_depts, created_teams


def seed_users_and_staff(db: Session, org: Organization, depts: dict, teams: dict, domain: str, is_college: bool):
    """Creates 1 Org Admin, 2 Help Desk, 1 Team Lead, 10 Support Team Members, and 12 Users."""
    hashed_pwd = get_password_hash(DEFAULT_PASSWORD)
    primary_team = list(teams.values())[0] if teams else None
    primary_dept = list(depts.values())[0] if depts else None

    # 1. Organization Admin
    admin_email = f"admin@{domain}"
    admin_user = db.query(User).filter(User.email == admin_email).first()
    if not admin_user:
        admin_user = User(
            organization_id=org.id,
            email=admin_email,
            hashed_password=hashed_pwd,
            full_name=f"{org.name} Admin",
            role=UserRole.ORGANIZATION_ADMIN,
            department_id=primary_dept.id if primary_dept else None,
            account_status=AccountStatus.ACTIVE,
            is_demo=True,
        )
        db.add(admin_user)
        db.flush()

    # 2. Help Desk Staff (2 accounts)
    helpdesk_accounts = []
    hd1_email = f"helpdesk1@{domain}"
    hd1 = db.query(User).filter(User.email == hd1_email).first()
    if not hd1:
        hd1 = User(
            organization_id=org.id,
            email=hd1_email,
            hashed_password=hashed_pwd,
            full_name=f"Priya Sharma ({org.name})",
            role=UserRole.HELP_DESK,
            department_id=primary_dept.id if primary_dept else None,
            account_status=AccountStatus.ACTIVE,
            is_demo=True,
        )
        db.add(hd1)
        db.flush()
    helpdesk_accounts.append(hd1)

    hd2_email = f"helpdesk2@{domain}"
    hd2 = db.query(User).filter(User.email == hd2_email).first()
    if not hd2:
        hd2 = User(
            organization_id=org.id,
            email=hd2_email,
            hashed_password=hashed_pwd,
            full_name=f"Rahul Verma ({org.name})",
            role=UserRole.HELP_DESK,
            department_id=primary_dept.id if primary_dept else None,
            account_status=AccountStatus.ACTIVE,
            is_demo=True,
        )
        db.add(hd2)
        db.flush()
    helpdesk_accounts.append(hd2)

    # 3. Support Team Lead
    lead_email = f"lead@{domain}"
    lead_user = db.query(User).filter(User.email == lead_email).first()
    if not lead_user:
        lead_user = User(
            organization_id=org.id,
            email=lead_email,
            hashed_password=hashed_pwd,
            full_name=f"Team Lead ({org.name})",
            role=UserRole.SUPPORT_TEAM_LEAD,
            department_id=primary_dept.id if primary_dept else None,
            support_team_id=primary_team.id if primary_team else None,
            account_status=AccountStatus.ACTIVE,
            is_demo=True,
        )
        db.add(lead_user)
        db.flush()

    # 4. 10 Support Team Members
    team_list = list(teams.values())
    staff_members = []
    for idx, name in enumerate(STAFF_NAMES, start=1):
        staff_email = f"staff{idx}@{domain}"
        assigned_team = team_list[(idx - 1) % len(team_list)] if team_list else None
        staff_user = db.query(User).filter(User.email == staff_email).first()
        if not staff_user:
            staff_user = User(
                organization_id=org.id,
                email=staff_email,
                hashed_password=hashed_pwd,
                full_name=f"{name} ({org.name})",
                role=UserRole.SUPPORT_TEAM_MEMBER,
                department_id=assigned_team.department_id if assigned_team else None,
                support_team_id=assigned_team.id if assigned_team else None,
                account_status=AccountStatus.ACTIVE,
                is_demo=True,
            )
            db.add(staff_user)
            db.flush()
        staff_members.append(staff_user)

    # 5. 12 End Users (Students or Employees)
    end_users = []
    prefix = "student" if is_college else "emp"
    title_prefix = "Student" if is_college else "Employee"
    for idx in range(1, 13):
        u_email = f"{prefix}{idx}@{domain}"
        u_name = f"{title_prefix} {idx} ({org.name})"
        user_record = db.query(User).filter(User.email == u_email).first()
        if not user_record:
            user_record = User(
                organization_id=org.id,
                email=u_email,
                hashed_password=hashed_pwd,
                full_name=u_name,
                role=UserRole.USER,
                account_status=AccountStatus.ACTIVE,
                is_demo=True,
            )
            db.add(user_record)
            db.flush()
        end_users.append(user_record)

    return admin_user, helpdesk_accounts, lead_user, staff_members, end_users


def seed_knowledge_base(db: Session, org: Organization, is_college: bool, author_id: int):
    """Seeds 6 approved authoritative KB documents and 1 unapproved draft KB per organisation."""
    if is_college:
        kb_data = [
            {
                "title": f"[{org.name}] Student Portal Hall Ticket Download Timeout Troubleshooting",
                "problem": "Students experience 504 Gateway Timeout or blank PDF when attempting to download semester examination hall tickets 24 hours prior to exams.",
                "solution": "1. Verify candidate admit card status in the academic database.\n2. Invalidate Redis auth session cache on the examination portal cluster.\n3. Increase FastCGI timeout to 120s on reverse proxy.\n4. Re-generate PDF blob from candidate records if hash mismatch occurs.",
                "symptoms": "504 Gateway Timeout, incomplete PDF download, admit card button disabled.",
                "possible_causes": "Heavy connection concurrency on portal backend, stale session locks in Redis, slow database query on student eligibility table.",
                "troubleshooting_steps": "1. Check server error logs: tail -n 100 /var/log/nginx/exam_portal_error.log.\n2. Invalidate cache: redis-cli del student_session_{id}.\n3. Ensure candidate eligibility flag is set to 1.",
                "verified_resolution": "Flushed Redis cache cluster, increased FastCGI timeout to 120s, and re-indexed admit card pdf blob store.",
                "tags": "examination,hall-ticket,portal-timeout,redis,nginx",
                "approved": True,
            },
            {
                "title": f"[{org.name}] Campus Wi-Fi 802.1X Certificate Renewal and Authentication Failure",
                "problem": "Students and faculty unable to connect to campus 802.1X secure SSID after root certificate expiry. Devices prompt for credentials continuously.",
                "solution": "1. Install the updated DigiCert Global Root G2 certificate on the user device.\n2. Forget the network SSID and reconnect.\n3. Select PEAP with MSCHAPv2 and set domain to campus authentication realm.",
                "symptoms": "Repeated password prompts, 'Could not authenticate' error on Android/iOS/Windows.",
                "possible_causes": "Client device caching expired intermediate CA certificate or radius server certificate mismatch.",
                "troubleshooting_steps": "1. Check FreeRadius logs for Auth-Reject packets.\n2. Provide students with the captive portal download link for the updated certificate profile.",
                "verified_resolution": "Distributed updated CA profile via onboarding portal and updated RADIUS server certificate bundle.",
                "tags": "wifi,network,radius,802.1x,certificate",
                "approved": True,
            },
            {
                "title": f"[{org.name}] Fee Payment Gateway Reconciliation and Pending Receipt Resolution",
                "problem": "Tuition or examination fee deducted from student bank account via UPI/NetBanking, but portal shows status 'PENDING' with no receipt.",
                "solution": "1. Initiate server-to-server gateway dual-verification query using merchant transaction ID.\n2. If gateway reports 'SUCCESS', update fee ledger entry to 'PAID' and generate digital receipt.\n3. If transaction failed, trigger auto-refund advice to beneficiary within 3 business days.",
                "symptoms": "Money debited, fee portal pending status, no hall ticket unlocked.",
                "possible_causes": "Dropped webhook callback from payment aggregator, bank server timeout.",
                "troubleshooting_steps": "1. Query payment aggregator API: GET /v1/payments/{tx_id}.\n2. Replay webhook manually if status is 'captured'.",
                "verified_resolution": "Executed manual webhook replay against payment gateway; verified status captured and generated student receipt.",
                "tags": "fee,payment,upi,reconciliation,receipt",
                "approved": True,
            },
            {
                "title": f"[{org.name}] Library RFID Scanner & Turnstile Gate Connectivity",
                "problem": "Automated RFID checkout kiosks and turnstile entry readers fail to scan student smart cards, causing long queues.",
                "solution": "1. Power cycle RFID reader controller module.\n2. Check TCP socket connection to KOHA library management server.\n3. Verify SIP2 protocol daemon status.",
                "symptoms": "RFID reader red LED blinking, reader displays 'Server Offline'.",
                "possible_causes": "SIP2 service crashed on KOHA server, network switch port auto-negotiation failure.",
                "troubleshooting_steps": "1. Restart SIP2 daemon: systemctl restart koha-sip2-daemon.\n2. Ping RFID controller IP from server.",
                "verified_resolution": "Restarted SIP2 protocol daemon on Koha server and reconnected switch patch cable.",
                "tags": "library,rfid,koha,turnstile,hardware",
                "approved": True,
            },
            {
                "title": f"[{org.name}] Student LMS Password Reset and SSO Token Expiry",
                "problem": "Student cannot access Moodle LMS portal after password change. Browser displays OAuth2 token invalidation error.",
                "solution": "1. Clear browser cookies and local storage for lms subdomain.\n2. Revoke active OAuth2 tokens in identity provider dashboard.\n3. Re-login using institutional email credentials.",
                "symptoms": "Infinite login loop on LMS login page, 'OAuth State Mismatch'.",
                "possible_causes": "Cached session cookies conflicting with updated SAML assertion.",
                "troubleshooting_steps": "1. Check user account in LDAP directory.\n2. Clear session: php admin/cli/kill_session.php --user={id}.",
                "verified_resolution": "Cleared stale Moodle session table and synced user LDAP password hash.",
                "tags": "lms,moodle,sso,password-reset,accounts",
                "approved": True,
            },
            {
                "title": f"[{org.name}] Hostel Block C Floor 3 Wi-Fi Access Point Recovery",
                "problem": "Hostel Block C 3rd Floor Wi-Fi completely down or unreachable. Access points show amber status LED.",
                "solution": "1. Power cycle PoE switch port feeding Block C Floor 3 access points.\n2. Verify DHCP lease pool saturation on hostel VLAN 40.\n3. Expand DHCP subnet if pool is exhausted.",
                "symptoms": "No Wi-Fi signal in rooms 301-320, AP status lights amber, devices unable to acquire IP.",
                "possible_causes": "PoE switch port hung, DHCP lease pool exhaustion, severed patch cord in riser closet.",
                "troubleshooting_steps": "1. Check switch port PoE power delivery.\n2. Inspect DHCP pool: show ip dhcp pool hostel-c-fl3.",
                "verified_resolution": "Power-cycled PoE switch port 18 on hostel switch and cleared exhausted DHCP lease bindings.",
                "tags": "hostel,wifi,poe,dhcp,outage",
                "approved": True,
            },
            # 7. Unapproved draft KB (for Demo F testing)
            {
                "title": f"[{org.name}] DRAFT UNAPPROVED: Experimental Campus Starlink Satellite Fallback Setup",
                "problem": "Draft guidelines for testing experimental secondary satellite uplink during fiber cut events.",
                "solution": "Connect emergency gateway to Starlink terminal port 2 with manual static route 0.0.0.0/0.",
                "symptoms": "Primary ISP fiber cut.",
                "possible_causes": "Road construction severance.",
                "troubleshooting_steps": "Do not execute without telecom director sign-off.",
                "verified_resolution": "Unverified draft procedure pending network committee review.",
                "tags": "draft,unapproved,starlink,satellite",
                "approved": False,
            },
        ]
    else:
        kb_data = [
            {
                "title": f"[{org.name}] GlobalProtect VPN Okta SAML Authentication Loop Troubleshooting",
                "problem": "Engineers and remote staff unable to connect to production VPN; browser enters continuous authentication loop with Okta identity provider.",
                "solution": "1. Clear GlobalProtect client cached cookies in settings.\n2. Update Palo Alto gateway IdP signing certificate in firewall settings.\n3. Ensure user has 'Eng-VPN-Access' group assigned in Okta directory.",
                "symptoms": "GlobalProtect client displays 'Connecting', redirects to Okta, repeats continuously.",
                "possible_causes": "Expired SAML signing certificate on firewall gateway, stale client cookie in embedded browser.",
                "troubleshooting_steps": "1. Inspect firewall auth logs: show log auth.\n2. Verify Okta app certificate expiry date.\n3. Purge ~/.GlobalProtect/cookies.xml on client.",
                "verified_resolution": "Cleared stale GlobalProtect keychain tokens, updated IdP SSO certificate in gateway portal, and flushed DNS cache.",
                "tags": "vpn,okta,saml,globalprotect,network",
                "approved": True,
            },
            {
                "title": f"[{org.name}] Production Redis Cluster Latency Spikes and Connection Timeouts",
                "problem": "High P99 latency on checkout and auth microservices due to Redis cluster connection pool exhaustion and slow queries.",
                "solution": "1. Check slowlog on Redis master nodes: SLOWLOG GET 20.\n2. Identify and optimize high-cardinality KEYS or HGETALL calls.\n3. Increase client connection pool max idle connections and enable read replicas.",
                "symptoms": "HTTP 500/504 errors on checkout API, Redis response time > 200ms.",
                "possible_causes": "Unindexed HGETALL queries on session keys, memory fragmentation, network throttling.",
                "troubleshooting_steps": "1. Run redis-cli -p 6379 info stats.\n2. Inspect instantaneous_ops_per_sec and rejected_connections.",
                "verified_resolution": "Replaced O(N) KEYS command with SCAN in session middleware and scaled Redis read replicas from 2 to 4.",
                "tags": "redis,cache,latency,microservices,sre",
                "approved": True,
            },
            {
                "title": f"[{org.name}] Kubernetes Pod OOMKilled and Memory Leak Diagnostics",
                "problem": "Microservice containers crashing with exit code 137 (OOMKilled) under sudden load spikes.",
                "solution": "1. Analyze heap dump using memory profiler to locate memory retention leak.\n2. Adjust container memory request and limit ratio in Helm deployment chart.\n3. Configure Horizontal Pod Autoscaler (HPA) to scale on memory threshold.",
                "symptoms": "Container restarts repeatedly, kubectl describe pod shows Last State: Terminated OOMKilled.",
                "possible_causes": "Unbounded cache growth in node.js/python worker, insufficient container memory limit.",
                "troubleshooting_steps": "1. kubectl top pod -n production.\n2. kubectl logs {pod_id} --previous.",
                "verified_resolution": "Patched unbounded in-memory cache in payment worker and increased pod memory limit to 2Gi.",
                "tags": "kubernetes,oomkilled,docker,helm,devops",
                "approved": True,
            },
            {
                "title": f"[{org.name}] Payment Webhook Retry Storm and Dead Letter Queue Backoff",
                "problem": "Third-party payment webhooks experiencing retry storms, overwhelming downstream event consumers and causing message queue delays.",
                "solution": "1. Enable exponential backoff with jitter on incoming webhook ingest queue.\n2. Move failing payloads to Dead Letter Queue (DLQ) after 5 failed attempts.\n3. Increase Kafka consumer group concurrency.",
                "symptoms": "Kafka consumer lag exceeding 100k messages, delayed payment confirmation notifications.",
                "possible_causes": "Downstream banking partner API rate limiting, unhandled payload validation exception.",
                "troubleshooting_steps": "1. Inspect Kafka consumer group lag: kafka-consumer-groups.sh --describe.\n2. Check DLQ error logs in Datadog.",
                "verified_resolution": "Deployed exponential backoff with jitter on webhook ingest queue and routed corrupted payloads to DLQ.",
                "tags": "payments,webhook,kafka,dlq,architecture",
                "approved": True,
            },
            {
                "title": f"[{org.name}] MacBook Jamf MDM Enrollment and FileVault Encryption Recovery",
                "problem": "Newly provisioned developer laptops fail Jamf Pro enrollment profile validation and FileVault escrow sync.",
                "solution": "1. Renew Jamf MDM push notification certificate profile.\n2. Re-trigger enrollment via terminal: sudo profiles renew -type enrollment.\n3. Escrow individual recovery key to Jamf secure vault.",
                "symptoms": "Device blocked from corporate Wi-Fi and GitHub access due to non-compliant device state.",
                "possible_causes": "Clock drift on client laptop, APNs certificate renewal pending.",
                "troubleshooting_steps": "1. Check MDM status: sudo jamf checkJSSConnection.\n2. Verify FileVault: fdesetup status.",
                "verified_resolution": "Ran sudo profiles renew -type enrollment and successfully escrowed FileVault recovery key.",
                "tags": "jamf,macos,mdm,filevault,workplace-it",
                "approved": True,
            },
            {
                "title": f"[{org.name}] AWS VPC Peering and Cross-Account Transit Gateway Routing",
                "problem": "Services in Staging VPC unable to reach shared database cluster in Infra VPC after route table update.",
                "solution": "1. Verify Transit Gateway route table associations and propagations.\n2. Ensure security groups allow ingress on port 5432 from staging CIDR block 10.20.0.0/16.\n3. Validate AWS Network Access Analyzer findings.",
                "symptoms": "Connection timed out error when connecting to PostgreSQL or Elasticsearch cluster.",
                "possible_causes": "Missing blackhole route cleanup, security group ingress rule missing CIDR block.",
                "troubleshooting_steps": "1. Test connectivity: nc -zv db.internal 5432.\n2. Check VPC Flow Logs for REJECT records.",
                "verified_resolution": "Added missing route 10.20.0.0/16 to Transit Gateway route table and allowed security group ingress.",
                "tags": "aws,vpc,transit-gateway,networking,cloud",
                "approved": True,
            },
            # 7. Unapproved draft KB (for Demo F testing)
            {
                "title": f"[{org.name}] DRAFT UNAPPROVED: Experimental Zero-Trust Mesh Network Protocol",
                "problem": "Draft internal testing procedure for WireGuard based mesh routing between dark stores.",
                "solution": "Manually flash OpenWrt gateway routers with experimental firmware v0.9-alpha.",
                "symptoms": "Testing only.",
                "possible_causes": "Experimental protocol testing.",
                "troubleshooting_steps": "Pending security architect approval.",
                "verified_resolution": "Unverified draft procedure pending security council sign-off.",
                "tags": "draft,unapproved,wireguard,zero-trust",
                "approved": False,
            },
        ]

    for item in kb_data:
        existing = db.query(KnowledgeBase).filter(
            KnowledgeBase.organization_id == org.id,
            KnowledgeBase.title == item["title"],
        ).first()

        if not existing:
            kb = KnowledgeBase(
                organization_id=org.id,
                title=item["title"],
                problem_description=item["problem"],
                solution=item["solution"],
                symptoms=item["symptoms"],
                possible_causes=item["possible_causes"],
                troubleshooting_steps=item["troubleshooting_steps"],
                verified_resolution=item["verified_resolution"],
                source_type="MANUAL_KB",
                tags=item["tags"],
                version="1.0",
                is_demo=True,
                is_verified=item["approved"],
                approval_status=KBApprovalStatus.APPROVED if item["approved"] else KBApprovalStatus.DRAFT,
                created_by_user_id=author_id,
            )
            db.add(kb)
            db.flush()


def seed_tickets_for_org(db: Session, org: Organization, is_college: bool, users: list, staff: list, depts: dict, teams: dict):
    """Generates 26-28 realistic tickets per organisation with varied statuses, priorities, and historical incident records."""
    now = datetime.now(timezone.utc)
    team_list = list(teams.values())
    dept_list = list(depts.values())

    # Helper to pick user & engineer
    def get_user(i):
        return users[i % len(users)]

    def get_eng(i):
        return staff[i % len(staff)]

    # Fetch categories
    cats = db.query(IssueCategory).filter(IssueCategory.organization_id == org.id).all()
    cat_map = {c.name: c for c in cats}

    # Ticket definitions tailored per org type
    if is_college:
        # College tickets
        ticket_specs = [
            # 1. Outage / Critical
            {
                "subject": "Campus Core Router Reboot Failure - Entire Campus Network Down",
                "description": "The main core router in Admin block failed to complete boot sequence after scheduled firmware upgrade. All academic blocks, departments, labs and Wi-Fi are completely disconnected.",
                "cat": "Network issues",
                "priority": TicketPriority.CRITICAL,
                "status": TicketStatus.IN_PROGRESS,
                "impact": "CAMPUS_WIDE",
                "urgency": "IMMEDIATE",
                "score": 98.0,
                "age_days": 1,
            },
            # 2. Exam Hall Ticket Timeout (Historical match for Demo B at MIT)
            {
                "subject": "Unable to download semester examination hall ticket timeout error 504",
                "description": "Multiple students in final semester B.Tech reporting 504 Gateway Timeout when attempting to download their examination hall ticket from student portal.",
                "cat": "Examination issues",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.RESOLVED,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 88.0,
                "age_days": 45,
                "resolution": "Flushed Redis cache on auth cluster, increased FastCGI timeout to 120s, and re-indexed admit card pdf blob store.",
            },
            # 3. New incoming Exam Hall ticket (will match #2 for Demo B)
            {
                "subject": "Exam hall ticket download throwing timeout 504 on portal",
                "description": "I am trying to download my semester exam hall ticket for tomorrow's examination, but the portal keeps timing out with HTTP 504.",
                "cat": "Examination issues",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.AWAITING_HELP_DESK_REVIEW,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 88.0,
                "age_days": 0,
            },
            # 4. SJC Duplicate Outage #1 (For Demo A)
            {
                "subject": "Hostel Block C 3rd Floor Wi-Fi completely down and unreachable",
                "description": "Hostel Block C 3rd floor Wi-Fi has stopped working since 8 PM. All access points in corridor show red/amber LED. No devices can connect in rooms 301 to 320.",
                "cat": "Network issues",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.IN_PROGRESS,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 82.0,
                "age_days": 0,
            },
            # 5. SJC Duplicate Outage #2 (Duplicate of #4)
            {
                "subject": "Hostel Block C 3rd floor no internet signal on WiFi",
                "description": "There is no internet signal or Wi-Fi connection in Hostel Block C third floor. Unable to study for upcoming tests. Please fix quickly.",
                "cat": "Network issues",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.AWAITING_HELP_DESK_REVIEW,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 80.0,
                "age_days": 0,
            },
            # 6. SJC Duplicate Outage #3 (Duplicate of #4)
            {
                "subject": "Block C floor 3 Wi-Fi disconnected cannot connect",
                "description": "Hostel Wi-Fi is down on the 3rd floor of Block C. Access points appear unpowered or unresponsive.",
                "cat": "Network issues",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.AWAITING_HELP_DESK_REVIEW,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 80.0,
                "age_days": 0,
            },
            # 7. Fee payment failure
            {
                "subject": "Tuition fee payment debited from account but portal status shows unpaid",
                "description": "Paid Rs 45,000 tuition fee using HDFC NetBanking. Amount was debited and bank reference received, but portal fee receipt shows pending.",
                "cat": "Fee and payment issues",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.ASSIGNED,
                "impact": "MEDIUM",
                "urgency": "HIGH",
                "score": 85.0,
                "age_days": 2,
            },
            # 8. Admission counseling document upload
            {
                "subject": "Unable to upload 12th marksheet in admission counseling portal",
                "description": "Counseling portal document upload form gives error 'File size exceeds maximum allowed' even though the scanned PDF is only 1.2 MB.",
                "cat": "Admission issues",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.ASSIGNED,
                "impact": "MEDIUM",
                "urgency": "MEDIUM",
                "score": 68.0,
                "age_days": 3,
            },
            # 9. Lab Projector HDMI failure
            {
                "subject": "Electronics Lab 204 Overhead Projector HDMI input broken",
                "description": "The ceiling mounted Epson projector in Lab 204 does not display signal over HDMI cable. Bent pins observed in wall plate connector.",
                "cat": "Hardware issues",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.APPROVED_FOR_ROUTING,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 38.0,
                "age_days": 4,
            },
            # 10. Student ERP password reset
            {
                "subject": "Student ERP account locked after 3 failed password attempts",
                "description": "I forgot my ERP password and account is now locked. I need my internal marks statement for scholarship submission.",
                "cat": "Account and access issues",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.RESOLVED,
                "impact": "LOW",
                "urgency": "MEDIUM",
                "score": 52.0,
                "age_days": 20,
                "resolution": "Verified student identity via enrollment ID and issued temporary password reset token to registered mobile number.",
            },
            # 11. Matlab Network License Manager failure
            {
                "subject": "Matlab R2023b network license manager connection timed out in CAD lab",
                "description": "CAD/CAM lab computers cannot obtain Matlab license token. FlexNet error -15: Cannot connect to license server system.",
                "cat": "Software issues",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.RESOLVED,
                "impact": "MEDIUM",
                "urgency": "MEDIUM",
                "score": 62.0,
                "age_days": 35,
                "resolution": "Restarted FlexLM license service on host 10.10.2.15 and opened firewall port 27000.",
            },
            # 12. Library RFID turnstile gate failure
            {
                "subject": "Library entrance RFID turnstile gate not scanning student smart ID cards",
                "description": "The turnstile entrance barcode/RFID reader in Central Library is not responding to student smart cards, causing delays.",
                "cat": "Technical issues",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.RESOLVED,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 42.0,
                "age_days": 40,
                "resolution": "Restarted SIP2 protocol daemon on Koha server and reconnected switch patch cable.",
            },
            # 13. Girls Hostel Biometric attendance machine offline
            {
                "subject": "Girls Hostel Block A biometric turnstile reader display dead",
                "description": "Biometric fingerprint and face reader at Block A entrance is not powering on after yesterday's thunder storm.",
                "cat": "Hardware issues",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.IN_PROGRESS,
                "impact": "MEDIUM",
                "urgency": "MEDIUM",
                "score": 58.0,
                "age_days": 5,
            },
            # 14. Degree certificate dispatch tracking
            {
                "subject": "Provisional degree certificate dispatch tracking number not received",
                "description": "Applied for provisional degree certificate 2 weeks ago. Status is marked Dispatched but courier tracking link is missing.",
                "cat": "Other organisational issues",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.ASSIGNED,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 25.0,
                "age_days": 6,
            },
            # 15. Examination Revaluation Form payment error
            {
                "subject": "Revaluation application form payment gateway deducting money twice",
                "description": "Applied for revaluation in Data Structures course. Gateway timed out on first attempt and deducted fee twice on retry.",
                "cat": "Fee and payment issues",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.IN_PROGRESS,
                "impact": "MEDIUM",
                "urgency": "HIGH",
                "score": 84.0,
                "age_days": 1,
            },
            # 16. Academic Timetable clash
            {
                "subject": "Elective subject timetable clash between Machine Learning and Cloud Computing",
                "description": "Both 6th semester electives Machine Learning (CS601) and Cloud Computing (CS604) are scheduled at 10:00 AM on Tuesdays.",
                "cat": "Examination issues",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.RESOLVED,
                "impact": "MEDIUM",
                "urgency": "MEDIUM",
                "score": 55.0,
                "age_days": 50,
                "resolution": "Rescheduled Cloud Computing (CS604) tutorial session to Thursday 2:00 PM to eliminate elective overlap.",
            },
            # 17. Mechanical Lab 3D printer calibration
            {
                "subject": "Creality 3D printer in Innovation Lab bed leveling sensor failing",
                "description": "CR-Touch auto leveling sensor on Creality Ender 3 printer in Innovation Lab blinking red and refusing to home Z-axis.",
                "cat": "Hardware issues",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.ASSIGNED,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 32.0,
                "age_days": 8,
            },
            # 18. Campus Wi-Fi 802.1X certificate error on MacBooks
            {
                "subject": "MacBook laptops unable to authenticate on Campus-Secure Wi-Fi with new certificate",
                "description": "All faculty MacBooks running macOS Sonoma fail to authenticate on Campus-Secure 802.1x SSID after institutional certificate renewal.",
                "cat": "Network issues",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.RESOLVED,
                "impact": "MEDIUM",
                "urgency": "MEDIUM",
                "score": 65.0,
                "age_days": 25,
                "resolution": "Installed the updated DigiCert Global Root G2 certificate on user devices and re-enrolled campus profile.",
            },
            # 19. Placement portal resume upload bug
            {
                "subject": "Campus placement portal fails to parse PDF resumes with multi-column layout",
                "description": "Students applying for campus drive unable to submit profile; ATS parser in placement cell portal throws JSON decode error.",
                "cat": "Software issues",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.IN_PROGRESS,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 78.0,
                "age_days": 1,
            },
            # 20. Auditorium Audio system mic feedback
            {
                "subject": "Main Seminar Hall wireless lapel microphone dead during conference",
                "description": "Wireless Sennheiser microphone transmitter in main seminar hall has damaged battery contacts and heavy static feedback.",
                "cat": "Hardware issues",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.ASSIGNED,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 30.0,
                "age_days": 10,
            },
            # 21. Student Bus Pass renewal verification
            {
                "subject": "Bus pass smart card renewal payment not reflecting at transport counter",
                "description": "Student paid online bus pass renewal fee of Rs 3,500. Transport counter terminal shows card as expired.",
                "cat": "Fee and payment issues",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.RESOLVED,
                "impact": "LOW",
                "urgency": "MEDIUM",
                "score": 50.0,
                "age_days": 30,
                "resolution": "Synced transport management database with finance ledger; card re-validated successfully.",
            },
            # 22. Server Room AC temperature high
            {
                "subject": "Server Room Rack 2 temperature alert exceeding 32 degrees Celsius",
                "description": "SNMP temperature sensor in Server Room Admin block reporting thermal threshold breach. Secondary HVAC unit has tripped.",
                "cat": "Technical issues",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.RESOLVED,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 86.0,
                "age_days": 15,
                "resolution": "Reset circuit breaker on secondary HVAC precision cooling unit and replaced clogged intake filter.",
            },
            # 23. Moodle LMS quiz submission timeout
            {
                "subject": "Moodle LMS database connection pool exhausted during midterm online quiz",
                "description": "250 students taking online database midterm quiz simultaneously received 502 Bad Gateway error on submit button.",
                "cat": "Software issues",
                "priority": TicketPriority.CRITICAL,
                "status": TicketStatus.RESOLVED,
                "impact": "CAMPUS_WIDE",
                "urgency": "IMMEDIATE",
                "score": 94.0,
                "age_days": 40,
                "resolution": "Increased PHP-FPM max_children from 50 to 200 and tuned PostgreSQL max_connections to 400 with PgBouncer.",
            },
            # 24. Hostel Hot Water geyser power trip
            {
                "subject": "Block B 2nd floor solar hybrid geyser tripping earth leakage circuit breaker",
                "description": "The hot water supply geyser in Block B second floor bathroom is tripping the corridor MCB repeatedly.",
                "cat": "Other organisational issues",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.ASSIGNED,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 28.0,
                "age_days": 7,
            },
            # 25. Obscure / No Evidence Ticket (Demo E)
            {
                "subject": "Requesting exotic bespoke quantum compiler license for esoteric experimental emulator",
                "description": "I need authorization for an obscure experimental esoteric quantum algorithmic syntax emulator written in specialized assembly.",
                "cat": "Software issues",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.AWAITING_HELP_DESK_REVIEW,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 22.0,
                "age_days": 0,
            },
            # 26. Additional Routine Ticket
            {
                "subject": "Campus ID card lost in cafeteria request for duplicate smart card",
                "description": "I misplaced my RFID smart identity card in the campus food court yesterday. Requesting issuance of duplicate card.",
                "cat": "Other organisational issues",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.AWAITING_HELP_DESK_REVIEW,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 20.0,
                "age_days": 0,
            },
        ]
    else:
        # Startup tickets
        ticket_specs = [
            # 1. P0 Outage
            {
                "subject": "Production Payment Gateway Webhook Latency Spikes Exceeding 15s",
                "description": "Downstream payment webhook delivery is experiencing massive backlog. Over 25,000 transaction events queued in Kafka with consumer lag exceeding threshold.",
                "cat": "Critical Service Outages",
                "priority": TicketPriority.CRITICAL,
                "status": TicketStatus.IN_PROGRESS,
                "impact": "CAMPUS_WIDE",
                "urgency": "IMMEDIATE",
                "score": 99.0,
                "age_days": 0,
            },
            # 2. Historical VPN SAML loop (Demo C at Freshworks)
            {
                "subject": "VPN client stuck in Okta authentication loop on macOS",
                "description": "Engineers on macOS Sonoma cannot connect to production VPN; browser redirects to Okta SSO repeatedly without establishing tunnel.",
                "cat": "Network & VPN",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.RESOLVED,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 82.0,
                "age_days": 30,
                "resolution": "Cleared stale GlobalProtect keychain tokens, updated IdP SSO certificate in gateway portal, and flushed DNS cache.",
            },
            # 3. New incoming VPN ticket (matches #2 for Demo C)
            {
                "subject": "GlobalProtect VPN repeating Okta SAML login loop repeatedly",
                "description": "I am trying to log into the corporate VPN using GlobalProtect, but it opens Chrome, verifies Okta MFA, and then loops back to the login prompt.",
                "cat": "Network & VPN",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.AWAITING_HELP_DESK_REVIEW,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 80.0,
                "age_days": 0,
            },
            # 4. Redis cluster timeout
            {
                "subject": "Production Redis Cluster Latency Spikes on Cart Microservice",
                "description": "High P99 latency reported on cart microservice. Redis master node CPU reaching 100% due to unindexed KEYS command query.",
                "cat": "Cloud Infrastructure",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.RESOLVED,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 86.0,
                "age_days": 20,
                "resolution": "Replaced O(N) KEYS command with SCAN in session middleware and scaled Redis read replicas from 2 to 4.",
            },
            # 5. Kubernetes Pod OOMKilled
            {
                "subject": "Checkout service pods crash looping with exit code 137 OOMKilled",
                "description": "Kubernetes pods in production namespace running checkout-v2 service crashing every 15 minutes due to memory leak under traffic spike.",
                "cat": "Cloud Infrastructure",
                "priority": TicketPriority.CRITICAL,
                "status": TicketStatus.RESOLVED,
                "impact": "HIGH",
                "urgency": "IMMEDIATE",
                "score": 92.0,
                "age_days": 35,
                "resolution": "Patched unbounded in-memory cache in payment worker and increased pod memory limit to 2Gi.",
            },
            # 6. Okta SSO access for new engineer
            {
                "subject": "New joinee SRE missing GitHub enterprise and AWS production read-only role",
                "description": "Joined DevOps team on Monday but Okta group mapping did not assign AWS production telemetry account and GitHub org permissions.",
                "cat": "SSO & Access Control",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.ASSIGNED,
                "impact": "LOW",
                "urgency": "MEDIUM",
                "score": 58.0,
                "age_days": 2,
            },
            # 7. CI/CD GitHub Runner capacity exhaustion
            {
                "subject": "GitHub Actions self-hosted runner pool queue delay exceeding 45 minutes",
                "description": "Pull request validation pipelines are stuck in queued state on Kubernetes runner scale set. Autoscaler reached max replica limit.",
                "cat": "Developer Tooling",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.ASSIGNED,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 78.0,
                "age_days": 1,
            },
            # 8. MacBook Jamf MDM profile renewal failure
            {
                "subject": "MacBook Pro FileVault encryption key not syncing with Jamf Pro MDM",
                "description": "Compliance scanner flagged developer laptop as non-compliant due to missing FileVault recovery key escrow.",
                "cat": "Hardware & Workstation",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.RESOLVED,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 35.0,
                "age_days": 18,
                "resolution": "Ran sudo profiles renew -type enrollment and successfully escrowed FileVault recovery key.",
            },
            # 9. Payment Webhook DLQ retry storm
            {
                "subject": "Payment refund webhook notifications failing with 429 Too Many Requests",
                "description": "Third-party banking API is rate limiting our outbound refund webhook consumers. Need backoff implementation.",
                "cat": "Payment Gateway Issues",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.RESOLVED,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 85.0,
                "age_days": 25,
                "resolution": "Deployed exponential backoff with jitter on webhook ingest queue and routed corrupted payloads to DLQ.",
            },
            # 10. AWS Transit Gateway routing failure
            {
                "subject": "Staging VPC unable to connect to shared Kafka cluster in Infra account",
                "description": "Services in staging VPC cannot reach kafka.infra.internal on port 9092. Route table shows blackhole route.",
                "cat": "Cloud Infrastructure",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.RESOLVED,
                "impact": "MEDIUM",
                "urgency": "MEDIUM",
                "score": 64.0,
                "age_days": 42,
                "resolution": "Added missing route 10.20.0.0/16 to Transit Gateway route table and allowed security group ingress.",
            },
            # 11. Dark store handheld terminal Wi-Fi disconnect (Zepto/Logistics)
            {
                "subject": "Warehouse Zebra TC52 barcode scanner terminals dropping Wi-Fi signal in cold room",
                "description": "Picker handhelds in deep freeze section of dark store losing connection to fulfillment engine every 2 minutes.",
                "cat": "Hardware & Workstation",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.IN_PROGRESS,
                "impact": "MEDIUM",
                "urgency": "HIGH",
                "score": 68.0,
                "age_days": 3,
            },
            # 12. Seller Portal product image upload timeout (Meesho)
            {
                "subject": "Seller hub product catalog photo upload failing with S3 multi-part timeout",
                "description": "Suppliers attempting to upload high-res product photos receiving 408 Request Timeout on direct S3 presigned URL.",
                "cat": "Critical Service Outages",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.IN_PROGRESS,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 84.0,
                "age_days": 1,
            },
            # 13. Office Floor 4 Wi-Fi AP rebooting
            {
                "subject": "Floor 4 Engineering bay Cisco Meraki AP rebooting under high client density",
                "description": "Cisco Meraki MR46 AP in main engineering wing power cycling when connected clients exceed 120 devices.",
                "cat": "Network & VPN",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.APPROVED_FOR_ROUTING,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 40.0,
                "age_days": 4,
            },
            # 14. Ergonomic monitor arm request
            {
                "subject": "Dual monitor arm mount request for remote workstation setup",
                "description": "Requesting standard corporate IT dual-arm gas-spring VESA monitor mount for home office setup.",
                "cat": "General Inquiries",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.AWAITING_HELP_DESK_REVIEW,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 20.0,
                "age_days": 5,
            },
            # 15. PostgreSQL Database deadlocks on inventory update
            {
                "subject": "Inventory reservation transactions causing deadlocks on SKU master table",
                "description": "Flash sale flash checkout transactions encountering deadlock errors in postgres transaction log: Deadlock found when trying to get lock.",
                "cat": "Cloud Infrastructure",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.RESOLVED,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 88.0,
                "age_days": 28,
                "resolution": "Enforced deterministic SKU locking order in reservation service and converted row locks to advisory locks.",
            },
            # 16. Datadog APM tracing agent high CPU usage
            {
                "subject": "Datadog daemonset agent consuming over 1.5 cores on worker nodes",
                "description": "Datadog agent v7.45 running on EKS nodes consuming excessive CPU cycles due to unbound socket profiling.",
                "cat": "Developer Tooling",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.ASSIGNED,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 38.0,
                "age_days": 7,
            },
            # 17. Single Sign-On session logout bug
            {
                "subject": "Single Sign-On session expiring every 15 minutes instead of 8 hours",
                "description": "Corporate Google Workspace OAuth token lifetime misconfigured on staging environment; developers prompted to re-login continuously.",
                "cat": "SSO & Access Control",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.RESOLVED,
                "impact": "LOW",
                "urgency": "MEDIUM",
                "score": 54.0,
                "age_days": 19,
                "resolution": "Updated IdP session timeout parameter in OAuth client settings to 28800 seconds.",
            },
            # 18. Customer checkout UPI Intent flow error
            {
                "subject": "UPI Intent callback not returning customer to merchant app on Android 14",
                "description": "Android 14 users paying via PhonePe or Google Pay are not returned to confirmation screen after successful UPI pin entry.",
                "cat": "Payment Gateway Issues",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.IN_PROGRESS,
                "impact": "HIGH",
                "urgency": "HIGH",
                "score": 82.0,
                "age_days": 2,
            },
            # 19. Docker registry 503 Service Unavailable
            {
                "subject": "Internal Harbor Docker container registry returning 503 during deployment",
                "description": "CI builds cannot push release images to harbor.internal. Error: 503 Service Unavailable backend storage connection timed out.",
                "cat": "Developer Tooling",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.RESOLVED,
                "impact": "MEDIUM",
                "urgency": "MEDIUM",
                "score": 62.0,
                "age_days": 12,
                "resolution": "Restarted Harbor registry core pod and pruned dangling images to recover 180GB storage volume.",
            },
            # 20. Laptop battery swelling replacement
            {
                "subject": "MacBook Air M2 trackpad unresponsive due to swollen battery",
                "description": "Trackpad is physically lifting and difficult to click on developer laptop. Requesting immediate hardware inspection and battery swap.",
                "cat": "Hardware & Workstation",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.ASSIGNED,
                "impact": "LOW",
                "urgency": "HIGH",
                "score": 75.0,
                "age_days": 3,
            },
            # 21. ElasticSearch cluster unassigned shards
            {
                "subject": "ElasticSearch cluster red status due to 12 unassigned shards",
                "description": "Log search cluster went red after node termination. Shard allocation failed with out of disk space on hot data tier.",
                "cat": "Cloud Infrastructure",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.RESOLVED,
                "impact": "MEDIUM",
                "urgency": "HIGH",
                "score": 80.0,
                "age_days": 32,
                "resolution": "Expanded EBS volume by 500GB on data node and triggered shard reroute retry with allocate_stale_primary.",
            },
            # 22. Cloudflare DDoS false positives on merchant API
            {
                "subject": "Cloudflare WAF rate limiting blocking valid merchant bulk inventory sync",
                "description": "High-volume merchant partners receiving 403 Forbidden on /api/v2/inventory/bulk endpoint due to WAF rule 100045.",
                "cat": "Critical Service Outages",
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.IN_PROGRESS,
                "impact": "MEDIUM",
                "urgency": "HIGH",
                "score": 83.0,
                "age_days": 1,
            },
            # 23. VPN gateway redundancy failover test
            {
                "subject": "Secondary VPN gateway failed health check during automated failover drill",
                "description": "BGP route withdraw did not switch traffic to standby VPN tunnel during scheduled resilience drill.",
                "cat": "Network & VPN",
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.RESOLVED,
                "impact": "MEDIUM",
                "urgency": "MEDIUM",
                "score": 60.0,
                "age_days": 45,
                "resolution": "Corrected BGP autonomous system number and re-advertised MED metric on secondary tunnel.",
            },
            # 24. Obscure / No Evidence Ticket (Demo E)
            {
                "subject": "Requesting exotic bespoke quantum compiler license for esoteric experimental emulator",
                "description": "I need authorization for an obscure experimental esoteric quantum algorithmic syntax emulator written in specialized assembly.",
                "cat": "Developer Tooling",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.AWAITING_HELP_DESK_REVIEW,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 22.0,
                "age_days": 0,
            },
            # 25. Routine IT asset inquiry
            {
                "subject": "Annual corporate IT equipment return policy for remote employees",
                "description": "Inquiring about policy and prepaid shipping label procedure for returning legacy peripheral docking station.",
                "cat": "General Inquiries",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.AWAITING_HELP_DESK_REVIEW,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 20.0,
                "age_days": 0,
            },
            # 26. Software license seat request
            {
                "subject": "Figma Enterprise design license seat allocation for new UI designer",
                "description": "New product designer joined checkout squad and requires editor seat in corporate Figma workspace.",
                "cat": "SSO & Access Control",
                "priority": TicketPriority.LOW,
                "status": TicketStatus.AWAITING_HELP_DESK_REVIEW,
                "impact": "LOW",
                "urgency": "LOW",
                "score": 24.0,
                "age_days": 0,
            },
        ]

    created_tickets = []
    first_outage_ticket = None

    for i, spec in enumerate(ticket_specs, start=1):
        t_num = f"TKT-{org.code}-{i:04d}"
        existing = db.query(Ticket).filter(
            Ticket.organization_id == org.id,
            Ticket.ticket_number == t_num,
        ).first()

        created_time = now - timedelta(days=spec["age_days"], hours=i % 12, minutes=i * 3)
        resolved_time = (created_time + timedelta(hours=4, minutes=30)) if spec["status"] in (TicketStatus.RESOLVED, TicketStatus.CLOSED) else None

        sub_user = get_user(i)
        cat_obj = cat_map.get(spec["cat"])
        assigned_engineer = get_eng(i) if spec["status"] in (TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED) else None

        # Build evidence JSON
        evidence_payload = {
            "classification": {
                "predicted_category": spec["cat"],
                "confidence": 0.89,
                "subcategory": "General",
                "needs_human_review": False,
            },
            "priority": {
                "impact": spec["impact"],
                "urgency": spec["urgency"],
                "priority_score": spec["score"],
                "sla_rule": "SLA Engine Default Rule",
            },
            "routing": {
                "recommended_department_name": cat_obj.department.name if cat_obj and cat_obj.department else None,
                "recommended_support_team_name": cat_obj.support_team.name if cat_obj and cat_obj.support_team else None,
            },
        }

        if not existing:
            t = Ticket(
                organization_id=org.id,
                ticket_number=t_num,
                user_id=sub_user.id,
                category_id=cat_obj.id if cat_obj else None,
                subcategory=spec["cat"],
                impact=spec["impact"],
                urgency=spec["urgency"],
                subject=spec["subject"],
                description=spec["description"],
                source=TicketSource.WEB,
                ai_predicted_category=spec["cat"],
                ai_predicted_priority=spec["priority"],
                ai_priority_score=spec["score"],
                ai_priority_explanation=f"Evaluated via priority scoring engine. Priority: {spec['priority'].value} (score: {spec['score']}). Impact: {spec['impact']}, Urgency: {spec['urgency']}.",
                ai_recommended_department_id=cat_obj.department_id if cat_obj else None,
                ai_recommended_support_team_id=cat_obj.support_team_id if cat_obj else None,
                ai_confidence_score=0.92,
                ai_analysis_status="COMPLETED",
                ai_evidence_json=json.dumps(evidence_payload),
                confirmed_priority=spec["priority"],
                department_id=cat_obj.department_id if cat_obj else (dept_list[0].id if dept_list else None),
                support_team_id=cat_obj.support_team_id if cat_obj else (team_list[0].id if team_list else None),
                assigned_engineer_id=assigned_engineer.id if assigned_engineer else None,
                status=spec["status"],
                verified_resolution=spec.get("resolution"),
                is_resolution_verified=True if spec.get("resolution") else False,
                is_demo=True,
                created_at=created_time,
                updated_at=resolved_time or created_time,
                resolved_at=resolved_time,
            )

            # Link duplicates for Demo A (SJC hostel Wi-Fi cluster)
            if i == 4 and org.code == "SJC-01":
                first_outage_ticket = t

            if i in (5, 6) and org.code == "SJC-01" and first_outage_ticket:
                t.ai_duplicate_ticket_id = first_outage_ticket.id
                t.ai_duplicate_score = 0.86 if i == 5 else 0.81
                t.related_incident_id = first_outage_ticket.id

            db.add(t)
            db.flush()

            # Add comments
            if spec.get("resolution"):
                res_comment = TicketComment(
                    organization_id=org.id,
                    ticket_id=t.id,
                    user_id=assigned_engineer.id if assigned_engineer else sub_user.id,
                    comment=f"Resolution: {spec['resolution']}",
                    is_internal=False,
                    created_at=resolved_time or created_time,
                )
                db.add(res_comment)

            # Audit history
            hist = TicketHistory(
                organization_id=org.id,
                ticket_id=t.id,
                previous_status=TicketStatus.SUBMITTED,
                new_status=spec["status"],
                changed_by_user_id=sub_user.id,
                description=f"Initial state set to {spec['status'].value}",
                created_at=created_time,
            )
            db.add(hist)
            created_tickets.append(t)
        else:
            created_tickets.append(existing)

    return created_tickets


def index_all_into_qdrant(db: Session, org: Organization):
    """Indexes all approved KB documents and verified tickets of this organisation into Qdrant."""
    print(f"[*] Ingesting vector embeddings into Qdrant for {org.name} ({org.code})...")

    # 1. Index Knowledge Base
    kb_entries = db.query(KnowledgeBase).filter(
        KnowledgeBase.organization_id == org.id,
        KnowledgeBase.approval_status == KBApprovalStatus.APPROVED,
    ).all()

    for entry in kb_entries:
        try:
            vector_store.upsert_knowledge_base(
                doc_id=entry.id,
                organization_id=entry.organization_id,
                title=entry.title,
                problem_description=entry.problem_description,
                solution=entry.solution,
                category=entry.category.name if entry.category else "General Support",
                symptoms=entry.symptoms,
                troubleshooting_steps=entry.troubleshooting_steps,
                verified_resolution=entry.verified_resolution,
                source_type=entry.source_type or "MANUAL_KB",
                source_ticket_id=entry.source_ticket_id,
                tags=entry.tags,
                version=entry.version or "1.0",
                is_verified=entry.is_verified,
            )
        except Exception as ex:
            print(f"    [!] Error indexing KB {entry.id}: {ex}")

    # 2. Index Tickets (especially resolved tickets with verified resolutions)
    tickets = db.query(Ticket).filter(
        Ticket.organization_id == org.id,
    ).all()

    for t in tickets:
        try:
            vector_store.upsert_ticket(
                ticket_id=t.id,
                organization_id=t.organization_id,
                ticket_number=t.ticket_number,
                subject=t.subject,
                description=t.description,
                category=t.category.name if t.category else (t.ai_predicted_category or "General"),
                status=t.status.value,
                confirmed_priority=t.confirmed_priority.value if t.confirmed_priority else None,
                verified_resolution=t.verified_resolution,
                is_resolution_verified=t.is_resolution_verified,
                created_at_iso=t.created_at.isoformat() if t.created_at else None,
            )
        except Exception as ex:
            print(f"    [!] Error indexing Ticket {t.id}: {ex}")

    print(f"    [+] Indexed {len(kb_entries)} KB articles and {len(tickets)} tickets for {org.name}.")


def seed_phase5():
    """Main entrypoint for Phase 5 multi-tenant dataset seeding."""
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("  QueueMind AI — Phase 5 Eight-Organisation Dataset Seeding")
        print("=" * 80)

        total_orgs = 0
        total_users = 0
        total_tickets = 0
        total_kbs = 0

        for org_def in ORGANIZATIONS:
            print(f"\nProcessing Organisation: {org_def['name']} ({org_def['code']})...")

            # Check or create Organization
            org = db.query(Organization).filter(Organization.code == org_def["code"]).first()
            if not org:
                org = Organization(
                    name=org_def["name"],
                    code=org_def["code"],
                    slug=org_def["slug"],
                    org_type=org_def["org_type"],
                    description=org_def["description"],
                    contact_email=org_def["contact_email"],
                    is_active=True,
                    is_demo=True,
                )
                db.add(org)
                db.flush()
                print(f"  [+] Created Organization: {org.name} ({org.code})")
            else:
                org.is_demo = True
                print(f"  [=] Organization {org.name} already exists. Marked as demo.")

            total_orgs += 1

            # Seed Departments, Teams, and Categories
            depts, teams = seed_departments_and_teams(db, org, org_def["is_college"])
            print(f"  [+] Configured {len(depts)} departments and {len(teams)} support teams.")

            # Seed Staff and Users
            admin_u, hd_staff, lead_u, staff_members, end_users = seed_users_and_staff(
                db, org, depts, teams, org_def["domain"], org_def["is_college"]
            )
            org_user_count = 1 + len(hd_staff) + 1 + len(staff_members) + len(end_users)
            total_users += org_user_count
            print(f"  [+] Provisioned {org_user_count} individual accounts (Admin, HelpDesk, Lead, 10 Staff, 12 Users).")

            # Seed Knowledge Base
            seed_knowledge_base(db, org, org_def["is_college"], admin_u.id)
            kb_count = db.query(KnowledgeBase).filter(KnowledgeBase.organization_id == org.id).count()
            total_kbs += kb_count
            print(f"  [+] Seeded {kb_count} knowledge base articles (including symptoms, causes, troubleshooting, resolutions).")

            # Seed Tickets
            tickets = seed_tickets_for_org(
                db, org, org_def["is_college"], end_users, staff_members, depts, teams
            )
            total_tickets += len(tickets)
            print(f"  [+] Seeded {len(tickets)} realistic tickets with varied statuses, priorities, and historical incident records.")

            db.commit()

            # Index into Qdrant
            index_all_into_qdrant(db, org)

        print("\n" + "=" * 80)
        print("  Phase 5 Dataset Seeding Completed Successfully!")
        print(f"  - Total Organisations Seeded: {total_orgs}")
        print(f"  - Total Individual Users Created: {total_users}")
        print(f"  - Total Realistic Tickets Seeded: {total_tickets}")
        print(f"  - Total Knowledge Base Articles: {total_kbs}")
        print(f"  - Default Demo Credentials: Email prefix + '@<domain>' | Password: '{DEFAULT_PASSWORD}'")
        print("=" * 80)

    except Exception as ex:
        db.rollback()
        print(f"[!] Seeding failed: {ex}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_phase5()
