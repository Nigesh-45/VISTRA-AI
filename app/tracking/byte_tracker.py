"""ByteTrack Multi-Object Tracker integration for temporary track_id assignment."""

from dataclasses import dataclass, field
import numpy as np
from typing import Dict, List, Optional, Tuple
from app.detection.yolo_detector import DetectionResult
from app.events.event_logger import EventLogger


@dataclass
class TrackedTarget:
    """Representation of an actively tracked face target."""
    track_id: int
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    frame_number: int
    timestamp: float
    age: int = 1
    hits: int = 1
    time_since_update: int = 0


def calculate_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    """Calculate Intersection over Union (IoU) between two bounding boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    iou = interArea / float(boxAArea + boxBArea - interArea + 1e-6)
    return iou


class ByteTrackerWrapper:
    """Wrapper around ByteTrack multi-object tracker with fallback IoU association."""

    def __init__(
        self,
        max_age: int = 30,
        track_thresh: float = 0.50,
        event_logger: Optional[EventLogger] = None
    ):
        self.max_age = max_age
        self.track_thresh = track_thresh
        self.logger = event_logger
        self.next_track_id = 1
        self.active_tracks: Dict[int, TrackedTarget] = {}
        self.supervision_tracker = None

        self._init_supervision()

    def _init_supervision(self) -> None:
        """Attempt initializing Supervision ByteTrack."""
        try:
            import supervision as sv
            self.supervision_tracker = sv.ByteTrack(
                track_activation_threshold=self.track_thresh,
                lost_track_buffer=self.max_age
            )
            print("[Tracker] Initialized supervision.ByteTrack successfully.")
        except Exception as e:
            print(f"[Tracker] Supervision ByteTrack fallback to robust internal IoU tracker: {e}")

    def update(
        self,
        detections: List[DetectionResult],
        frame_number: int,
        timestamp: float
    ) -> List[TrackedTarget]:
        """Update tracker with frame detections and return active tracked targets."""

        # Try supervision ByteTrack if available
        if self.supervision_tracker is not None and detections:
            try:
                import supervision as sv
                xyxy = np.array([d.bbox for d in detections], dtype=np.float32)
                confidence = np.array([d.confidence for d in detections], dtype=np.float32)
                class_id = np.zeros(len(detections), dtype=int)

                sv_dets = sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_id)
                tracked_sv = self.supervision_tracker.update_with_detections(sv_dets)

                output_tracks: List[TrackedTarget] = []
                if tracked_sv.tracker_id is not None:
                    for i, t_id in enumerate(tracked_sv.tracker_id):
                        b = tracked_sv.xyxy[i].astype(int)
                        conf = float(tracked_sv.confidence[i]) if tracked_sv.confidence is not None else 0.90
                        x1, y1, x2, y2 = int(b[0]), int(b[1]), int(b[2]), int(b[3])
                        
                        target = TrackedTarget(
                            track_id=int(t_id),
                            bbox=(x1, y1, x2, y2),
                            confidence=conf,
                            frame_number=frame_number,
                            timestamp=timestamp
                        )
                        output_tracks.append(target)
                        if self.logger:
                            self.logger.log_event("TRACKING", track_id=int(t_id), confidence=conf, metadata={"bbox": [x1, y1, x2, y2]})
                return output_tracks
            except Exception as e:
                print(f"[Tracker] Supervision update error ({e}). Switching to IoU tracking.")

        # Robust Fallback IoU Tracker Implementation
        for t in self.active_tracks.values():
            t.time_since_update += 1

        matched_track_ids = set()
        matched_det_indices = set()

        if detections and self.active_tracks:
            # Match existing tracks with detections via IoU
            for det_idx, det in enumerate(detections):
                best_iou = 0.0
                best_tid = None
                for tid, target in self.active_tracks.items():
                    if tid in matched_track_ids:
                        continue
                    iou = calculate_iou(det.bbox, target.bbox)
                    if iou > best_iou and iou > 0.30:
                        best_iou = iou
                        best_tid = tid

                if best_tid is not None:
                    target = self.active_tracks[best_tid]
                    target.bbox = det.bbox
                    target.confidence = det.confidence
                    target.frame_number = frame_number
                    target.timestamp = timestamp
                    target.hits += 1
                    target.age += 1
                    target.time_since_update = 0

                    matched_track_ids.add(best_tid)
                    matched_det_indices.add(det_idx)

        # Create new tracks for unmatched detections
        for det_idx, det in enumerate(detections):
            if det_idx not in matched_det_indices:
                tid = self.next_track_id
                self.next_track_id += 1
                new_target = TrackedTarget(
                    track_id=tid,
                    bbox=det.bbox,
                    confidence=det.confidence,
                    frame_number=frame_number,
                    timestamp=timestamp
                )
                self.active_tracks[tid] = new_target
                matched_track_ids.add(tid)

        # Prune dead tracks exceeding max_age
        dead_tids = [tid for tid, t in self.active_tracks.items() if t.time_since_update > self.max_age]
        for tid in dead_tids:
            del self.active_tracks[tid]

        # Active tracks output
        current_tracks = [t for t in self.active_tracks.values() if t.time_since_update == 0]
        if self.logger:
            for t in current_tracks:
                self.logger.log_event("TRACKING", track_id=t.track_id, confidence=t.confidence, metadata={"bbox": list(t.bbox)})

        return current_tracks
