import pytest
import numpy as np
import cv2
from app.detection.yolo_detector import YOLODetector, DetectionResult


def test_yolo_detector_instantiation():
    detector = YOLODetector(confidence=0.50, skip_frames=5)
    assert detector.confidence == 0.50
    assert detector.skip_frames == 5

    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.circle(frame, (100, 100), 40, (255, 255, 255), -1)

    dets = detector.detect(frame, frame_number=1, timestamp=0.1)
    assert isinstance(dets, list)
