"""
Semantic Duplicate Ticket Detection for QueueMind AI.

Phase 5 Part 4:
- Leverages Sentence Transformers / Dense Semantic Vectors with Qdrant vector database.
- Strictly organization-aware retrieval.
- Detects exact duplicates, near-duplicates with different wording, and recurring outage reports.
- Distinguishes likely duplicates (>= 0.75) from related/similar tickets (>= 0.50).
- Supports incident cluster counting and human-in-the-loop Help Desk confirmation.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
import numpy as np

from app.ai.embedding_engine import embedding_engine
from app.ai.vector_store import vector_store
from app.models.ticket import Ticket, TicketStatus


EXACT_DUPLICATE_THRESHOLD = 0.88
LIKELY_DUPLICATE_THRESHOLD = 0.70
SIMILAR_ISSUE_THRESHOLD = 0.50


class DuplicateDetector:
    """
    Computes semantic similarity against existing open/active tickets in the same organisation.
    """

    @classmethod
    def find_duplicate(
        cls,
        db: Session,
        organization_id: int,
        current_ticket_id: int,
        subject: str,
        description: str,
        threshold: float = SIMILAR_ISSUE_THRESHOLD,
    ) -> Optional[Dict[str, Any]]:
        """
        Searches for duplicate or related tickets strictly within the same organisation.
        """
        query_text = f"{subject} {description}".strip()

        # 1. Search via Qdrant Vector Store
        qdrant_results = vector_store.search_similar_tickets(
            organization_id=organization_id,
            query_text=query_text,
            exclude_ticket_id=current_ticket_id,
            only_resolved=False,
            limit=10,
            score_threshold=threshold,
        )

        candidates: List[Dict[str, Any]] = []

        if qdrant_results:
            candidates = qdrant_results
        else:
            # 2. Database Fallback
            candidate_tickets: List[Ticket] = (
                db.query(Ticket)
                .filter(
                    Ticket.organization_id == organization_id,
                    Ticket.id != current_ticket_id,
                    Ticket.status.in_([
                        TicketStatus.SUBMITTED,
                        TicketStatus.AWAITING_HELP_DESK_REVIEW,
                        TicketStatus.APPROVED_FOR_ROUTING,
                        TicketStatus.ASSIGNED,
                        TicketStatus.IN_PROGRESS,
                        TicketStatus.RESOLVED,
                    ]),
                )
                .order_by(Ticket.created_at.desc())
                .limit(100)
                .all()
            )

            if not candidate_tickets:
                return None

            q_vec = np.array(embedding_engine.encode(query_text))

            for t in candidate_tickets:
                t_text = f"{t.subject} {t.description}".strip()
                t_vec = np.array(embedding_engine.encode(t_text))
                sim = float(np.dot(q_vec, t_vec))
                if sim >= threshold:
                    candidates.append({
                        "ticket_id": t.id,
                        "ticket_number": t.ticket_number,
                        "subject": t.subject,
                        "category": t.category.name if t.category else (t.ai_predicted_category or ""),
                        "status": t.status.value,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                        "similarity_score": round(sim, 3),
                    })

            candidates.sort(key=lambda x: x["similarity_score"], reverse=True)

        if not candidates:
            return None

        best = candidates[0]
        best_score = best["similarity_score"]

        # Classification into exact, likely, or similar
        is_exact = best_score >= EXACT_DUPLICATE_THRESHOLD
        is_likely = best_score >= LIKELY_DUPLICATE_THRESHOLD
        classification_label = "EXACT_DUPLICATE" if is_exact else ("LIKELY_DUPLICATE" if is_likely else "SIMILAR_ISSUE")

        # Count total related reports for this issue in the organization
        count_related = len(candidates)
        if count_related > 1:
            summary = (
                f"{count_related} similar reports have been submitted for this issue in your organisation. "
                f"Matches {best['ticket_number']} ('{best['subject']}') with {round(best_score * 100, 1)}% similarity."
            )
        else:
            summary = (
                f"Potential duplicate of {best['ticket_number']} ('{best['subject']}') "
                f"with {round(best_score * 100, 1)}% similarity."
            )

        return {
            "is_duplicate": True,
            "duplicate_ticket_id": best["ticket_id"],
            "duplicate_ticket_number": best["ticket_number"],
            "duplicate_subject": best["subject"],
            "similarity_score": best_score,
            "status": best.get("status"),
            "classification": classification_label,
            "related_count": count_related,
            "cluster_size": count_related,
            "summary": summary,
            "related_tickets": [
                {
                    "ticket_id": c["ticket_id"],
                    "ticket_number": c["ticket_number"],
                    "subject": c["subject"],
                    "similarity_score": c["similarity_score"],
                    "status": c.get("status"),
                }
                for c in candidates[:5]
            ],
        }


duplicate_detector = DuplicateDetector()
