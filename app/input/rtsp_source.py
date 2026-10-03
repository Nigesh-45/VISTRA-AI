"""VideoSource implementation for live RTSP IP camera streams with auto-reconnect."""

import threading
import time
from typing import Optional, Tuple
import cv2
import numpy as np
from app.input.base import VideoSource
from app.events.event_logger import EventLogger


class RTSPVideoSource(VideoSource):
    """Threaded RTSP camera client supporting continuous auto-reconnection."""

    def __init__(
        self,
        rtsp_url: str,
        event_logger: Optional[EventLogger] = None,
        reconnect_delay: float = 3.0,
        max_retries: int = 10
    ):
        self.rtsp_url = rtsp_url
        self.logger = event_logger
        self.reconnect_delay = reconnect_delay
        self.max_retries = max_retries

        self.cap: Optional[cv2.VideoCapture] = None
        self.running = True
        self.connected = False

        self.latest_frame: Optional[np.ndarray] = None
        self.frame_number = 0
        self.lock = threading.Lock()
        self.fps = 30.0

        self.thread = threading.Thread(target=self._read_worker, daemon=True)
        self._connect()
        self.thread.start()

    def _connect(self) -> bool:
        """Attempt connection to RTSP stream."""
        retries = 0
        while self.running and retries < self.max_retries:
            self.cap = cv2.VideoCapture(self.rtsp_url)
            if self.cap.isOpened():
                self.connected = True
                fps_val = self.cap.get(cv2.CAP_PROP_FPS)
                if fps_val and fps_val > 0:
                    self.fps = fps_val
                if self.logger:
                    self.logger.log_event("RTSP_RECONNECTED", metadata={"rtsp_url": self.rtsp_url})
                return True

            retries += 1
            if self.logger:
                self.logger.log_event(
                    "RTSP_DISCONNECTED",
                    level="WARNING",
                    metadata={"rtsp_url": self.rtsp_url, "attempt": retries}
                )
            # Sleep in 0.1s slices to allow instant shutdown response
            stop_time = time.time() + self.reconnect_delay
            while self.running and time.time() < stop_time:
                time.sleep(0.1)

        self.connected = False
        return False

    def _read_worker(self) -> None:
        """Background thread worker fetching RTSP frames continuously."""
        while self.running:
            if not self.connected or self.cap is None or not self.cap.isOpened():
                if not self._connect():
                    time.sleep(self.reconnect_delay)
                    continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.connected = False
                if self.logger:
                    self.logger.log_event("RTSP_DISCONNECTED", level="WARNING", metadata={"rtsp_url": self.rtsp_url})
                if self.cap:
                    self.cap.release()
                time.sleep(self.reconnect_delay)
                continue

            with self.lock:
                self.latest_frame = frame.copy()
                self.frame_number += 1

            time.sleep(0.005)

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], int, float]:
        with self.lock:
            if self.latest_frame is None:
                return False, None, self.frame_number, time.time()
            frame_copy = self.latest_frame.copy()
            fn = self.frame_number
            ts = time.time()
        return True, frame_copy, fn, ts

    def is_opened(self) -> bool:
        return self.connected

    def get_fps(self) -> float:
        return self.fps

    def release(self) -> None:
        self.running = False
        self.connected = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
