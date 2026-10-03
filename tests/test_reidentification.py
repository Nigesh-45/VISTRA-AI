import pytest
import numpy as np
import cv2
from app.database.database import DatabaseManager
from app.database.repository import VisitorRepository
from app.events.event_manager import EventManager
from app.visitors.visitor_manager import VisitorManager


@pytest.fixture
def setup_env():
    db_mgr = DatabaseManager("sqlite:///:memory:")
    db_mgr.init_db()
    ev_mgr = EventManager(entry_dir="logs/entries", exit_dir="logs/exits")
    vis_mgr = VisitorManager(event_manager=ev_mgr, exit_timeout_frames=5)
    return db_mgr, ev_mgr, vis_mgr


def test_reidentification_count_integrity(setup_env):
    db_mgr, ev_mgr, vis_mgr = setup_env

    crop = np.zeros((100, 100, 3), dtype=np.uint8)

    # 1. Visitor enters under Track 17
    with db_mgr.get_session() as session:
        face_id = VisitorRepository.generate_next_face_id(session)
        assert face_id == "VIS-00001"
        VisitorRepository.create_visitor(session, face_id, current_status="INSIDE")

        # First Entry
        vis_mgr.process_recognized_track(
            db_session=session,
            track_id=17,
            face_id=face_id,
            bbox=(10, 10, 50, 50),
            face_crop=crop,
            confidence=0.95,
            frame_number=1
        )

        unique_cnt1 = VisitorRepository.count_unique_visitors(session)
        assert unique_cnt1 == 1

    # 2. Track 17 disappears and exits (timeout = 5 frames)
    with db_mgr.get_session() as session:
        for f in range(2, 8):
            vis_mgr.update_missing_tracks(session, current_visible_track_ids=set(), frame_number=f)

        vis = VisitorRepository.get_visitor(session, "VIS-00001")
        assert vis.current_status == "OUTSIDE"

        unique_cnt2 = VisitorRepository.count_unique_visitors(session)
        assert unique_cnt2 == 1

    # 3. Same visitor re-enters with a NEW track ID (Track 31)
    with db_mgr.get_session() as session:
        vis_mgr.process_recognized_track(
            db_session=session,
            track_id=31,  # NEW TRACK ID
            face_id="VIS-00001",  # SAME PERSISTENT FACE ID
            bbox=(10, 10, 50, 50),
            face_crop=crop,
            confidence=0.92,
            frame_number=20
        )

        vis = VisitorRepository.get_visitor(session, "VIS-00001")
        assert vis.current_status == "INSIDE"
        assert vis.total_visits == 2  # Incremented visits counter

        unique_cnt3 = VisitorRepository.count_unique_visitors(session)
        # CRITICAL ASSERTION: Unique count MUST NOT INCREASE!
        assert unique_cnt3 == 1
