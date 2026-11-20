"""
Ollama Service Integration for QueueMind AI.

Requirement:
- Interfaces with Ollama (Qwen / Llama) for grounded language summaries and explanations.
- Never fabricates AI output when the service is unreachable.
- Fails safely with explicit status reporting if Ollama is offline.
"""

from typing import Dict, List, Optional
import httpx
from app.core.config import settings


import time

class OllamaService:
    """
    Interfaces with Ollama HTTP API for LLM-grounded incident summarisation.
    """

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL
        self._last_check_time = 0.0
        self._cached_available = False

    def is_service_available(self) -> bool:
        """Checks if local Ollama daemon is reachable with a low timeout, cached for 30s."""
        now = time.time()
        if now - self._last_check_time < 30.0:
            return self._cached_available
        self._last_check_time = now
        try:
            with httpx.Client(timeout=0.4) as client:
                res = client.get(f"{self.base_url}/api/tags")
                self._cached_available = (res.status_code == 200)
                return self._cached_available
        except Exception:
            self._cached_available = False
            return False

    def generate_grounded_summary(
        self,
        subject: str,
        description: str,
        category: str,
        priority: str,
        kb_context: Optional[List[Dict[str, object]]] = None,
    ) -> Dict[str, object]:
        """
        Requests an LLM summary from Ollama if available.
        Returns status 'AVAILABLE' with summary, or 'UNAVAILABLE' on failure.
        """
        if not self.is_service_available():
            return {
                "status": "UNAVAILABLE",
                "summary": None,
                "troubleshooting_steps": None,
                "service_url": self.base_url,
                "model": self.model,
                "note": f"Ollama daemon not reachable at {self.base_url}. Analysis flagged for manual Help Desk triage.",
            }

        # Build prompt grounded on ticket and KB context
        kb_text = ""
        if kb_context:
            kb_text = "\n".join([
                f"- Relevant Solution from Knowledge Base: {item.get('title')}: {item.get('solution')}"
                for item in kb_context
            ])

        prompt = (
            f"You are the QueueMind AI triage assistant for an educational helpdesk.\n"
            f"Analyze this support incident and provide a concise 2-sentence summary and 2 immediate troubleshooting checks.\n\n"
            f"Ticket Subject: {subject}\n"
            f"Description: {description}\n"
            f"Classified Category: {category}\n"
            f"Calculated Priority: {priority}\n"
        )
        if kb_text:
            prompt += f"\nKnown Approved Resolutions:\n{kb_text}\n"

        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    response_text = data.get("response", "").strip()
                    return {
                        "status": "AVAILABLE",
                        "summary": response_text,
                        "model": self.model,
                        "service_url": self.base_url,
                    }
                else:
                    return {
                        "status": "FAILED",
                        "summary": None,
                        "note": f"Ollama returned HTTP status {res.status_code}",
                        "service_url": self.base_url,
                    }
        except Exception as ex:
            return {
                "status": "FAILED",
                "summary": None,
                "note": f"Ollama generation timed out or failed: {str(ex)}",
                "service_url": self.base_url,
            }


ollama_service = OllamaService()
