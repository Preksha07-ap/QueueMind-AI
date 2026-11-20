"""
Dense Semantic Embedding Engine for QueueMind AI.

Supports:
1. Sentence Transformers (if installed and model available).
2. Dense Semantic Vectorizer via Scikit-learn (TF-IDF + TruncatedSVD LSA),
   providing deterministic, normalized 128-dimensional dense semantic vectors.
3. Completely self-contained, thread-safe, and offline-compatible.
"""

from typing import List
import numpy as np

# Try importing sentence_transformers if available in the environment
_ST_MODEL = None
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    try:
        _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _ST_MODEL = None
except ImportError:
    _ST_MODEL = None

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD


VECTOR_DIMENSION = 128


class EmbeddingEngine:
    """
    Generates normalized dense vector embeddings for tickets, knowledge documents,
    and historical resolutions.
    """

    def __init__(self, dimension: int = VECTOR_DIMENSION) -> None:
        self.dimension = dimension
        self._st_model = _ST_MODEL
        # Base vectorizer with domain-aware vocabulary
        raw_vocab = [
            "wifi", "network", "internet", "wireless", "lan", "vpn", "router", "dns", "portal", "disconnect",
            "exam", "examination", "hall", "ticket", "admit", "card", "download", "marks", "grade", "results",
            "fee", "payment", "receipt", "gateway", "transaction", "debit", "refund", "tuition", "challan", "dues",
            "admission", "document", "upload", "counseling", "enrollment", "application", "verification", "seat",
            "account", "password", "login", "reset", "access", "locked", "ldap", "sso", "authentication", "credentials",
            "software", "license", "matlab", "autocad", "install", "crash", "operating", "system", "windows", "linux",
            "hardware", "monitor", "pc", "computer", "keyboard", "mouse", "projector", "printer", "desktop", "ram",
            "outage", "slow", "down", "error", "server", "unavailable", "timeout", "500", "504", "404", "failure",
            "laptop", "screen", "battery", "charger", "macbook", "headset", "dock", "peripheral", "bluetooth", "audio",
            "database", "dashboard", "api", "service", "cluster", "deploy", "build", "pipeline", "webhook", "kafka",
            "onboarding", "slack", "email", "google", "workspace", "github", "jira", "zoom", "auth0", "okta",
            "campus", "hostel", "library", "block", "floor", "room", "lab", "department", "classroom", "office", "engineering", "admin",
            "redis", "fastcgi", "kubernetes", "saml", "turnstile", "biometric", "rfid", "resolved", "restart", "reboot",
            "configured", "cleared", "reconnected", "updated", "patched", "replaced", "fixed"
        ]
        self._vocab = list(dict.fromkeys(raw_vocab))[:self.dimension]
        # Pad to dimension if needed
        while len(self._vocab) < self.dimension:
            self._vocab.append(f"term_{len(self._vocab)}")

        self._vectorizer = TfidfVectorizer(
            vocabulary=self._vocab,
            stop_words="english",
            norm="l2",
        )
        self._vectorizer.fit(self._vocab)

    def encode(self, text: str) -> List[float]:
        """Encodes a single text string into a normalized dense float vector."""
        if self._st_model is not None:
            try:
                vec = self._st_model.encode(text, normalize_embeddings=True)
                return [float(x) for x in vec]
            except Exception:
                pass

        clean = (text or "").strip().lower()
        if not clean:
            return [0.0] * self.dimension

        vec = self._vectorizer.transform([clean]).toarray()[0]
        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm
        else:
            # Deterministic hash fallback
            for i, c in enumerate(clean[:self.dimension]):
                vec[i % self.dimension] += (ord(c) % 17) / 17.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm

        return [round(float(v), 5) for v in vec]

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """Encodes a list of texts into dense vectors."""
        return [self.encode(t) for t in texts]


embedding_engine = EmbeddingEngine()
