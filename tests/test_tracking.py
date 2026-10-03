import pytest
from app.detection.yolo_detector import DetectionResult
from app.tracking.byte_tracker import ByteTrackerWrapper, calculate_iou


def test_iou_calculation():
    boxA = (10, 10, 50, 50)
    boxB = (10, 10, 50, 50)
    boxC = (100, 100, 150, 150)

    assert pytest.approx(calculate_iou(boxA, boxB)) == 1.0
    assert pytest.approx(calculate_iou(boxA, boxC)) == 0.0


def test_byte_tracker_update():
    tracker = ByteTrackerWrapper(max_age=10)

    det1 = DetectionResult(bbox=(10, 10, 60, 60), confidence=0.90, frame_number=1, timestamp=0.1)
    tracks1 = tracker.update([det1], frame_number=1, timestamp=0.1)

    assert len(tracks1) == 1
    tid = tracks1[0].track_id

    # Frame 2: slightly moved box
    det2 = DetectionResult(bbox=(12, 12, 62, 62), confidence=0.91, frame_number=2, timestamp=0.2)
    tracks2 = tracker.update([det2], frame_number=2, timestamp=0.2)

    assert len(tracks2) == 1
    assert tracks2[0].track_id == tid  # Track ID continuity preserved
