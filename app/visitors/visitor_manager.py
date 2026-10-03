"""Visitor Manager coordinating identity mapping, state machine transitions, and timeout exits."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Set, Tuple
import numpy as np
from sqlalchemy.orm import Session

from app.database.repository import VisitorRepository
from app.events.event_manager import EventManager
from app.events.event_logger import EventLogger
from app.visitors.visitor_state import TemporalPredictionHistory, VisitorStatus


@dataclass
class VisitorTrackState:
    track_id: int
    face_id: Optional[str]
    status: VisitorStatus
    last_bbox: Tuple[int, int, int, int]
    last_crop: Optional[np.ndarray]
    last_confidence: float
    last_seen_frame: int
    missing_frames: int = 0


class VisitorManager:
    """Orchestrates visitor lifecycle, identity smoothing, exactly-once ENTRY/EXIT events, and exit timeouts."""

    def __init__(

        self,
        event_manager: EventManager,
        exit_timeout_frames: int = 30,
        event_logger: Optional[EventLogger] = None
    ):
        self.event_manager = event_manager
        self.exit_timeout_frames = exit_timeout_frames
        self.logger = event_logger

        # Map track_id -> VisitorTrackState
        self.active_tracks: Dict[int, VisitorTrackState] = {}
        # Track history for identity smoothing
        self.temporal_history = TemporalPredictionHistory(history_size=5)

    def process_recognized_track(
        self,
        db_session: Session,
        track_id: int,
        face_id: str,
        bbox: Tuple[int, int, int, int],
        face_crop: Optional[np.ndarray],
        confidence: float,
        frame_number: int
    ) -> VisitorTrackState:
        """Update track with matched face_id and trigger ENTRY event if transitioning from OUTSIDE."""

        self.temporal_history.add_prediction(track_id, face_id)
        smoothed_face_id = self.temporal_history.get_smoothed_face_id(track_id) or face_id

        db_visitor = VisitorRepository.get_visitor(db_session, smoothed_face_id)
        db_status = db_visitor.current_status if db_visitor else "OUTSIDE"

        # Check if face_id is already active under a different track_id
        for existing_tid, existing_state in list(self.active_tracks.items()):
            if existing_tid != track_id and existing_state.face_id == smoothed_face_id:
                del self.active_tracks[existing_tid]
                self.temporal_history.clear_track(existing_tid)

        if track_id in self.active_tracks:
            state = self.active_tracks[track_id]
            state.face_id = smoothed_face_id
            state.last_bbox = bbox
            if face_crop is not None and face_crop.size > 0:
                state.last_crop = face_crop
            state.last_confidence = confidence
            state.last_seen_frame = frame_number
            state.missing_frames = 0
        else:
            state = VisitorTrackState(
                track_id=track_id,
                face_id=smoothed_face_id,
                status=VisitorStatus.INSIDE if db_status == "INSIDE" else VisitorStatus.OUTSIDE,
                last_bbox=bbox,
                last_crop=face_crop,
                last_confidence=confidence,
                last_seen_frame=frame_number,
                missing_frames=0
            )
            self.active_tracks[track_id] = state

        # Check if ENTRY event is required (visitor was OUTSIDE)
        if state.status == VisitorStatus.OUTSIDE:
            if db_visitor and db_visitor.current_status == "OUTSIDE" and db_visitor.total_visits >= 1 and state.last_seen_frame > 0:
                VisitorRepository.increment_visits(db_session, smoothed_face_id)

            state.status = VisitorStatus.INSIDE
            self.event_manager.trigger_entry_event(
                db_session=db_session,
                face_id=smoothed_face_id,
                track_id=track_id,
                face_crop=face_crop,
                confidence=confidence,
                frame_number=frame_number
            )

        return state

    def update_missing_tracks(
        self,
        db_session: Session,
        current_visible_track_ids: Set[int],
        frame_number: int
    ) -> None:
        """Increment missing count for unseen tracks and trigger EXIT events when timeout exceeded."""

        tracks_to_remove = []

        for track_id, state in list(self.active_tracks.items()):
            if track_id not in current_visible_track_ids:
                state.missing_frames += 1

                if state.missing_frames >= self.exit_timeout_frames:
                    # Timeout exceeded -> Trigger EXIT Event
                    if state.face_id and state.status == VisitorStatus.INSIDE:
                        self.event_manager.trigger_exit_event(
                            db_session=db_session,
                            face_id=state.face_id,
                            track_id=track_id,
                            face_crop=state.last_crop,
                            confidence=state.last_confidence,
                            frame_number=frame_number
                        )
                        state.status = VisitorStatus.OUTSIDE

                    VisitorRepository.end_track(db_session, track_id)
                    tracks_to_remove.append(track_id)

        for tid in tracks_to_remove:
            del self.active_tracks[tid]
            self.temporal_history.clear_track(tid)

    def force_flush_exits(self, db_session: Session, frame_number: int) -> None:
        """Force trigger EXIT events for all remaining active tracks on shutdown."""
        for track_id, state in list(self.active_tracks.items()):
            if state.face_id and state.status == VisitorStatus.INSIDE:
                self.event_manager.trigger_exit_event(
                    db_session=db_session,
                    face_id=state.face_id,
                    track_id=track_id,
                    face_crop=state.last_crop,
                    confidence=state.last_confidence,
                    frame_number=frame_number
                )
                state.status = VisitorStatus.OUTSIDE
            VisitorRepository.end_track(db_session, track_id)

        self.active_tracks.clear()
