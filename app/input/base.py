"""Abstract Base Class for Video Sources."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
import numpy as np


class VideoSource(ABC):
    """Abstract interface for video stream readers (file, RTSP, camera)."""

    @abstractmethod
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], int, float]:
        """Read the next video frame.

        Returns:
            Tuple of (success: bool, frame: Optional[np.ndarray], frame_number: int, timestamp_sec: float)
        """
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        """Check if video source stream is currently active."""
        pass

    @abstractmethod
    def get_fps(self) -> float:
        """Get source frame rate."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Release underlying camera or file handle resources."""
        pass
