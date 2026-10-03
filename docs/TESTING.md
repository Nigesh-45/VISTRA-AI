# Testing Strategy & Automated Test Suite - VISITR-AI

VISITR-AI includes an automated test suite implemented using `pytest`.

## 1. Running Automated Tests

To execute the complete test suite:

```bash
python -m pytest tests/ -v
```

---

## 2. Test Suite Module Breakdown

| Test File | Target Component | Verifies |
| :--- | :--- | :--- |
| `tests/test_config.py` | Configuration Loader | Schema validation, default fallback, custom JSON parsing. |
| `tests/test_video_source.py` | Video Stream Reader | Frame reading, timestamp calculation, resource cleanup. |
| `tests/test_detection.py` | YOLO Face Detector | Model instantiation, bounding box structure, confidence thresholding. |
| `tests/test_tracking.py` | ByteTrack Tracker | Track ID assignment, IoU association, track lifecycle. |
| `tests/test_recognition.py` | InsightFace Engine | 512-d feature extraction, L2 normalization vector checks. |
| `tests/test_matching.py` | Cosine Similarity Matcher | Cosine metric math, gallery store max limits, threshold matching. |
| `tests/test_registration.py` | Auto-Registration Engine | Face quality filter (sharpness, size), candidate buffer selection. |
| `tests/test_reidentification.py` | Identity & Counting | **Critical Test**: Re-entry under new track ID preserves original `face_id` and unique count = 1. |
| `tests/test_state_machine.py` | Visitor State Machine | Temporal prediction history smoothing, state transitions. |
| `tests/test_events.py` | Event Manager | Atomic image saving, file existence checks, DB event creation. |
| `tests/test_database.py` | SQLite Repository | Foreign keys, session transactions, ORM CRUD operations. |
| `tests/test_counting.py` | Unique Visitor Analytics | `count_unique_visitors()` integrity across multiple visitors. |

---

## 3. Empirical Test Results Summary

```
======================= 18 passed, 1 warning in 14.49s ========================
```

All 18 tests pass with 100% success rate.
