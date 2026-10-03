import pytest
import numpy as np
import cv2
from app.database.database import DatabaseManager
from app.recognition.insightface_engine import InsightFaceEngine
from app.recognition.matcher import EmbeddingStore
from app.registration.auto_registration import AutoRegistrationEngine
from app.utils.image_utils import evaluate_face_quality, calculate_sharpness


@pytest.fixture
def setup_reg():
    db_mgr = DatabaseManager("sqlite:///:memory:")
    db_mgr.init_db()
    rec = InsightFaceEngine(model_name="buffalo_sc")
    store = EmbeddingStore()
    engine = AutoRegistrationEngine(
        recognition_engine=rec,
        embedding_store=store,
        min_face_size=20,
        min_sharpness=5.0,
        buffer_frames=2
    )
    return db_mgr, engine, store


def test_quality_eval():
    # Tiny crop
    small_crop = np.zeros((10, 10, 3), dtype=np.uint8)
    valid, reason = evaluate_face_quality(small_crop, min_size=30)
    assert valid is False
    assert "TOO_SMALL" in reason

    # Sharp synthetic crop
    sharp_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(sharp_crop, (20, 20), (80, 80), (255, 255, 255), -1)
    valid_sharp, _ = evaluate_face_quality(sharp_crop, min_size=30, min_sharpness=5.0)
    assert valid_sharp is True


def test_auto_registration_flow(setup_reg):
    db_mgr, engine, store = setup_reg

    frame = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.circle(frame, (200, 200), 50, (255, 255, 255), -1)
    bbox = (150, 150, 250, 250)

    # Frame 1
    engine.add_candidate(track_id=1, frame=frame, bbox=bbox, confidence=0.90, frame_number=1, timestamp=1.0)
    assert engine.is_ready_to_register(1) is False

    # Frame 2
    engine.add_candidate(track_id=1, frame=frame, bbox=bbox, confidence=0.95, frame_number=2, timestamp=1.1)
    assert engine.is_ready_to_register(1) is True

    with db_mgr.get_session() as session:
        face_id, crop, emb = engine.register_new_visitor(session, track_id=1)
        assert face_id == "VIS-00001"
        assert crop is not None
        assert emb is not None
        assert store.is_empty() is False
