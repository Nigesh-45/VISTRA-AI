import os
import cv2
import numpy as np
import pytest
from app.input.file_source import FileVideoSource


def test_file_video_source(tmp_path):
    video_path = tmp_path / "test.mp4"

    # Create synthetic test mp4
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(video_path), fourcc, 10.0, (100, 100))
    for _ in range(5):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        out.write(frame)
    out.release()

    src = FileVideoSource(str(video_path))
    assert src.is_opened() is True
    assert src.get_fps() == 10.0

    ret, frame, fn, ts = src.read_frame()
    assert ret is True
    assert frame is not None
    assert fn == 1

    src.release()
