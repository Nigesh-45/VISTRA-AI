import pytest
import numpy as np
from app.recognition.matcher import SimilarityMatcher, EmbeddingStore
from app.utils.similarity import cosine_similarity


def test_cosine_similarity():
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    assert pytest.approx(cosine_similarity(v1, v2)) == 1.0
    assert pytest.approx(cosine_similarity(v1, v3)) == 0.0


def test_matcher_matching():
    store = EmbeddingStore(max_embeddings_per_visitor=3)
    matcher = SimilarityMatcher(similarity_threshold=0.50)

    # Visitor A embedding
    vA = np.random.randn(512).astype(np.float32)
    vA /= np.linalg.norm(vA)
    store.add_embedding("VIS-00001", vA)

    # Query with identical vector
    res = matcher.match(vA, store)
    assert res.matched is True
    assert res.face_id == "VIS-00001"
    assert pytest.approx(res.similarity) == 1.0

    # Query with orthogonal vector
    vB = np.random.randn(512).astype(np.float32)
    vB /= np.linalg.norm(vB)
    # Ensure orthogonality for testing
    vB = vB - np.dot(vB, vA) * vA
    vB /= np.linalg.norm(vB)

    res_unmatched = matcher.match(vB, store)
    assert res_unmatched.matched is False
