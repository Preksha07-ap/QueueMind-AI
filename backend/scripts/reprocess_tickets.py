"""
Safe Ticket Reprocessor for QueueMind AI.

Re-evaluates existing tickets with the AI Triage Engine:
- Recalculates category, subcategory, impact, urgency, priority SLA
- Suggests department and support team
- Detects semantic duplicates
- Preserves ticket IDs, submitters, comments, history, and status
"""

import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.session import SessionLocal
from app.models.ticket import Ticket
from app.ai.triage_orchestrator import run_ai_triage


def reprocess_tickets():
    db = SessionLocal()
    try:
        tickets = db.query(Ticket).all()
        print(f"Found {len(tickets)} tickets to reprocess.")
        reprocessed = 0

        for t in tickets:
            print(f"Reprocessing Ticket #{t.ticket_number} (ID: {t.id}) - '{t.subject[:40]}...'")
            run_ai_triage(db=db, ticket=t)
            reprocessed += 1

        db.commit()
        print(f"Successfully reprocessed {reprocessed} tickets through the AI triage engine.")
    except Exception as ex:
        db.rollback()
        print(f"Error during reprocessing: {ex}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    reprocess_tickets()
