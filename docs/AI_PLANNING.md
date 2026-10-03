# AI Application Building Workflow & Planning - VISITR-AI

This document details the end-to-end AI application building workflow, architectural planning, and engineering design rationale utilized during the development of **VISITR-AI**.

---

## 1. Problem Understanding
Video analytics applications in visitor management frequently fail due to **identity fragmentation**. Traditional object trackers assign temporary track IDs that reset whenever a person is temporarily occluded, turns away, or exits and re-enters. This leads to **inflated unique visitor counts**, **duplicate entry/exit logs**, and **corrupted analytics**. The objective was to build a computer vision pipeline that decouples temporary spatial tracking from persistent facial identity.

## 2. Requirement Analysis
Key functional and technical constraints extracted from the Katomaran Hackathon specification:
- Dual video stream support (static MP4 and live RTSP with auto-reconnection).
- SOTA face detection (YOLOv8) and 512-d ArcFace recognition (InsightFace).
- **Prohibited Library**: Explicit prohibition of the standard `face_recognition` library.
- Automatic registration of unknown faces using composite quality evaluation.
- Exactly-once `ENTRY` and `EXIT` events per visit cycle using state machine guards.
- Database persistence via SQLite + SQLAlchemy ORM.
- Structured file logging to `logs/events.log`.
- High efficiency with configurable frame skipping (`skip_frames`).

## 3. Architecture Planning
The system was designed around a **Decoupled Identity Architecture**:
- **Spatial Tracker**: ByteTrack handles continuous frame-to-frame bounding box tracking (`track_id`).
- **Facial Identity**: InsightFace ArcFace computes 512-d feature embeddings (`face_id` format `VIS-XXXXX`).
- When a person exits and re-enters under a new `track_id`, ArcFace embedding matching resolves the target back to their existing `face_id`, recording a new visit without inflating `count_unique_visitors()`.

## 4. Technology Selection
- **Core Language**: Python 3.11.
- **Detector**: Ultralytics YOLOv8 (`yolov8n.pt`).
- **Tracker**: Supervision ByteTrack integration.
- **Recognition**: InsightFace `buffalo_sc` (ArcFace 512-d embedding extractor).
- **ORM & DB**: SQLAlchemy 2.0 with SQLite database engine.
- **Monitoring & Metrics**: `psutil` telemetry collector.
- **Testing Framework**: `pytest`.
- **UI Framework**: Streamlit web dashboard (`dashboard.py`).

## 5. Feature Planning
Key feature milestones planned:
1. Video stream abstraction (File & Threaded RTSP).
2. Detection & configurable frame skipping (`skip_frames=5`).
3. Spatial multi-object tracking.
4. Face quality evaluation (sharpness, size, confidence).
5. Facial embedding & gallery similarity matching.
6. Auto-registration for unregistered faces.
7. Visitor state machine (`OUTSIDE` -> `INSIDE` -> `OUTSIDE`).
8. Event manager & structured logger (`events.log`).
9. Atomic persistence (image crops + DB transaction).
10. Telemetry & dashboard UI.

## 6. Module Decomposition
The repository was decomposed into clean Python packages under `app/`:
- `app/config`: Schema validation via Pydantic & JSON loader.
- `app/input`: `FileVideoSource` & `RTSPVideoSource`.
- `app/detection`: `YOLODetector` wrapper.
- `app/tracking`: `ByteTrackerWrapper`.
- `app/recognition`: `InsightFaceEngine` & `SimilarityMatcher`.
- `app/registration`: `AutoRegistrationEngine` & quality scorer.
- `app/visitors`: `VisitorStateMachine` & `TemporalPredictionHistory`.
- `app/events`: `EventManager` & `StructuredEventLogger`.
- `app/database`: SQLAlchemy models (`Visitor`, `Embedding`, `Event`, `Track`) & repository operations.
- `app/pipeline`: `VideoPipelineProcessor` orchestrator.
- `app/monitoring`: Telemetry latency monitor.

## 7. Database Planning
Designed 4 core relational tables:
- `visitors`: Primary record (`face_id`, `first_seen`, `last_seen`, `total_visits`, `current_status`).
- `embeddings`: Foreign-key bound face embeddings (`face_id`, `embedding_data` BLOB).
- `events`: Audit trail of `ENTRY` and `EXIT` events (`face_id`, `track_id`, `event_type`, `timestamp`, `image_path`, `confidence`, `frame_number`).
- `tracks`: Spatial track history (`face_id`, `track_id`, `started_at`, `ended_at`).

## 8. AI Model Planning
- **Face Detection**: YOLOv8 nano model (`yolov8n.pt`) fine-tuned for high-speed bounding box localization.
- **Feature Extraction**: InsightFace `buffalo_sc` model producing L2-normalized 512-dimensional feature vectors.
- **Execution Provider**: CPU execution fallback with optional ONNX Runtime GPU support.

## 9. Tracking Planning
- Selected **ByteTrack** for spatial data association due to its resilience against temporary low-score detections and occlusions.
- Configured track parameters: `max_age=30` frames and `track_thresh=0.50`.

## 10. Recognition Planning
- Cosine similarity threshold tuned to `0.45` based on empirical validation.
- Similarity formula:
  $$\text{similarity}(u, v) = \frac{u \cdot v}{\|u\| \|v\|}$$
- Embeddings are stored L2-normalized, allowing fast inner product calculation.

## 11. Registration Planning
- Built a candidate buffer evaluated over 3 detection frames.
- Quality score computed as:
  $$\text{Quality Score} = \text{confidence} \times (\text{sharpness} + 1) \times \sqrt{\text{bbox\_area}}$$
- Best candidate crop selected for persistent registration to prevent registering blurry or obscured face crops.

## 12. Entry / Exit Event Planning
- Enforced strict state machine transitions:
  - `OUTSIDE` + Valid Detection -> Trigger `ENTRY` Event -> Transition to `INSIDE`.
  - `INSIDE` + Inactive > `exit_timeout_frames` (30 frames) -> Trigger `EXIT` Event -> Transition to `OUTSIDE`.
- State machine prevents duplicate entry/exit events for active visitors.

## 13. Logging Planning
- Structured event logging written to `logs/events.log`.
- Log format includes timestamp, event name, `face_id`, `track_id`, confidence, frame index, and image paths.

## 14. Testing Strategy
- Comprehensive test suite in `tests/` containing 26 unit and integration test modules.
- Tests cover configuration, detection, tracking, matching, auto-registration, re-identification, state machine state transitions, database operations, and adversarial scenario handling.

## 15. Deployment Planning
- Packaged using Docker and Docker Compose.
- Persistence achieved via volume mounts for `database/`, `logs/`, and `output/`.
- Non-root user execution and health check scripts configured.

## 16. AI-Assisted Development Workflow
- **Prompt-Driven Architecture**: Used structured prompt directives specifying strict system rules (e.g. prohibited libraries, atomic file writes).
- **Incremental Code Generation**: Generated clean modular components, inspecting unit test outputs at every iteration.

## 17. Validation and Debugging Workflow
- Test-driven validation loop: `IMPLEMENT -> RUN TESTS -> INSPECT LOGS -> FIX -> RE-TEST`.
- Ran empirical benchmark execution against `data/sample_video.mp4` to collect actual latency metrics.

## 18. Final Audit
- Complete inspection of repository against Katomaran Hackathon evaluation requirements, verifying doc completeness, clean git state, reproducible Docker environment, and empirical sample exports.
