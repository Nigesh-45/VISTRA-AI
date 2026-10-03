"""Adversarial Audit Test Suite for Exactly-Once Event Integrity and Storage Consistency."""

import glob
import os
import pytest
import numpy as np

from app.database.database import DatabaseManager
from app.database.repository import VisitorRepository
from app.events.event_logger import EventLogger
from app.events.event_manager import EventManager
from app.visitors.visitor_manager import VisitorManager
from app.visitors.visitor_state import VisitorStatus


@pytest.fixture
def event_audit_env(tmp_path):
    db_file = tmp_path / "event_audit.db"
    db_mgr = DatabaseManager(f"sqlite:///{db_file}")
    db_mgr.init_db()

    entry_dir = tmp_path / "entries"
    exit_dir = tmp_path / "exits"
    log_file = tmp_path / "events.log"

    event_logger = EventLogger(log_file_path=str(log_file))
    event_mgr = EventManager(
        entry_dir=str(entry_dir),
        exit_dir=str(exit_dir),
        event_logger=event_logger
    )
    vis_mgr = VisitorManager(
        event_manager=event_mgr,
        exit_timeout_frames=5,
        event_logger=event_logger
    )

    return db_mgr, event_mgr, vis_mgr, entry_dir, exit_dir, log_file


def test_adversarial_exactly_once_event_lifecycle(event_audit_env):
    db_mgr, event_mgr, vis_mgr, entry_dir, exit_dir, log_file = event_audit_env
    crop = np.zeros((80, 80, 3), dtype=np.uint8)

    # Register initial visitor VIS-00001
    with db_mgr.get_session() as session:
        face_id1 = VisitorRepository.generate_next_face_id(session)  # VIS-00001
        VisitorRepository.create_visitor(session, face_id1, current_status="OUTSIDE")

    # --- SCENARIO 1: One Visitor Visible for 500 Frames ---
    with db_mgr.get_session() as session:
        for f in range(1, 501):
            vis_mgr.process_recognized_track(
                db_session=session,
                track_id=1,
                face_id="VIS-00001",
                bbox=(10, 10, 90, 90),
                face_crop=crop,
                confidence=0.95,
                frame_number=f
            )

        events = VisitorRepository.get_events(session)
        entries = [e for e in events if e.event_type == "ENTRY"]
        exits = [e for e in events if e.event_type == "EXIT"]

        # VERIFY: Exactly 1 ENTRY, 0 EXITS across 500 frames
        assert len(entries) == 1
        assert len(exits) == 0

    # --- SCENARIO 2: Temporary Detection Loss (2 missing frames < timeout 5) ---
    with db_mgr.get_session() as session:
        vis_mgr.update_missing_tracks(session, current_visible_track_ids=set(), frame_number=501)
        vis_mgr.update_missing_tracks(session, current_visible_track_ids=set(), frame_number=502)

        # Reappears on frame 503
        vis_mgr.process_recognized_track(
            db_session=session,
            track_id=1,
            face_id="VIS-00001",
            bbox=(10, 10, 90, 90),
            face_crop=crop,
            confidence=0.95,
            frame_number=503
        )

        events = VisitorRepository.get_events(session)
        entries = [e for e in events if e.event_type == "ENTRY"]
        exits = [e for e in events if e.event_type == "EXIT"]

        # VERIFY: Temporary loss does NOT create EXIT or duplicate ENTRY
        assert len(entries) == 1
        assert len(exits) == 0

    # --- SCENARIO 3: Permanent Disappearance (> timeout 5 frames) ---
    with db_mgr.get_session() as session:
        for f in range(504, 515):
            vis_mgr.update_missing_tracks(session, current_visible_track_ids=set(), frame_number=f)

        events = VisitorRepository.get_events(session)
        entries = [e for e in events if e.event_type == "ENTRY"]
        exits = [e for e in events if e.event_type == "EXIT"]

        # VERIFY: Permanent loss creates exactly ONE EXIT
        assert len(entries) == 1
        assert len(exits) == 1
        assert VisitorRepository.get_visitor(session, "VIS-00001").current_status == "OUTSIDE"

    # --- SCENARIO 4: Return of the Same Visitor (with NEW track_id = 88) ---
    with db_mgr.get_session() as session:
        vis_mgr.process_recognized_track(
            db_session=session,
            track_id=88,  # NEW TRACK ID
            face_id="VIS-00001",  # SAME PERSISTENT FACE ID
            bbox=(10, 10, 90, 90),
            face_crop=crop,
            confidence=0.94,
            frame_number=600
        )

        events = VisitorRepository.get_events(session)
        entries = [e for e in events if e.event_type == "ENTRY"]
        exits = [e for e in events if e.event_type == "EXIT"]

        # VERIFY: Return creates 1 new ENTRY (Total 2 entries, 1 exit)
        assert len(entries) == 2
        assert len(exits) == 1

        # VERIFY: Unique visitor count remains EXACTLY 1
        assert VisitorRepository.count_unique_visitors(session) == 1

    # --- SCENARIO 5: Two Visitors Simultaneously (VIS-00001 & VIS-00002) ---
    with db_mgr.get_session() as session:
        face_id2 = VisitorRepository.generate_next_face_id(session)  # VIS-00002
        VisitorRepository.create_visitor(session, face_id2, current_status="OUTSIDE")

        # Frame 601: Both visible simultaneously
        vis_mgr.process_recognized_track(session, track_id=88, face_id="VIS-00001", bbox=(10, 10, 90, 90), face_crop=crop, confidence=0.95, frame_number=601)
        vis_mgr.process_recognized_track(session, track_id=99, face_id="VIS-00002", bbox=(200, 200, 280, 280), face_crop=crop, confidence=0.91, frame_number=601)

        events = VisitorRepository.get_events(session)
        entries = [e for e in events if e.event_type == "ENTRY"]

        # VERIFY: VIS-00002 generated 1 ENTRY, VIS-00001 remained inside without duplicate entry
        assert len(entries) == 3  # (VIS-00001 Entry #1, VIS-00001 Entry #2, VIS-00002 Entry #1)
        assert VisitorRepository.count_unique_visitors(session) == 2

    # --- SCENARIO 6: New Tracker ID for Existing Visitor Already Inside ---
    with db_mgr.get_session() as session:
        # VIS-00001 tracker ID switches from 88 to 105 while VIS-00001 is ALREADY INSIDE
        vis_mgr.process_recognized_track(session, track_id=105, face_id="VIS-00001", bbox=(15, 15, 95, 95), face_crop=crop, confidence=0.93, frame_number=602)

        events = VisitorRepository.get_events(session)
        entries = [e for e in events if e.event_type == "ENTRY"]

        # VERIFY: NO duplicate ENTRY generated when tracker ID shifts while visitor is already INSIDE!
        assert len(entries) == 3

    # Flush remaining active tracks for exit
    with db_mgr.get_session() as session:
        vis_mgr.force_flush_exits(session, frame_number=700)

        events = VisitorRepository.get_events(session)
        exits = [e for e in events if e.event_type == "EXIT"]
        assert len(exits) == 3  # (VIS-00001 Exit #1, VIS-00001 Exit #2, VIS-00002 Exit #1)

    # --- SCENARIO 7: Storage & Log Agreement Consistency Check ---
    with db_mgr.get_session() as session:
        db_events = VisitorRepository.get_events(session)
        assert len(db_events) == 6  # 3 ENTRY + 3 EXIT events

        # Verify DB image paths exist on filesystem
        for ev in db_events:
            assert ev.image_path is not None
            assert os.path.exists(ev.image_path)
            assert os.path.getsize(ev.image_path) > 0

    # Verify log file contains matching event entries
    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()
        assert log_content.count("EVENT=ENTRY") >= 3
        assert log_content.count("EVENT=EXIT") >= 3
