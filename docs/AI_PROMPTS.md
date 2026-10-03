# AI Prompts & Development Directives - VISITR-AI

This document preserves the actual prompts, engineering directives, and system instructions utilized during the AI-assisted development of **VISITR-AI**.

---

## 1. Planning Prompt
```text
You are the lead architect for building my final submission for the Katomaran Hackathon.
PROJECT: VISITR-AI (Intelligent Face Tracking, Auto-Registration & Unique Visitor Analytics)
MISSION: Build a technically excellent, production-style, modular, reliable and interview-defensible computer vision application that satisfies EVERY requirement in the Katomaran problem statement.
Analyze requirements, identify edge cases (identity fragmentation, duplicate entry events, occlusion, stream drops), and outline a modular architecture.
```

## 2. Architecture Prompt
```text
Design a Decoupled Identity Architecture for VISITR-AI.
Strictly separate temporary spatial tracking (track_id assigned by ByteTrack) from persistent facial identity (face_id format VIS-XXXXX assigned by ArcFace embedding matching).
Ensure that when a target exits and re-enters under a new track_id, ArcFace cosine matching resolves them back to their original face_id, recording a return visit without inflating unique_visitors count.
```

## 3. Implementation Prompt
```text
Create clean, modular Python 3.11 code under the app/ package.
Follow PEP 8 guidelines, use explicit type hints, write comprehensive docstrings, and eliminate circular dependencies.
Abstract key components: input sources, detection, tracking, recognition, registration, state machine, event management, database ORM, and pipeline orchestration.
```

## 4. Detection Prompt
```text
Implement app/detection/yolo_detector.py using Ultralytics YOLOv8 (yolov8n.pt).
Include configurable confidence threshold, IoU threshold, and frame skipping (skip_frames = 5).
Frame skipping should run deep learning detection once every 6 frames to optimize CPU latency while relying on spatial tracking between detection cycles.
```

## 5. Tracking Prompt
```text
Implement app/tracking/byte_tracker.py using Supervision ByteTrack integration.
Maintain bounding box spatial continuity across video frames.
Assign temporary integer track_id values and maintain target tracks across brief occlusions up to max_age = 30 frames.
```

## 6. Recognition Prompt
```text
Implement app/recognition/insightface_engine.py and app/recognition/matcher.py.
CRITICAL DIRECTIVE: DO NOT use the Python face_recognition library.
Use InsightFace (buffalo_sc model) to extract L2-normalized 512-dimensional facial feature vectors.
Implement Cosine Similarity matching against database embeddings gallery using threshold 0.45:
similarity = (u . v) / (||u|| ||v||)
```

## 7. Auto-registration Prompt
```text
Implement app/registration/auto_registration.py for unregistered unknown faces.
Buffer candidate face crops for new tracks over 3 detection frames.
Evaluate crop quality using composite score: confidence * (sharpness + 1) * sqrt(area), where sharpness is Laplacian variance.
Select the candidate crop with the highest quality score for persistent embedding generation and assign persistent ID VIS-XXXXX.
```

## 8. Re-identification Prompt
```text
Implement visitor re-identification in app/visitors/visitor_manager.py.
When a returning visitor is matched against the embedding gallery with cosine similarity >= 0.45:
1. Retain existing persistent face_id (e.g. VIS-00001).
2. Increment total_visits counter.
3. Update last_seen timestamp.
4. Ensure count_unique_visitors() query remains unchanged.
```

## 9. Entry/Exit Logic Prompt
```text
Implement app/visitors/visitor_state.py and app/events/event_manager.py.
Enforce a strict State Machine: OUTSIDE -> INSIDE -> OUTSIDE.
Trigger exactly one ENTRY event upon initial detection/recognition of an OUTSIDE visitor.
Trigger exactly one EXIT event when an INSIDE visitor is inactive for > exit_timeout_frames (30 frames).
State machine guards must eliminate duplicate entry or exit events for active visitors.
```

## 10. Database Prompt
```text
Implement app/database/ models.py, database.py, and repository.py using SQLAlchemy ORM and SQLite.
Define 4 relational tables:
- visitors (face_id PK, first_seen, last_seen, total_visits, current_status)
- embeddings (id PK, face_id FK, embedding_data BLOB)
- events (id PK, face_id FK, track_id, event_type, timestamp, image_path, confidence, frame_number)
- tracks (id PK, face_id FK, track_id, started_at, ended_at)
Implement atomic persistence (temp image write -> rename -> DB transaction commit).
```

## 11. Logging Prompt
```text
Implement app/events/event_logger.py for structured event logging.
Format log entries containing timestamp, event name, face_id, track_id, confidence, frame index, and image paths.
Write central log output to logs/events.log. Ensure thread-safe, non-blocking file writing.
```

## 12. Testing Prompt
```text
Create automated unit and integration tests in tests/ using pytest.
Cover config validation, detection, tracking, matching, auto-registration, re-identification, state machine state transitions, database CRUD, and adversarial cases (blurry crops, track loss, immediate re-entry).
Achieve 100% test pass rate across all test modules.
```

## 13. Deployment Prompt
```text
Prepare production deployment configuration:
Create Dockerfile, docker-compose.yml, .dockerignore, and .env.example.
Ensure local model caching (~/.insightface and ./yolov8n.pt), volume persistence for database/ and logs/, non-root container execution, and health check script (scripts/health_check.py).
```

## 14. Final Audit Prompt
```text
Perform a complete final audit against all Katomaran Hackathon evaluation requirements.
Audit repository structure, verify doc completeness (COMPLIANCE_MATRIX, AI_PLANNING, FEATURES, ARCHITECTURE, COMPUTE_ANALYSIS, DEMO_SCRIPT, AI_PROMPTS, INTERVIEW_GUIDE, DEPLOYMENT, FINAL_SUBMISSION_CHECKLIST), clean .gitignore, export empirical sample outputs to sample_output/, verify pytest pass rate, and ensure README contains exact Katomaran footer statement.
```
