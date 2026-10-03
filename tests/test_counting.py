import pytest
from app.database.database import DatabaseManager
from app.database.repository import VisitorRepository


def test_unique_visitor_counting():
    db = DatabaseManager("sqlite:///:memory:")
    db.init_db()

    with db.get_session() as session:
        assert VisitorRepository.count_unique_visitors(session) == 0

        v1 = VisitorRepository.generate_next_face_id(session)
        VisitorRepository.create_visitor(session, v1)
        assert VisitorRepository.count_unique_visitors(session) == 1

        v2 = VisitorRepository.generate_next_face_id(session)
        VisitorRepository.create_visitor(session, v2)
        assert VisitorRepository.count_unique_visitors(session) == 2

        # Increment visits for v1
        VisitorRepository.increment_visits(session, v1)
        assert VisitorRepository.count_unique_visitors(session) == 2
