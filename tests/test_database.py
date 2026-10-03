import pytest
import numpy as np
from app.database.database import DatabaseManager
from app.database.repository import VisitorRepository


@pytest.fixture
def db():
    db_mgr = DatabaseManager("sqlite:///:memory:")
    db_mgr.init_db()
    return db_mgr


def test_visitor_crud(db):
    with db.get_session() as session:
        face_id1 = VisitorRepository.generate_next_face_id(session)
        assert face_id1 == "VIS-00001"

        vis = VisitorRepository.create_visitor(session, face_id1, current_status="INSIDE")
        assert vis.face_id == "VIS-00001"
        assert vis.total_visits == 1
        assert vis.current_status == "INSIDE"

        face_id2 = VisitorRepository.generate_next_face_id(session)
        assert face_id2 == "VIS-00002"

        fetched = VisitorRepository.get_visitor(session, "VIS-00001")
        assert fetched is not None
        assert fetched.face_id == "VIS-00001"


def test_embedding_persistence(db):
    with db.get_session() as session:
        face_id = VisitorRepository.generate_next_face_id(session)
        VisitorRepository.create_visitor(session, face_id)

        vec = np.random.randn(512).astype(np.float32)
        vec /= np.linalg.norm(vec)

        VisitorRepository.add_embedding(session, face_id, vec)

        all_embs = VisitorRepository.get_all_embeddings(session)
        assert len(all_embs) == 1
        fid, ret_vec = all_embs[0]
        assert fid == face_id
        assert np.allclose(vec, ret_vec, atol=1e-4)


def test_event_logging_db(db):
    with db.get_session() as session:
        face_id = VisitorRepository.generate_next_face_id(session)
        VisitorRepository.create_visitor(session, face_id)

        event = VisitorRepository.add_event(
            session=session,
            face_id=face_id,
            track_id=10,
            event_type="ENTRY",
            image_path="logs/entries/test.jpg",
            confidence=0.92,
            frame_number=100
        )
        assert event.id is not None
        assert event.event_type == "ENTRY"

        events = VisitorRepository.get_events(session)
        assert len(events) == 1
        assert events[0].face_id == face_id
