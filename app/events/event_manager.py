"""EventManager ensuring atomic image saving, DB persistence, and exactly-once event logging."""

from datetime import datetime, timezone
import os
from typing import Optional
import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.database.repository import VisitorRepository
from app.events.event_logger import EventLogger
from app.utils.image_utils import save_image_atomically
from app.utils.time_utils import format_date_dir, format_filename_timestamp


class EventManager:
    """Manages ENTRY and EXIT event creation with atomic file writes and DB transactional integrity."""

    def __init__(
        self,
        entry_dir: str = "logs/entries",
        exit_dir: str = "logs/exits",
        event_logger: Optional[EventLogger] = None
    ):
        self.entry_dir = entry_dir
        self.exit_dir = exit_dir
        self.logger = event_logger

    def _generate_image_path(self, base_dir: str, face_id: str, dt: datetime) -> str:
        """Generate formatted image filepath: base_dir/YYYY-MM-DD/VIS-XXXXX_YYYY-MM-DD_HHMMSS.jpg."""
        date_folder = format_date_dir(dt)
        time_str = format_filename_timestamp(dt)
        folder = os.path.join(base_dir, date_folder)
        os.makedirs(folder, exist_ok=True)

        filename = f"{face_id}_{time_str}.jpg"
        target_path = os.path.join(folder, filename)

        # Avoid collision if saved in same second
        counter = 1
        while os.path.exists(target_path):
            filename = f"{face_id}_{time_str}_{counter}.jpg"
            target_path = os.path.join(folder, filename)
            counter += 1

        return target_path

    def trigger_entry_event(
        self,
        db_session: Session,
        face_id: str,
        track_id: Optional[int],
        face_crop: Optional[np.ndarray],
        confidence: Optional[float] = None,
        frame_number: Optional[int] = None,
        timestamp_dt: Optional[datetime] = None
    ) -> Optional[str]:
        """Process ENTRY event atomically."""
        if timestamp_dt is None:
            timestamp_dt = datetime.now(timezone.utc)

        image_path: Optional[str] = None
        if face_crop is not None and face_crop.size > 0:
            target = self._generate_image_path(self.entry_dir, face_id, timestamp_dt)
            if save_image_atomically(face_crop, target):
                image_path = target

        # Save DB event
        event = VisitorRepository.add_event(
            session=db_session,
            face_id=face_id,
            track_id=track_id,
            event_type="ENTRY",
            timestamp=timestamp_dt,
            image_path=image_path,
            confidence=confidence,
            frame_number=frame_number
        )

        # Update Visitor DB status
        VisitorRepository.update_visitor_status(db_session, face_id=face_id, new_status="INSIDE")

        # Structured Event Log
        if self.logger:
            self.logger.log_event(
                "ENTRY",
                face_id=face_id,
                track_id=track_id,
                confidence=confidence,
                metadata={"image_path": image_path, "frame": frame_number}
            )

        return image_path

    def trigger_exit_event(
        self,
        db_session: Session,
        face_id: str,
        track_id: Optional[int],
        face_crop: Optional[np.ndarray],
        confidence: Optional[float] = None,
        frame_number: Optional[int] = None,
        timestamp_dt: Optional[datetime] = None
    ) -> Optional[str]:
        """Process EXIT event atomically."""
        if timestamp_dt is None:
            timestamp_dt = datetime.now(timezone.utc)

        image_path: Optional[str] = None
        if face_crop is not None and face_crop.size > 0:
            target = self._generate_image_path(self.exit_dir, face_id, timestamp_dt)
            if save_image_atomically(face_crop, target):
                image_path = target

        # Save DB event
        event = VisitorRepository.add_event(
            session=db_session,
            face_id=face_id,
            track_id=track_id,
            event_type="EXIT",
            timestamp=timestamp_dt,
            image_path=image_path,
            confidence=confidence,
            frame_number=frame_number
        )

        # Update Visitor DB status
        VisitorRepository.update_visitor_status(db_session, face_id=face_id, new_status="OUTSIDE")

        # Structured Event Log
        if self.logger:
            self.logger.log_event(
                "EXIT",
                face_id=face_id,
                track_id=track_id,
                confidence=confidence,
                metadata={"image_path": image_path, "frame": frame_number}
            )

        return image_path
