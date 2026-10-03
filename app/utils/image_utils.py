"""Image crop, quality analysis, and atomic saving utilities."""

import os
from typing import Optional, Tuple
import cv2
import numpy as np


def crop_face(frame: np.ndarray, bbox: Tuple[int, int, int, int], margin: float = 0.1) -> Optional[np.ndarray]:
    """Extract face crop from image frame with optional margin padding."""
    if frame is None or frame.size == 0:
        return None

    h, w = frame.shape[:2]
    x1, y1, x2, y2 = bbox

    bw = x2 - x1
    bh = y2 - y1

    if bw <= 0 or bh <= 0:
        return None

    pad_w = int(bw * margin)
    pad_h = int(bh * margin)

    cx1 = max(0, x1 - pad_w)
    cy1 = max(0, y1 - pad_h)
    cx2 = min(w, x2 + pad_w)
    cy2 = min(h, y2 + pad_h)

    if cx2 <= cx1 or cy2 <= cy1 or (cx2 - cx1) < 10 or (cy2 - cy1) < 10:
        return None

    crop = frame[cy1:cy2, cx1:cx2]
    if crop.size == 0:
        return None

    return crop.copy()


def calculate_sharpness(crop: np.ndarray) -> float:
    """Calculate image sharpness score using Laplacian variance."""
    if crop is None or crop.size == 0:
        return 0.0
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def evaluate_face_quality(
    crop: np.ndarray,
    min_size: int = 50,
    min_sharpness: float = 10.0
) -> Tuple[bool, str]:
    """Validate if face crop satisfies minimum dimensions and sharpness thresholds."""
    if crop is None or crop.size == 0:
        return False, "INVALID_CROP"

    ch, cw = crop.shape[:2]
    if cw < min_size or ch < min_size:
        return False, f"TOO_SMALL ({cw}x{ch} < {min_size})"

    sharpness = calculate_sharpness(crop)
    if sharpness < min_sharpness:
        return False, f"BLURRY (sharpness {sharpness:.1f} < {min_sharpness})"

    return True, "QUALITY_PASS"


def save_image_atomically(image: np.ndarray, target_path: str) -> bool:
    """Save image to disk using temp file write and atomic rename for reliability."""
    if image is None or image.size == 0:
        return False

    target_path = str(target_path)
    dir_name = os.path.dirname(target_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    temp_path = target_path + ".tmp"
    try:
        ext = os.path.splitext(target_path)[1] or ".jpg"
        ret, buf = cv2.imencode(ext, image)
        if not ret:
            return False

        with open(temp_path, "wb") as f:
            f.write(buf)

        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

        # Atomic rename
        os.replace(temp_path, target_path)
        return True
    except Exception as e:
        print(f"[ImageUtils] Atomic save failed for {target_path}: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False
