"""Repository pattern implementations for database entities."""

from datetime import datetime, timezone
from typing import List, Tuple, Optional
import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.models import Visitor, Embedding, Event, Track


class VisitorRepository:
    """Repository handling all CRUD and query operations for VISITR-AI."""

    @staticmethod
    def generate_next_face_id(session: Session) -> str:
        """Generate persistent database-backed Face ID like VIS-00001."""
        max_id = session.query(func.max(Visitor.id)).scalar()
        next_num = (max_id or 0) + 1
        return f"VIS-{next_num:05d}"

    @staticmethod
    def get_visitor(session: Session, face_id: str) -> Optional[Visitor]:
        """Fetch visitor record by face_id."""
        return session.query(Visitor).filter(Visitor.face_id == face_id).first()

    @staticmethod
    def create_visitor(session: Session, face_id: str, current_status: str = "INSIDE") -> Visitor:
        """Register a new visitor in database."""
        now = datetime.now(timezone.utc)
        visitor = Visitor(
            face_id=face_id,
            first_seen=now,
            last_seen=now,
            total_visits=1,
            current_status=current_status,
            created_at=now
        )
        session.add(visitor)
        session.flush()
        return visitor

    @staticmethod
    def update_visitor_status(session: Session, face_id: str, new_status: str) -> Optional[Visitor]:
        """Update current_status and last_seen for visitor."""
        visitor = VisitorRepository.get_visitor(session, face_id)
        if visitor:
            visitor.current_status = new_status
            visitor.last_seen = datetime.now(timezone.utc)
            session.flush()
        return visitor

    @staticmethod
    def increment_visits(session: Session, face_id: str) -> Optional[Visitor]:
        """Increment total_visits counter for re-identified returning visitor."""
        visitor = VisitorRepository.get_visitor(session, face_id)
        if visitor:
            visitor.total_visits += 1
            visitor.current_status = "INSIDE"
            visitor.last_seen = datetime.now(timezone.utc)
            session.flush()
        return visitor

    @staticmethod
    def count_unique_visitors(session: Session) -> int:
        """Count total unique persistent visitors in database."""
        return session.query(Visitor).count()

    @staticmethod
    def add_embedding(session: Session, face_id: str, embedding_vec: np.ndarray) -> Embedding:
        """Add face embedding vector to database."""
        emb = Embedding(
            face_id=face_id,
            created_at=datetime.now(timezone.utc)
        )
        emb.set_embedding(embedding_vec)
        session.add(emb)
        session.flush()
        return emb

    @staticmethod
    def get_all_embeddings(session: Session) -> List[Tuple[str, np.ndarray]]:
        """Retrieve all stored embeddings paired with their face_ids."""
        records = session.query(Embedding).all()
        return [(rec.face_id, rec.get_embedding()) for rec in records]

    @staticmethod
    def add_event(
        session: Session,
        face_id: str,
        track_id: Optional[int],
        event_type: str,
        timestamp: Optional[datetime] = None,
        image_path: Optional[str] = None,
        confidence: Optional[float] = None,
        frame_number: Optional[int] = None
    ) -> Event:
        """Record an ENTRY or EXIT event in the database."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        event = Event(
            face_id=face_id,
            track_id=track_id,
            event_type=event_type,
            timestamp=timestamp,
            image_path=image_path,
            confidence=confidence,
            frame_number=frame_number
        )
        session.add(event)
        session.flush()
        return event

    @staticmethod
    def get_events(session: Session, limit: int = 50) -> List[Event]:
        """Fetch recent events sorted by timestamp descending."""
        return session.query(Event).order_by(Event.timestamp.desc()).limit(limit).all()

    @staticmethod
    def add_track(session: Session, face_id: str, track_id: int) -> Track:
        """Record a temporary track associated with a persistent face_id."""
        track = Track(
            face_id=face_id,
            track_id=track_id,
            started_at=datetime.now(timezone.utc)
        )
        session.add(track)
        session.flush()
        return track

    @staticmethod
    def end_track(session: Session, track_id: int) -> None:
        """Mark track as ended."""
        track = session.query(Track).filter(Track.track_id == track_id, Track.ended_at.is_(None)).first()
        if track:
            track.ended_at = datetime.now(timezone.utc)
            session.flush()
