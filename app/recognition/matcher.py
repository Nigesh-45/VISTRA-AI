"""Cosine Similarity Matcher and In-Memory Embedding Gallery Store."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
from app.events.event_logger import EventLogger
from app.utils.similarity import cosine_similarity


@dataclass
class MatchResult:
    """Outcome of an embedding matching query against gallery."""
    matched: bool
    face_id: Optional[str]
    similarity: float
    all_scores: Dict[str, float]


class EmbeddingStore:
    """In-memory gallery storing bounded embeddings per persistent visitor face_id."""

    def __init__(self, max_embeddings_per_visitor: int = 5):
        self.max_embeddings = max_embeddings_per_visitor
        # Map face_id -> list of L2-normalized numpy embedding vectors
        self.gallery: Dict[str, List[np.ndarray]] = {}

    def add_embedding(self, face_id: str, embedding: np.ndarray) -> None:
        """Add embedding vector to visitor gallery."""
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        if face_id not in self.gallery:
            self.gallery[face_id] = []

        self.gallery[face_id].append(embedding)
        # Keep bounded gallery
        if len(self.gallery[face_id]) > self.max_embeddings:
            self.gallery[face_id].pop(0)

    def load_from_db(self, db_records: List[Tuple[str, np.ndarray]]) -> None:
        """Populate gallery from database records."""
        self.gallery.clear()
        for face_id, vec in db_records:
            self.add_embedding(face_id, vec)

    def is_empty(self) -> bool:
        return len(self.gallery) == 0


class SimilarityMatcher:
    """Cosine similarity embedding matcher."""

    def __init__(
        self,
        similarity_threshold: float = 0.45,
        event_logger: Optional[EventLogger] = None
    ):
        self.threshold = similarity_threshold
        self.logger = event_logger

    def match(
        self,
        query_embedding: np.ndarray,
        store: EmbeddingStore
    ) -> MatchResult:
        """Query embedding against stored gallery using cosine similarity."""
        if query_embedding is None or store.is_empty():
            return MatchResult(matched=False, face_id=None, similarity=0.0, all_scores={})

        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_embedding = query_embedding / norm

        scores: Dict[str, float] = {}

        best_face_id: Optional[str] = None
        best_similarity: float = -1.0

        for face_id, gallery_vecs in store.gallery.items():
            if not gallery_vecs:
                continue
            # Calculate max cosine similarity against all gallery samples for this visitor
            sims = [float(cosine_similarity(query_embedding, g_vec)) for g_vec in gallery_vecs]
            max_sim = max(sims)
            scores[face_id] = max_sim

            if max_sim > best_similarity:
                best_similarity = max_sim
                best_face_id = face_id

        is_match = best_similarity >= self.threshold and best_face_id is not None

        if is_match and self.logger:
            self.logger.log_event("RECOGNIZED", face_id=best_face_id, confidence=best_similarity)

        return MatchResult(
            matched=is_match,
            face_id=best_face_id if is_match else None,
            similarity=best_similarity if is_match else (best_similarity if best_similarity > 0 else 0.0),
            all_scores=scores
        )
