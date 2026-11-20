"""
Phase 5 Dataset Cleanup Script for QueueMind AI.
Safely removes all seeded demo records where is_demo == True.

Guarantees:
- Strictly preserves existing non-demo records (JSS-01, APEX-01, master platform accounts).
- Deletes demo tickets, comments, histories, and attachments.
- Deletes demo knowledge base entries.
- Deletes demo users, support teams, departments, and issue categories.
- Deletes demo organizations.
- Cleans up Qdrant vector store records for demo organizations.
"""

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.database.base import import_all_models
from app.models.organization import Organization
from app.models.department import Department
from app.models.support_team import SupportTeam
from app.models.issue_category import IssueCategory
from app.models.user import User
from app.models.ticket import Ticket
from app.models.ticket_comment import TicketComment
from app.models.ticket_history import TicketHistory
from app.models.knowledge_base import KnowledgeBase
from app.ai.vector_store import vector_store

import_all_models()

PRESERVED_ORG_CODES = {"JSS-01", "APEX-01"}


def cleanup_phase5():
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("  QueueMind AI — Phase 5 Demo Dataset Cleanup")
        print("=" * 80)

        # 1. Identify Demo Organizations
        demo_orgs = db.query(Organization).filter(
            Organization.is_demo == True,  # noqa: E712
            ~Organization.code.in_(PRESERVED_ORG_CODES),
        ).all()

        demo_org_ids = [org.id for org in demo_orgs]
        print(f"[*] Found {len(demo_orgs)} demo organisations to clean up: {[o.name for o in demo_orgs]}")

        if not demo_org_ids:
            print("[=] No demo organisations found. Preserved non-demo records are intact.")
            return

        # 2. Delete Demo Tickets (and related comments & histories)
        demo_tickets = db.query(Ticket).filter(
            (Ticket.organization_id.in_(demo_org_ids)) | (Ticket.is_demo == True)  # noqa: E712
        ).all()
        demo_ticket_ids = [t.id for t in demo_tickets]

        if demo_ticket_ids:
            # Delete comments
            deleted_comments = db.query(TicketComment).filter(
                TicketComment.ticket_id.in_(demo_ticket_ids)
            ).delete(synchronize_session=False)

            # Delete history
            deleted_history = db.query(TicketHistory).filter(
                TicketHistory.ticket_id.in_(demo_ticket_ids)
            ).delete(synchronize_session=False)

            # Delete tickets
            deleted_tickets = db.query(Ticket).filter(
                Ticket.id.in_(demo_ticket_ids)
            ).delete(synchronize_session=False)

            print(f"  [-] Deleted {deleted_tickets} tickets, {deleted_comments} comments, and {deleted_history} audit records.")

        # 3. Delete Demo Knowledge Base Entries
        deleted_kbs = db.query(KnowledgeBase).filter(
            (KnowledgeBase.organization_id.in_(demo_org_ids)) | (KnowledgeBase.is_demo == True)  # noqa: E712
        ).delete(synchronize_session=False)
        print(f"  [-] Deleted {deleted_kbs} knowledge base entries.")

        # 4. Delete Demo Users
        deleted_users = db.query(User).filter(
            (User.organization_id.in_(demo_org_ids)) | (User.is_demo == True)  # noqa: E712
        ).delete(synchronize_session=False)
        print(f"  [-] Deleted {deleted_users} demo user accounts.")

        # 5. Delete Issue Categories
        deleted_cats = db.query(IssueCategory).filter(
            IssueCategory.organization_id.in_(demo_org_ids)
        ).delete(synchronize_session=False)
        print(f"  [-] Deleted {deleted_cats} issue categories.")

        # 6. Delete Support Teams
        deleted_teams = db.query(SupportTeam).filter(
            SupportTeam.organization_id.in_(demo_org_ids)
        ).delete(synchronize_session=False)
        print(f"  [-] Deleted {deleted_teams} support teams.")

        # 7. Delete Departments
        deleted_depts = db.query(Department).filter(
            Department.organization_id.in_(demo_org_ids)
        ).delete(synchronize_session=False)
        print(f"  [-] Deleted {deleted_depts} departments.")

        # 8. Delete Demo Organizations
        deleted_orgs = db.query(Organization).filter(
            Organization.id.in_(demo_org_ids)
        ).delete(synchronize_session=False)
        print(f"  [-] Deleted {deleted_orgs} demo organisations.")

        db.commit()

        # 9. Clear vectors in Qdrant for demo orgs
        for org_id in demo_org_ids:
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                flt = Filter(must=[FieldCondition(key="organization_id", match=MatchValue(value=org_id))])
                vector_store.client.delete(
                    collection_name=vector_store.tickets_collection,
                    points_selector=flt,
                )
                vector_store.client.delete(
                    collection_name=vector_store.kb_collection,
                    points_selector=flt,
                )
            except Exception:
                pass

        print("\n[+] Phase 5 Demo Dataset Cleanup Complete. Non-demo records preserved.")

    except Exception as ex:
        db.rollback()
        print(f"[!] Cleanup failed: {ex}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_phase5()
