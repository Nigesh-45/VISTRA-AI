"""Auto-registration engine with best-frame crop buffer selection and persistent Face ID assignment."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import cv2
from sqlalchemy.orm import Session

from app.database.repository import VisitorRepository
from app.events.event_logger import EventLogger
from app.recognition.insightface_engine import InsightFaceEngine
from app.recognition.matcher import EmbeddingStore
from app.utils.image_utils import crop_face, evaluate_face_quality, calculate_sharpness


@dataclass
class FrameCandidate:
    crop: np.ndarray
    confidence: float
    sharpness: float
    area: int
    frame_number: int
    timestamp: float

    @property
    def quality_score(self) -> float:
        """Composite quality score emphasizing size, sharpness, and confidence."""
        return self.confidence * (self.sharpness + 1.0) * np.sqrt(self.area)


class AutoRegistrationEngine:
    """Manages best-frame candidate buffer per track and auto-registers new persistent visitors."""

    def __init__(
        self,
        recognition_engine: InsightFaceEngine,
        embedding_store: EmbeddingStore,
        min_face_size: int = 50,
        min_sharpness: float = 10.0,
        buffer_frames: int = 3,
        event_logger: Optional[EventLogger] = None
    ):
        self.recognition_engine = recognition_engine
        self.embedding_store = embedding_store
        self.min_face_size = min_face_size
        self.min_sharpness = min_sharpness
        self.buffer_frames = buffer_frames
        self.logger = event_logger

        # Map track_id -> List[FrameCandidate]
        self.candidate_buffers: Dict[int, List[FrameCandidate]] = {}

    def add_candidate(
        self,
        track_id: int,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int],
        confidence: float,
        frame_number: int,
        timestamp: float
    ) -> bool:
        """Evaluate and add face crop candidate to track buffer."""
        crop = crop_face(frame, bbox)
        if crop is None:
            return False

        valid, reason = evaluate_face_quality(crop, min_size=self.min_face_size, min_sharpness=self.min_sharpness)
        if not valid:
            if self.logger:
                self.logger.log_event("FACE_REJECTED_LOW_QUALITY", track_id=track_id, metadata={"reason": reason, "bbox": list(bbox)})
            return False

        sharpness = calculate_sharpness(crop)
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        area = max(1, bw * bh)

        cand = FrameCandidate(
            crop=crop,
            confidence=confidence,
            sharpness=sharpness,
            area=area,
            frame_number=frame_number,
            timestamp=timestamp
        )

        if track_id not in self.candidate_buffers:
            self.candidate_buffers[track_id] = []

        self.candidate_buffers[track_id].append(cand)
        # Cap buffer size to prevent memory leaks on prolonged tracking
        if len(self.candidate_buffers[track_id]) > 10:
            self.candidate_buffers[track_id].pop(0)

        return True

    def is_ready_to_register(self, track_id: int) -> bool:
        """Check if candidate buffer has reached required evaluation count."""
        return len(self.candidate_buffers.get(track_id, [])) >= self.buffer_frames

    def register_new_visitor(
        self,
        db_session: Session,
        track_id: int
    ) -> Tuple[Optional[str], Optional[np.ndarray], Optional[np.ndarray]]:
        """Select best candidate crop, extract embedding, and save visitor in DB and gallery.

        Returns:
            Tuple of (face_id: Optional[str], best_crop: Optional[np.ndarray], embedding: Optional[np.ndarray])
        """
        candidates = self.candidate_buffers.get(track_id, [])
        if not candidates:
            return None, None, None

        # Select best candidate by composite quality score
        best_cand = max(candidates, key=lambda c: c.quality_score)

        # Extract embedding vector
        embedding = self.recognition_engine.extract_embedding(best_cand.crop)
        if embedding is None:
            if self.logger:
                self.logger.log_event("FACE_REJECTED_LOW_QUALITY", track_id=track_id, metadata={"reason": "EMBEDDING_EXTRACTION_FAILED"})
            self.clear_buffer(track_id)
            return None, None, None

        # Generate persistent DB-backed Face ID like VIS-00001
        face_id = VisitorRepository.generate_next_face_id(db_session)

        # DB persistence
        visitor = VisitorRepository.create_visitor(db_session, face_id=face_id, current_status="INSIDE")
        VisitorRepository.add_embedding(db_session, face_id=face_id, embedding_vec=embedding)
        VisitorRepository.add_track(db_session, face_id=face_id, track_id=track_id)

        # Add to in-memory matching gallery
        self.embedding_store.add_embedding(face_id, embedding)

        if self.logger:
            self.logger.log_event(
                "NEW_FACE_REGISTERED",
                face_id=face_id,
                track_id=track_id,
                confidence=best_cand.confidence,
                metadata={"quality_score": round(best_cand.quality_score, 2), "sharpness": round(best_cand.sharpness, 1)}
            )

        self.clear_buffer(track_id)
        return face_id, best_cand.crop, embedding

    def clear_buffer(self, track_id: int) -> None:
        """Clear candidate buffer for track."""
        if track_id in self.candidate_buffers:
            del self.candidate_buffers[track_id]
