"""
Organisation-Scoped RAG Document & Verified Resolution Retrieval for QueueMind AI.

Phase 5 Part 7 & Part 8:
- Reads approved knowledge documents AND approved historical ticket resolutions.
- Stores & queries embeddings in Qdrant with organization_id filtering.
- Returns grounded summaries, verified troubleshooting steps, and exact source references.
- Safely handles no-evidence cases:
  "No sufficiently relevant approved knowledge or historical resolution was found. Human investigation is required."
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.ai.vector_store import vector_store
from app.models.knowledge_base import KBApprovalStatus, KnowledgeBase
from app.models.ticket import Ticket, TicketStatus


RAG_EVIDENCE_THRESHOLD = 0.40


class RAGRetriever:
    """
    Retrieves approved knowledge base articles and verified historical resolutions scoped strictly to the organisation.
    """

    @classmethod
    def index_knowledge_base_to_qdrant(cls, db: Session, organization_id: Optional[int] = None) -> int:
        """
        Indexes all approved knowledge base documents into Qdrant vector database.
        """
        query = db.query(KnowledgeBase).filter(KnowledgeBase.approval_status == KBApprovalStatus.APPROVED)
        if organization_id:
            query = query.filter(KnowledgeBase.organization_id == organization_id)

        docs = query.all()
        count = 0
        for doc in docs:
            vector_store.upsert_knowledge_document(
                doc_id=doc.id,
                organization_id=doc.organization_id,
                title=doc.title,
                content=f"{doc.problem_description}\n\nSolution: {doc.solution}",
                category=doc.category.name if doc.category else "General Support",
                tags=doc.tags,
                symptoms=doc.symptoms,
                troubleshooting_steps=doc.troubleshooting_steps,
                verified_resolution=doc.verified_resolution or doc.solution,
                source_type=doc.source_type or "MANUAL_KB",
                source_ticket_id=doc.source_ticket_id,
                is_verified=doc.is_verified,
                approval_status=doc.approval_status.value,
                version=doc.version or "1.0",
            )
            count += 1
        return count

    @classmethod
    def index_verified_historical_resolutions_to_qdrant(cls, db: Session, organization_id: Optional[int] = None) -> int:
        """
        Indexes verified historical ticket resolutions into Qdrant as authoritative knowledge.
        """
        query = db.query(Ticket).filter(
            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            Ticket.is_resolution_verified == True,  # noqa: E712
            Ticket.verified_resolution != None,     # noqa: E711
        )
        if organization_id:
            query = query.filter(Ticket.organization_id == organization_id)

        tickets = query.all()
        count = 0
        for t in tickets:
            vector_store.upsert_ticket(
                ticket_id=t.id,
                organization_id=t.organization_id,
                ticket_number=t.ticket_number,
                subject=t.subject,
                description=t.description,
                category=t.category.name if t.category else (t.ai_predicted_category or "General Support"),
                status=t.status.value,
                confirmed_priority=t.confirmed_priority.value if t.confirmed_priority else None,
                verified_resolution=t.verified_resolution,
                is_resolution_verified=t.is_resolution_verified,
                created_at_iso=t.created_at.isoformat() if t.created_at else None,
            )
            count += 1
        return count

    @classmethod
    def retrieve_context(
        cls,
        db: Session,
        organization_id: int,
        subject: str,
        description: str,
        limit: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves matching approved knowledge base documents for this organisation.
        """
        query_text = f"{subject} {description}".strip()

        # 1. Search via Qdrant
        qdrant_results = vector_store.search_knowledge(
            organization_id=organization_id,
            query_text=query_text,
            limit=limit,
            score_threshold=RAG_EVIDENCE_THRESHOLD,
        )

        if qdrant_results:
            return qdrant_results

        # 2. Database Fallback (Scikit-learn cosine similarity)
        kb_entries: List[KnowledgeBase] = (
            db.query(KnowledgeBase)
            .filter(
                KnowledgeBase.organization_id == organization_id,
                KnowledgeBase.approval_status == KBApprovalStatus.APPROVED,
            )
            .all()
        )

        if not kb_entries:
            return []

        from app.ai.embedding_engine import embedding_engine
        import numpy as np

        q_vec = np.array(embedding_engine.encode(query_text))
        scored = []

        for entry in kb_entries:
            full_text = f"{entry.title} {entry.problem_description} {entry.solution} {entry.symptoms or ''} {entry.troubleshooting_steps or ''}".strip()
            e_vec = np.array(embedding_engine.encode(full_text))
            score = float(np.dot(q_vec, e_vec))
            if score >= RAG_EVIDENCE_THRESHOLD:
                scored.append({
                    "doc_id": entry.id,
                    "title": entry.title,
                    "content": entry.problem_description[:300],
                    "solution": entry.solution[:300],
                    "category": entry.category.name if entry.category else "General Support",
                    "tags": entry.tags,
                    "symptoms": entry.symptoms,
                    "troubleshooting_steps": entry.troubleshooting_steps,
                    "verified_resolution": entry.verified_resolution or entry.solution,
                    "source_type": entry.source_type or "MANUAL_KB",
                    "source_ticket_id": entry.source_ticket_id,
                    "version": entry.version or "1.0",
                    "similarity_score": round(score, 3),
                })

        scored.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored[:limit]

    @classmethod
    def generate_rag_solution(
        cls,
        db: Session,
        organization_id: int,
        subject: str,
        description: str,
        category: str,
        historical_incident: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes grounded RAG synthesis combining approved knowledge documents and verified historical resolutions.
        Handles no-evidence case strictly:
        'No sufficiently relevant approved knowledge or historical resolution was found. Human investigation is required.'
        """
        kb_matches = cls.retrieve_context(db, organization_id, subject, description, limit=3)

        has_docs = len(kb_matches) > 0
        has_history = historical_incident is not None and historical_incident.get("has_historical_match", False)

        if not has_docs and not has_history:
            return {
                "has_sufficient_evidence": False,
                "suggested_solution": "No sufficiently relevant approved knowledge or historical resolution was found. Human investigation is required.",
                "explanation": "No matching approved knowledge base document or verified historical resolution met the minimum relevance threshold for this organisation.",
                "retrieved_documents": [],
                "historical_ticket_references": [],
                "confidence_score": 0.0,
            }

        # Build grounded synthesis
        solutions = []
        doc_refs = []
        hist_refs = []

        if has_docs:
            for d in kb_matches:
                doc_refs.append({
                    "doc_id": d.get("doc_id"),
                    "title": d.get("title"),
                    "category": d.get("category"),
                    "similarity_score": d.get("similarity_score"),
                    "source_type": d.get("source_type"),
                    "troubleshooting_steps": d.get("troubleshooting_steps"),
                })
                step = d.get("troubleshooting_steps") or d.get("solution") or d.get("verified_resolution")
                if step:
                    solutions.append(f"From Knowledge Base ('{d.get('title')}'): {step}")

        if has_history:
            hist_refs.append({
                "ticket_id": historical_incident.get("best_match_ticket_id"),
                "ticket_number": historical_incident.get("best_match_ticket_number"),
                "subject": historical_incident.get("best_match_subject"),
                "resolution": historical_incident.get("best_match_resolution"),
                "similarity_score": historical_incident.get("similarity_score"),
                "resolved_at": historical_incident.get("resolved_at"),
            })
            solutions.append(
                f"From Previous Resolved Incident #{historical_incident.get('best_match_ticket_number')}: "
                f"{historical_incident.get('best_match_resolution')}"
            )

        top_score = max(
            [d["similarity_score"] for d in kb_matches] +
            ([historical_incident["similarity_score"]] if has_history else [0.0])
        )

        suggested_text = "\n\n".join(solutions[:3])
        explanation = (
            f"Grounded recommendation based on {len(doc_refs)} approved knowledge document(s) "
            f"and {len(hist_refs)} verified historical incident(s) from your organisation. "
            f"Peak relevance confidence: {round(top_score * 100, 1)}%."
        )

        return {
            "has_sufficient_evidence": True,
            "suggested_solution": suggested_text,
            "explanation": explanation,
            "retrieved_documents": doc_refs,
            "historical_ticket_references": hist_refs,
            "confidence_score": top_score,
        }


rag_retriever = RAGRetriever()
