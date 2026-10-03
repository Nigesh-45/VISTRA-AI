"""SQLAlchemy ORM database models for VISITR-AI."""

from datetime import datetime, timezone
import json
from typing import List, Optional
import numpy as np
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    face_id = Column(String(32), unique=True, nullable=False, index=True)
    first_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    total_visits = Column(Integer, default=1, nullable=False)
    current_status = Column(String(16), default="OUTSIDE", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    embeddings = relationship("Embedding", back_populates="visitor", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="visitor", cascade="all, delete-orphan")
    tracks = relationship("Track", back_populates="visitor", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Visitor(face_id={self.face_id}, visits={self.total_visits}, status={self.current_status})>"


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    face_id = Column(String(32), ForeignKey("visitors.face_id", ondelete="CASCADE"), nullable=False, index=True)
    embedding_data = Column(Text, nullable=False)  # JSON string representation of numpy array
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    visitor = relationship("Visitor", back_populates="embeddings")

    def set_embedding(self, vec: np.ndarray) -> None:
        """Serialize numpy float array to JSON string."""
        self.embedding_data = json.dumps(vec.astype(float).tolist())

    def get_embedding(self) -> np.ndarray:
        """Deserialize JSON string to numpy float array."""
        return np.array(json.loads(self.embedding_data), dtype=np.float32)

    def __repr__(self) -> str:
        return f"<Embedding(id={self.id}, face_id={self.face_id})>"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    face_id = Column(String(32), ForeignKey("visitors.face_id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(Integer, nullable=True)
    event_type = Column(String(16), nullable=False)  # 'ENTRY' or 'EXIT'
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    image_path = Column(String(255), nullable=True)
    confidence = Column(Float, nullable=True)
    frame_number = Column(Integer, nullable=True)

    visitor = relationship("Visitor", back_populates="events")

    __table_args__ = (
        Index("idx_event_face_type", "face_id", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<Event(type={self.event_type}, face_id={self.face_id}, frame={self.frame_number})>"


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    face_id = Column(String(32), ForeignKey("visitors.face_id", ondelete="CASCADE"), nullable=False, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ended_at = Column(DateTime, nullable=True)

    visitor = relationship("Visitor", back_populates="tracks")

    def __repr__(self) -> str:
        return f"<Track(track_id={self.track_id}, face_id={self.face_id})>"
