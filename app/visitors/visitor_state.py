"""Visitor state machine and temporal prediction smoothing to prevent identity flickering."""

from collections import Counter
from enum import Enum
from typing import Dict, List, Optional


class VisitorStatus(str, Enum):
    OUTSIDE = "OUTSIDE"
    PROCESSING = "PROCESSING"
    INSIDE = "INSIDE"


class TemporalPredictionHistory:
    """Bounded history of recent face_id predictions for a track to smooth identity flickering."""

    def __init__(self, history_size: int = 5):
        self.history_size = history_size
        self.history: Dict[int, List[Optional[str]]] = {}

    def add_prediction(self, track_id: int, predicted_face_id: Optional[str]) -> None:
        if track_id not in self.history:
            self.history[track_id] = []
        self.history[track_id].append(predicted_face_id)
        if len(self.history[track_id]) > self.history_size:
            self.history[track_id].pop(0)

    def get_smoothed_face_id(self, track_id: int) -> Optional[str]:
        preds = self.history.get(track_id, [])
        if not preds:
            return None

        # Filter non-None predictions
        valid = [p for p in preds if p is not None]
        if not valid:
            return None

        # Return majority prediction
        most_common = Counter(valid).most_common(1)
        return most_common[0][0]

    def clear_track(self, track_id: int) -> None:
        if track_id in self.history:
            del self.history[track_id]
