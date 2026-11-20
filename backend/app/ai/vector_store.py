"""
Qdrant Vector Database Integration for QueueMind AI.

Manages:
1. 'tickets_semantic' collection: Ticket vectors for duplicate detection and historical incident intelligence.
2. 'knowledge_base_semantic' collection: Document chunks and approved resolution procedures for RAG.

Guarantees:
- Strict multi-tenant isolation via mandatory organization_id payload filtering.
- Seamless embedded/in-memory operation or live Qdrant daemon connection.
- COSINE distance metric.
"""

import logging
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.ai.embedding_engine import VECTOR_DIMENSION, embedding_engine
from app.core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_TICKETS = "tickets_semantic"
COLLECTION_KNOWLEDGE = "knowledge_base_semantic"


class QdrantVectorStore:
    """
    Qdrant client wrapper supporting multi-tenant semantic search.
    """

    def __init__(self) -> None:
        self.dimension = VECTOR_DIMENSION
        self._init_client()
        self._ensure_collections()

    def _init_client(self) -> None:
        """Attempts connection to remote Qdrant daemon, falling back to embedded/in-memory client."""
        try:
            client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=1.0)
            # Test connectivity
            client.get_collections()
            self.client = client
            self.is_embedded = False
            logger.info("Connected to external Qdrant daemon at %s:%s", settings.QDRANT_HOST, settings.QDRANT_PORT)
        except Exception:
            # Fallback to in-memory Qdrant instance
            self.client = QdrantClient(":memory:")
            self.is_embedded = True
            logger.info("Using embedded in-memory Qdrant instance")

    def _ensure_collections(self) -> None:
        """Creates required collections if they do not already exist."""
        for name in [COLLECTION_TICKETS, COLLECTION_KNOWLEDGE]:
            try:
                collections = [c.name for c in self.client.get_collections().collections]
                if name not in collections:
                    self.client.create_collection(
                        collection_name=name,
                        vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
                    )
            except Exception as e:
                logger.warning("Failed ensuring collection %s: %s", name, e)

    def upsert_ticket(
        self,
        ticket_id: int,
        organization_id: int,
        ticket_number: str,
        subject: str,
        description: str,
        category: str,
        status: str,
        confirmed_priority: Optional[str] = None,
        verified_resolution: Optional[str] = None,
        is_resolution_verified: bool = False,
        created_at_iso: Optional[str] = None,
    ) -> None:
        """Indexes or updates a ticket vector in Qdrant with tenant-scoped payload."""
        text = f"{subject} {description} {category}".strip()
        vector = embedding_engine.encode(text)

        payload: Dict[str, Any] = {
            "ticket_id": ticket_id,
            "organization_id": organization_id,
            "ticket_number": ticket_number,
            "subject": subject,
            "description": description[:300],
            "category": category,
            "status": status,
            "priority": confirmed_priority or "MEDIUM",
            "is_resolved": status in ["RESOLVED", "CLOSED"],
            "verified_resolution": verified_resolution,
            "is_resolution_verified": is_resolution_verified,
            "created_at": created_at_iso,
        }

        self.client.upsert(
            collection_name=COLLECTION_TICKETS,
            points=[PointStruct(id=ticket_id, vector=vector, payload=payload)],
        )

    def search_similar_tickets(
        self,
        organization_id: int,
        query_text: str,
        exclude_ticket_id: Optional[int] = None,
        only_resolved: bool = False,
        limit: int = 5,
        score_threshold: float = 0.50,
    ) -> List[Dict[str, Any]]:
        """
        Searches tickets strictly scoped to organization_id.
        Prevents cross-tenant access at the vector database filter level.
        """
        vector = embedding_engine.encode(query_text)

        must_conditions = [
            FieldCondition(key="organization_id", match=MatchValue(value=organization_id))
        ]
        if only_resolved:
            must_conditions.append(
                FieldCondition(key="is_resolved", match=MatchValue(value=True))
            )

        qdrant_filter = Filter(must=must_conditions)

        try:
            results = self.client.query_points(
                collection_name=COLLECTION_TICKETS,
                query=vector,
                query_filter=qdrant_filter,
                limit=limit + (1 if exclude_ticket_id else 0),
                score_threshold=score_threshold,
            ).points
        except Exception as e:
            logger.error("Qdrant ticket search error: %s", e)
            return []

        hits = []
        for point in results:
            if exclude_ticket_id and point.id == exclude_ticket_id:
                continue
            payload = point.payload or {}
            hits.append({
                "ticket_id": payload.get("ticket_id"),
                "ticket_number": payload.get("ticket_number"),
                "subject": payload.get("subject"),
                "category": payload.get("category"),
                "status": payload.get("status"),
                "priority": payload.get("priority"),
                "is_resolved": payload.get("is_resolved"),
                "verified_resolution": payload.get("verified_resolution"),
                "is_resolution_verified": payload.get("is_resolution_verified"),
                "created_at": payload.get("created_at"),
                "similarity_score": round(float(point.score), 3),
            })
            if len(hits) >= limit:
                break

        return hits

    def upsert_knowledge_document(
        self,
        doc_id: int,
        organization_id: int,
        title: str,
        content: str,
        category: str,
        tags: Optional[str] = None,
        symptoms: Optional[str] = None,
        troubleshooting_steps: Optional[str] = None,
        verified_resolution: Optional[str] = None,
        source_type: str = "MANUAL_KB",
        source_ticket_id: Optional[int] = None,
        is_verified: bool = True,
        approval_status: str = "APPROVED",
        version: str = "1.0",
    ) -> None:
        """Indexes an approved knowledge document or verified resolution in Qdrant."""
        text = f"{title} {content} {symptoms or ''} {troubleshooting_steps or ''} {category}".strip()
        vector = embedding_engine.encode(text)

        payload: Dict[str, Any] = {
            "doc_id": doc_id,
            "organization_id": organization_id,
            "title": title,
            "content": content[:600],
            "category": category,
            "tags": tags,
            "symptoms": symptoms,
            "troubleshooting_steps": troubleshooting_steps,
            "verified_resolution": verified_resolution,
            "source_type": source_type,
            "source_ticket_id": source_ticket_id,
            "is_verified": is_verified,
            "approval_status": approval_status,
            "version": version,
        }

        self.client.upsert(
            collection_name=COLLECTION_KNOWLEDGE,
            points=[PointStruct(id=doc_id, vector=vector, payload=payload)],
        )

    def search_knowledge(
        self,
        organization_id: int,
        query_text: str,
        limit: int = 4,
        score_threshold: float = 0.35,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves approved knowledge documents strictly for organization_id.
        Unapproved or cross-tenant records are filtered out.
        """
        vector = embedding_engine.encode(query_text)

        qdrant_filter = Filter(
            must=[
                FieldCondition(key="organization_id", match=MatchValue(value=organization_id)),
                FieldCondition(key="approval_status", match=MatchValue(value="APPROVED")),
            ]
        )

        try:
            results = self.client.query_points(
                collection_name=COLLECTION_KNOWLEDGE,
                query=vector,
                query_filter=qdrant_filter,
                limit=limit,
                score_threshold=score_threshold,
            ).points
        except Exception as e:
            logger.error("Qdrant knowledge search error: %s", e)
            return []

        hits = []
        for point in results:
            payload = point.payload or {}
            hits.append({
                "doc_id": payload.get("doc_id"),
                "title": payload.get("title"),
                "content": payload.get("content"),
                "category": payload.get("category"),
                "tags": payload.get("tags"),
                "symptoms": payload.get("symptoms"),
                "troubleshooting_steps": payload.get("troubleshooting_steps"),
                "verified_resolution": payload.get("verified_resolution"),
                "source_type": payload.get("source_type"),
                "source_ticket_id": payload.get("source_ticket_id"),
                "version": payload.get("version"),
                "similarity_score": round(float(point.score), 3),
            })

        return hits

    def count_points(self, collection_name: str) -> int:
        """Returns total points indexed in a collection."""
        try:
            info = self.client.get_collection(collection_name)
            return info.points_count or 0
        except Exception:
            return 0


vector_store = QdrantVectorStore()
