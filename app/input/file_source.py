"""VideoSource implementation for static video files (MP4, AVI, etc.)."""

import os
import time
from typing import Optional, Tuple
import cv2
import numpy as np
from app.input.base import VideoSource


class FileVideoSource(VideoSource):
    """Video source for pre-recorded video files."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found at path: {file_path}")

        self.cap = cv2.VideoCapture(file_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Unable to open video file: {file_path}")

        self.frame_number = 0
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        self.start_time = time.time()

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], int, float]:
        if not self.cap.isOpened():
            return False, None, self.frame_number, time.time()

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return False, None, self.frame_number, time.time()

        self.frame_number += 1
        timestamp = self.frame_number / self.fps
        return True, frame, self.frame_number, timestamp

    def is_opened(self) -> bool:
        return self.cap.isOpened()

    def get_fps(self) -> float:
        return self.fps

    def release(self) -> None:
        if self.cap and self.cap.isOpened():
            self.cap.release()
