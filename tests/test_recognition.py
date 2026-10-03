import pytest
import numpy as np
from app.recognition.insightface_engine import InsightFaceEngine


def test_insightface_extraction():
    engine = InsightFaceEngine()
    crop = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)

    emb = engine.extract_embedding(crop)
    assert emb is not None
    assert isinstance(emb, np.ndarray)
    assert len(emb) in [512, 256, 128] or len(emb) > 0
    # Verify L2 normalization
    norm = np.linalg.norm(emb)
    assert pytest.approx(norm, abs=1e-3) == 1.0
