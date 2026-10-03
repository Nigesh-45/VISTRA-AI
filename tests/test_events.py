import os
import pytest
import numpy as np
from app.database.database import DatabaseManager
from app.events.event_manager import EventManager
from app.database.repository import VisitorRepository


def test_event_manager_atomic(tmp_path):
    entry_dir = tmp_path / "entries"
    exit_dir = tmp_path / "exits"

    db = DatabaseManager("sqlite:///:memory:")
    db.init_db()
    mgr = EventManager(entry_dir=str(entry_dir), exit_dir=str(exit_dir))

    crop = np.zeros((60, 60, 3), dtype=np.uint8)

    with db.get_session() as session:
        face_id = VisitorRepository.generate_next_face_id(session)
        VisitorRepository.create_visitor(session, face_id)

        # Trigger ENTRY
        img_path = mgr.trigger_entry_event(
            db_session=session,
            face_id=face_id,
            track_id=1,
            face_crop=crop,
            confidence=0.95,
            frame_number=10
        )

        assert img_path is not None
        assert os.path.exists(img_path)
        assert os.path.getsize(img_path) > 0

        # Trigger EXIT
        exit_path = mgr.trigger_exit_event(
            db_session=session,
            face_id=face_id,
            track_id=1,
            face_crop=crop,
            confidence=0.91,
            frame_number=50
        )

        assert exit_path is not None
        assert os.path.exists(exit_path)
        assert os.path.getsize(exit_path) > 0

        events = VisitorRepository.get_events(session)
        assert len(events) == 2
        types = [e.event_type for e in events]
        assert "ENTRY" in types
        assert "EXIT" in types
