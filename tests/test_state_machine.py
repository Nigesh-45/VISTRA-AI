import pytest
from app.visitors.visitor_state import TemporalPredictionHistory, VisitorStatus


def test_temporal_smoothing():
    history = TemporalPredictionHistory(history_size=5)

    history.add_prediction(track_id=1, predicted_face_id="VIS-00001")
    history.add_prediction(track_id=1, predicted_face_id="VIS-00001")
    history.add_prediction(track_id=1, predicted_face_id=None)  # Noisy frame
    history.add_prediction(track_id=1, predicted_face_id="VIS-00001")

    smoothed = history.get_smoothed_face_id(track_id=1)
    assert smoothed == "VIS-00001"
