"""Adversarial Audit Test Suite for Identity Recognition, Re-Identification, and Quality Filters."""

import os
import pytest
import numpy as np
import cv2

from app.database.database import DatabaseManager
from app.database.repository import VisitorRepository
from app.events.event_manager import EventManager
from app.recognition.insightface_engine import InsightFaceEngine
from app.recognition.matcher import SimilarityMatcher, EmbeddingStore
from app.registration.auto_registration import AutoRegistrationEngine
from app.utils.similarity import cosine_similarity
from app.visitors.visitor_manager import VisitorManager
from app.visitors.visitor_state import TemporalPredictionHistory


@pytest.fixture
def setup_audit_env(tmp_path):
    db_file = tmp_path / "audit_visitors.db"
    db_mgr = DatabaseManager(f"sqlite:///{db_file}")
    db_mgr.init_db()

    entry_dir = tmp_path / "entries"
    exit_dir = tmp_path / "exits"
    ev_mgr = EventManager(entry_dir=str(entry_dir), exit_dir=str(exit_dir))
    vis_mgr = VisitorManager(event_manager=ev_mgr, exit_timeout_frames=3)

    rec_engine = InsightFaceEngine(model_name="buffalo_sc")
    store = EmbeddingStore()
    matcher = SimilarityMatcher(similarity_threshold=0.45)
    reg_engine = AutoRegistrationEngine(
        recognition_engine=rec_engine,
        embedding_store=store,
        min_face_size=30,
        min_sharpness=5.0,
        buffer_frames=2
    )

    return db_mgr, ev_mgr, vis_mgr, rec_engine, store, matcher, reg_engine


# --- TEST 1: New Face -> Registration ---
def test_audit_scenario_1_new_face_registration(setup_audit_env):
    db_mgr, _, _, _, store, _, reg_engine = setup_audit_env

    # High quality synthetic face crop
    frame = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.circle(frame, (150, 150), 60, (220, 200, 180), -1)
    cv2.circle(frame, (130, 130), 8, (0, 0, 0), -1)
    cv2.circle(frame, (170, 130), 8, (0, 0, 0), -1)

    bbox = (90, 90, 210, 210)
    track_id = 17

    # Frame 1 candidate
    reg_engine.add_candidate(track_id=track_id, frame=frame, bbox=bbox, confidence=0.92, frame_number=1, timestamp=0.1)
    assert reg_engine.is_ready_to_register(track_id) is False

    # Frame 2 candidate (reaches buffer threshold = 2)
    reg_engine.add_candidate(track_id=track_id, frame=frame, bbox=bbox, confidence=0.94, frame_number=2, timestamp=0.2)
    assert reg_engine.is_ready_to_register(track_id) is True

    with db_mgr.get_session() as session:
        face_id, best_crop, emb = reg_engine.register_new_visitor(session, track_id=track_id)
        assert face_id == "VIS-00001"
        assert best_crop is not None
        assert emb is not None
        # VERIFY: track_id != face_id
        assert str(track_id) != face_id
        assert VisitorRepository.count_unique_visitors(session) == 1


# --- TEST 2: Same Face -> Recognition ---
def test_audit_scenario_2_same_face_recognition(setup_audit_env):
    db_mgr, _, vis_mgr, _, store, matcher, _ = setup_audit_env

    # Seed vector
    vec1 = np.random.randn(512).astype(np.float32)
    vec1 /= np.linalg.norm(vec1)

    with db_mgr.get_session() as session:
        face_id = VisitorRepository.generate_next_face_id(session)
        VisitorRepository.create_visitor(session, face_id, current_status="INSIDE")
        VisitorRepository.add_embedding(session, face_id, vec1)
        store.add_embedding(face_id, vec1)

    # Query with same vector + slight noise
    query_vec = vec1 + np.random.randn(512).astype(np.float32) * 0.05
    query_vec /= np.linalg.norm(query_vec)

    match_res = matcher.match(query_vec, store)
    assert match_res.matched is True
    assert match_res.face_id == "VIS-00001"
    assert match_res.similarity >= 0.45

    with db_mgr.get_session() as session:
        # Process recognized track
        vis_mgr.process_recognized_track(
            db_session=session,
            track_id=17,
            face_id=match_res.face_id,
            bbox=(10, 10, 50, 50),
            face_crop=np.zeros((50, 50, 3), dtype=np.uint8),
            confidence=match_res.similarity,
            frame_number=10
        )

        # Unique count must remain 1
        assert VisitorRepository.count_unique_visitors(session) == 1


# --- TEST 3: Same Face with New Track ID -> Re-Identification ---
def test_audit_scenario_3_reidentification(setup_audit_env):
    db_mgr, ev_mgr, vis_mgr, _, store, matcher, _ = setup_audit_env

    crop = np.zeros((60, 60, 3), dtype=np.uint8)
    vec1 = np.random.randn(512).astype(np.float32)
    vec1 /= np.linalg.norm(vec1)

    # Phase A: Initial Visit (Track ID = 10)
    with db_mgr.get_session() as session:
        face_id = VisitorRepository.generate_next_face_id(session)  # VIS-00001
        VisitorRepository.create_visitor(session, face_id, current_status="INSIDE")
        VisitorRepository.add_embedding(session, face_id, vec1)
        store.add_embedding(face_id, vec1)

        vis_mgr.process_recognized_track(
            db_session=session,
            track_id=10,
            face_id=face_id,
            bbox=(10, 10, 50, 50),
            face_crop=crop,
            confidence=0.95,
            frame_number=1
        )
        assert VisitorRepository.count_unique_visitors(session) == 1

    # Phase B: Exit Event (Missing frames > timeout = 3)
    with db_mgr.get_session() as session:
        for f in range(2, 6):
            vis_mgr.update_missing_tracks(session, current_visible_track_ids=set(), frame_number=f)

        vis = VisitorRepository.get_visitor(session, "VIS-00001")
        assert vis.current_status == "OUTSIDE"

    # Phase C: Re-entry under NEW Track ID (Track ID = 99)
    with db_mgr.get_session() as session:
        match_res = matcher.match(vec1, store)
        assert match_res.matched is True
        assert match_res.face_id == "VIS-00001"

        vis_mgr.process_recognized_track(
            db_session=session,
            track_id=99,  # NEW TRACK ID
            face_id=match_res.face_id,  # MATCHED PERSISTENT FACE ID
            bbox=(10, 10, 50, 50),
            face_crop=crop,
            confidence=match_res.similarity,
            frame_number=100
        )

        vis = VisitorRepository.get_visitor(session, "VIS-00001")
        assert vis.current_status == "INSIDE"
        assert vis.total_visits == 2

        # CRITICAL ASSERTIONS:
        # 1. Unique visitor count MUST NOT INCREASE!
        assert VisitorRepository.count_unique_visitors(session) == 1
        # 2. Track ID != Face ID
        assert 99 != int(face_id.replace("VIS-", ""))


# --- TEST 4: Poor Face -> No Premature Registration ---
def test_audit_scenario_4_poor_face_rejection(setup_audit_env):
    db_mgr, _, _, _, _, _, reg_engine = setup_audit_env

    # 1. Tiny crop frame (10x10 px)
    tiny_frame = np.zeros((200, 200, 3), dtype=np.uint8)
    bbox_tiny = (50, 50, 60, 60)  # Width = 10px < min_face_size (30px)

    res1 = reg_engine.add_candidate(track_id=5, frame=tiny_frame, bbox=bbox_tiny, confidence=0.90, frame_number=1, timestamp=0.1)
    assert res1 is False

    # 2. Heavy blurry crop
    blur_frame = np.full((200, 200, 3), 128, dtype=np.uint8)  # Zero sharpness gradient
    bbox_blur = (50, 50, 120, 120)

    res2 = reg_engine.add_candidate(track_id=5, frame=blur_frame, bbox=bbox_blur, confidence=0.90, frame_number=2, timestamp=0.2)
    assert res2 is False

    with db_mgr.get_session() as session:
        # Verify NO visitor registered in DB
        assert VisitorRepository.count_unique_visitors(session) == 0


# --- TEST 5: Similar Faces -> Threshold Behavior ---
def test_audit_scenario_5_threshold_behavior(setup_audit_env):
    _, _, _, _, store, matcher, _ = setup_audit_env

    vA = np.zeros(512, dtype=np.float32)
    vA[0] = 1.0

    vB = np.zeros(512, dtype=np.float32)
    vB[0] = 0.6
    vB[1] = 0.8  # Cosine sim = 0.6 >= threshold 0.45

    vC = np.zeros(512, dtype=np.float32)
    vC[0] = 0.2
    vC[1] = 0.9798  # Cosine sim = 0.2 < threshold 0.45

    store.add_embedding("VIS-00001", vA)

    # Vector A -> Perfect Match
    resA = matcher.match(vA, store)
    assert resA.matched is True
    assert resA.face_id == "VIS-00001"

    # Vector B -> Above Threshold Match
    resB = matcher.match(vB, store)
    assert resB.matched is True
    assert resB.face_id == "VIS-00001"

    # Vector C -> Below Threshold Unmatched
    resC = matcher.match(vC, store)
    assert resC.matched is False


# --- TEST 6: Recognition Noise -> Temporal Stabilization ---
def test_audit_scenario_6_temporal_stabilization():
    history = TemporalPredictionHistory(history_size=5)

    # Sequence with 1 transient noisy UNKNOWN frame
    preds = ["VIS-00001", "VIS-00001", None, "VIS-00001", "VIS-00001"]
    for p in preds:
        history.add_prediction(track_id=12, predicted_face_id=p)

    smoothed = history.get_smoothed_face_id(track_id=12)
    assert smoothed == "VIS-00001"


# --- TEST 7: Application Restart -> Identity Persistence ---
def test_audit_scenario_7_restart_persistence(tmp_path):
    db_path = tmp_path / "persistent_visitors.db"
    db_url = f"sqlite:///{db_path}"

    vec = np.random.randn(512).astype(np.float32)
    vec /= np.linalg.norm(vec)

    # Session 1: Register visitor and store embedding in DB
    db1 = DatabaseManager(db_url)
    db1.init_db()
    with db1.get_session() as session:
        fid = VisitorRepository.generate_next_face_id(session)
        VisitorRepository.create_visitor(session, fid)
        VisitorRepository.add_embedding(session, fid, vec)

    # Session 2: Simulated Restart (Fresh memory store reloaded from DB)
    db2 = DatabaseManager(db_url)
    fresh_store = EmbeddingStore()
    matcher = SimilarityMatcher(similarity_threshold=0.45)

    with db2.get_session() as session:
        records = VisitorRepository.get_all_embeddings(session)
        fresh_store.load_from_db(records)

    # Query using same face vector
    res = matcher.match(vec, fresh_store)
    assert res.matched is True
    assert res.face_id == "VIS-00001"
    assert pytest.approx(res.similarity) == 1.0
