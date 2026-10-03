"""Mathematical helper utilities for similarity metrics."""

import numpy as np


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two 1D floating point vectors."""
    if vec1 is None or vec2 is None:
        return 0.0

    dot = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    sim = float(dot / (norm1 * norm2))
    if np.isnan(sim) or np.isinf(sim):
        return 0.0

    return max(-1.0, min(1.0, sim))
