"""InsightFace / ArcFace recognition engine generating normalized 512-d embeddings."""

import os
from typing import Optional, Tuple
import cv2
import numpy as np
from app.events.event_logger import EventLogger


class InsightFaceEngine:
    """InsightFace ArcFace feature extraction engine."""

    def __init__(
        self,
        model_name: str = "buffalo_sc",
        event_logger: Optional[EventLogger] = None
    ):
        self.model_name = model_name
        self.logger = event_logger
        self.app = None
        self.use_insightface = False

        self._init_model()

    def _init_model(self) -> None:
        """Initialize InsightFace FaceAnalysis engine ONCE."""
        try:
            import insightface
            from insightface.app import FaceAnalysis

            self.app = FaceAnalysis(name=self.model_name, providers=['CPUExecutionProvider'])
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            self.use_insightface = True
            print(f"[Recognition] Initialized InsightFace model ({self.model_name}) successfully.")
        except Exception as e:
            print(f"[Recognition] Warning: InsightFace initialization fallback to synthetic feature extractor: {e}")
            self.use_insightface = False

    def extract_embedding(self, face_crop: np.ndarray) -> Optional[np.ndarray]:
        """Extract L2-normalized 512-dimensional facial embedding vector from crop."""
        if face_crop is None or face_crop.size == 0 or face_crop.shape[0] < 10 or face_crop.shape[1] < 10:
            return None

        # Resize to standard size (112, 112) for face recognition
        crop_resized = cv2.resize(face_crop, (112, 112))

        if self.use_insightface and self.app is not None:
            try:
                faces = self.app.get(crop_resized)
                if faces and len(faces) > 0 and hasattr(faces[0], 'embedding') and faces[0].embedding is not None:
                    emb = faces[0].embedding
                    norm = np.linalg.norm(emb)
                    if norm > 0:
                        emb = emb / norm
                    if self.logger:
                        self.logger.log_event("EMBEDDING_GENERATED", metadata={"dim": len(emb)})
                    return emb.astype(np.float32)
            except Exception as e:
                print(f"[Recognition] InsightFace get embedding error: {e}")

        # Fallback feature extractor: Normalized multi-channel spatial HOG/color histogram (512-d)
        try:
            gray = cv2.cvtColor(crop_resized, cv2.COLOR_BGR2GRAY)
            # Resize to 16x16 to get 256 pixel values + HSV histograms 256 = 512 features
            small = cv2.resize(gray, (16, 16)).flatten().astype(np.float32)
            hsv = cv2.cvtColor(crop_resized, cv2.COLOR_BGR2HSV)
            hist_h = cv2.calcHist([hsv], [0], None, [128], [0, 180]).flatten()
            hist_s = cv2.calcHist([hsv], [1], None, [128], [0, 256]).flatten()
            
            feat = np.concatenate([small, hist_h, hist_s])
            norm = np.linalg.norm(feat)
            if norm > 0:
                feat = feat / norm
            if self.logger:
                self.logger.log_event("EMBEDDING_GENERATED", metadata={"dim": len(feat), "fallback": True})
            return feat.astype(np.float32)
        except Exception as e:
            print(f"[Recognition] Fallback embedding error: {e}")
            return None
