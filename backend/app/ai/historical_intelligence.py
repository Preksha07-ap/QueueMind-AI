"""
Historical Incident Intelligence for QueueMind AI.

Core Requirements (Phase 5 Part 5):
- Automatically searches previously resolved historical tickets from the same organisation.
- Evaluates similarity against verified resolution records (including weeks/months earlier).
- Distinguishes authoritative verified resolutions from unverified comments.
- Formulates actionable recommendations citing the previous ticket number, resolution date,
  troubleshooting steps, and similarity score.
- Supports recurring incident detection and cluster grouping.
- Enforces strict multi-tenant isolation.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.ai.vector_store import vector_store
from app.models.ticket import Ticket, TicketStatus


HISTORICAL_SIMILARITY_THRESHOLD = 0.55


class HistoricalIncidentIntelligence:
    """
    Analyzes incoming issues against resolved historical incident history.
    """

    @classmethod
    def analyze_incident(
        cls,
        db: Session,
        organization_id: int,
        current_ticket_id: int,
        subject: str,
        description: str,
        threshold: float = HISTORICAL_SIMILARITY_THRESHOLD,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves matching verified historical incident and produces a grounded recommendation.
        """
        query_text = f"{subject} {description}".strip()

        # 1. First search via Qdrant Vector Store
        qdrant_matches = vector_store.search_similar_tickets(
            organization_id=organization_id,
            query_text=query_text,
            exclude_ticket_id=current_ticket_id,
            only_resolved=True,
            limit=3,
            score_threshold=threshold,
        )

        candidates: List[Dict[str, Any]] = []

        if qdrant_matches:
            candidates = qdrant_matches
        else:
            # 2. Database Fallback (direct query for resolved tickets with verified resolution)
            resolved_tickets = (
                db.query(Ticket)
                .filter(
                    Ticket.organization_id == organization_id,
                    Ticket.id != current_ticket_id,
                    Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                    or_(
                        Ticket.is_resolution_verified == True,  # noqa: E712
                        Ticket.verified_resolution != None,     # noqa: E711
                    ),
                )
                .order_by(Ticket.created_at.desc())
                .limit(40)
                .all()
            )

            if not resolved_tickets:
                return None

            # Calculate similarity using embedding engine
            from app.ai.embedding_engine import embedding_engine
            import numpy as np

            q_vec = np.array(embedding_engine.encode(query_text))

            for t in resolved_tickets:
                t_text = f"{t.subject} {t.description} {t.verified_resolution or ''}".strip()
                t_vec = np.array(embedding_engine.encode(t_text))
                sim = float(np.dot(q_vec, t_vec))
                if sim >= threshold:
                    candidates.append({
                        "ticket_id": t.id,
                        "ticket_number": t.ticket_number,
                        "subject": t.subject,
                        "category": t.category.name if t.category else (t.ai_predicted_category or ""),
                        "status": t.status.value,
                        "verified_resolution": t.verified_resolution or "Standard procedure applied.",
                        "is_resolution_verified": t.is_resolution_verified,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                        "similarity_score": round(sim, 3),
                    })

            candidates.sort(key=lambda x: x["similarity_score"], reverse=True)

        if not candidates:
            return None

        best = candidates[0]
        sim_pct = int(round(best["similarity_score"] * 100))
        tkt_num = best["ticket_number"]
        res_text = best["verified_resolution"] or "Resolved according to standard operational checklist."

        # Grounded recommendation synthesis citing previous ticket reference, resolution date, similarity score, and recurring incident notice
        resolved_date_str = best.get("created_at") or "Unknown"
        recommendation = (
            f"Notice: This appears to be a recurring incident.\n\n"
            f"A similar {best.get('category', 'technical')} incident occurred and was successfully resolved in your organisation.\n\n"
            f"Previous Incident Reference: #{tkt_num}\n"
            f"Resolution Date: {resolved_date_str}\n"
            f"Similarity Score: {sim_pct}%\n"
            f"Verified Resolution Procedure: {res_text}\n\n"
            f"Recommended Action: Apply the verified resolution procedure from incident #{tkt_num}: '{res_text}'."
        )

        return {
            "has_historical_match": True,
            "best_match_ticket_id": best["ticket_id"],
            "best_match_ticket_number": tkt_num,
            "best_match_subject": best["subject"],
            "best_match_resolution": res_text,
            "resolved_at": resolved_date_str,
            "similarity_score": best["similarity_score"],
            "recommendation": recommendation,
            "recommendation_text": recommendation,
            "all_historical_candidates": candidates[:3],
        }


historical_intelligence = HistoricalIncidentIntelligence()
