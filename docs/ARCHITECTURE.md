# System Architecture Document - VISITR-AI

## Overview

**VISITR-AI** is built on a decoupled identity computer vision architecture designed to solve identity fragmentation in visitor tracking and analytics.

---

## Architecture Diagram

```
                              Video Source
                             (MP4 / RTSP)
                                  │
                                  ▼
                            Frame Manager
                     (FileSource / RTSPSource)
                                  │
                                  ▼
                         YOLO Face Detection
                           (skip_frames=5)
                                  │
                                  ▼
                              ByteTrack
                     (assigns temporary track_id)
                                  │
                                  ▼
                    Face Crop / Quality Filtering
                  (min_size, sharpness, confidence)
                                  │
                                  ▼
                   InsightFace / ArcFace Embedding
                 (extracts 512-d L2-norm vector)
                                  │
                                  ▼
                          Identity Matcher
                      (Cosine Similarity >= 0.45)
                      ┌───────────┴───────────┐
                   KNOWN                   UNKNOWN
                      │                       │
                      │               Auto Registration
                      │           (Best-Frame Crop Evaluation)
                      └───────────┬───────────┘
                                  │
                                  ▼
                          Persistent Face ID
                             (VIS-XXXXX)
                                  │
                                  ▼
                        Visitor State Manager
                 (OUTSIDE -> INSIDE -> OUTSIDE transitions)
                                  │
                                  ▼
                      Entry / Exit Event Manager
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
           Images            events.log           SQLite DB
       (entries/exits)      (structured)     (visitors, events)
              └───────────────────┬───────────────────┘
                                  │
                                  ▼
                       Unique Visitor Analytics
                    (COUNT(DISTINCT face_id))
```

---

## Component Breakdowns

### 1. Video Source Layer
- **Implementation**: `FileVideoSource` ([app/input/file_source.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/input/file_source.py)), `RTSPVideoSource` ([app/input/rtsp_source.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/input/rtsp_source.py)).
- **Role**: Reads frames from MP4 files or RTSP IP camera streams. Implements threaded background frame buffering and automatic socket reconnect retry logic (`rtsp_max_retries = 10`) for live network feeds.

### 2. Frame Manager
- **Implementation**: `VideoPipelineProcessor` ([app/pipeline/processor.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/pipeline/processor.py)).
- **Role**: Manages frame sequence indexing, timestamps, and detection skipping (`skip_frames = 5`). Dispatches frames to detection and tracking modules while computing telemetry latencies.

### 3. YOLO Face Detection
- **Implementation**: `YOLODetector` ([app/detection/yolo_detector.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/detection/yolo_detector.py)).
- **Role**: Uses Ultralytics YOLOv8 (`yolov8n.pt`) to localize facial bounding boxes with configurable confidence (`0.50`) and IoU (`0.45`) thresholds.

### 4. ByteTrack Multi-Object Tracker
- **Implementation**: `ByteTrackerWrapper` ([app/tracking/byte_tracker.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/tracking/byte_tracker.py)).
- **Role**: Maintains spatial target continuity across frames, assigning temporary `track_id` integers. Handles brief target occlusions up to `max_age = 30` frames.

### 5. Face Crop / Quality Filtering
- **Implementation**: `QualityEvaluator` ([app/registration/auto_registration.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/registration/auto_registration.py)), `image_utils` ([app/utils/image_utils.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/utils/image_utils.py)).
- **Role**: Filters out unusable face crops. Evaluates minimum dimensions (`>= 50px`), detection confidence, and Laplacian variance sharpness score before passing crops to the recognition engine.

### 6. InsightFace / ArcFace Embedding
- **Implementation**: `InsightFaceEngine` ([app/recognition/insightface_engine.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/recognition/insightface_engine.py)).
- **Role**: Extracts L2-normalized 512-dimensional feature embedding vectors using the SOTA `buffalo_sc` ArcFace model. (Strictly excludes the prohibited `face_recognition` library).

### 7. Identity Matcher
- **Implementation**: `SimilarityMatcher` ([app/recognition/matcher.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/recognition/matcher.py)).
- **Role**: Computes cosine similarity between query feature vectors and gallery embeddings saved in SQLite DB:
  $$\text{similarity}(u, v) = \frac{u \cdot v}{\|u\| \|v\|}$$
- Classifies target as **KNOWN** if similarity score `>= 0.45`, or **UNKNOWN** if below threshold.

### 8. Auto Registration Engine
- **Implementation**: `AutoRegistrationEngine` ([app/registration/auto_registration.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/registration/auto_registration.py)).
- **Role**: Buffers candidate face crops for unrecognized targets over 3 detection frames, selects the frame with the highest composite quality score (`confidence * (sharpness + 1) * sqrt(area)`), generates persistent embedding, and registers visitor.

### 9. Persistent Face ID Manager
- **Implementation**: `VisitorRepository` ([app/database/repository.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/database/repository.py)).
- **Role**: Assigns permanent, database-backed string identifiers (`VIS-00001`, `VIS-00002`) that remain constant across restarts and return visits.

### 10. Visitor State Manager
- **Implementation**: `VisitorStateMachine` ([app/visitors/visitor_state.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/visitors/visitor_state.py)).
- **Role**: Tracks operational visitor states (`OUTSIDE` vs `INSIDE`). Enforces strict state transition rules to eliminate duplicate entry and exit events.

### 11. Entry / Exit Event Manager
- **Implementation**: `EventManager` ([app/events/event_manager.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/events/event_manager.py)).
- **Role**: Triggers `ENTRY` event on initial recognition and `EXIT` event after `exit_timeout_frames = 30` frames of target absence. Coordinates atomic image saving, database commits, and logging.

### 12. Storage & Persistence Layer
- **Images**: Saves entry and exit crops to `logs/entries/YYYY-MM-DD/` and `logs/exits/YYYY-MM-DD/`.
- **Structured Log**: Appends formatted audit records to `logs/events.log`.
- **SQLite Database**: Atomic SQLAlchemy transactions persisting `visitors`, `embeddings`, `events`, and `tracks` tables.

### 13. Unique Visitor Analytics
- **Implementation**: `count_unique_visitors()` ([app/database/repository.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/database/repository.py)).
- **Role**: Computes unique visitor counts directly from database persistent Face IDs (`COUNT(DISTINCT face_id)`). Re-identifications increment `total_visits` without inflating unique counts.

---

## Identity Model: TRACK ID vs Persistent FACE ID

| Dimension | TRACK ID | Persistent FACE ID |
| :--- | :--- | :--- |
| **Source Module** | ByteTrack Multi-Object Tracker | InsightFace ArcFace / Similarity Matcher |
| **Scope** | Temporary (current continuous stream track) | Permanent across restarts and return visits |
| **Data Format** | Integer (`1`, `4`, `17`) | String (`VIS-00001`, `VIS-00002`) |
| **Lifecycle** | Cleared when target leaves camera view | Saved permanently in SQLite Database |

---

## Database ER Schema Diagram

```
  ┌─────────────────────────────────┐
  │            visitors             │
  ├─────────────────────────────────┤
  │ face_id (PK, VARCHAR)           │◄──────┐
  │ first_seen (DATETIME)           │       │
  │ last_seen (DATETIME)            │       │
  │ total_visits (INTEGER)          │       │
  │ current_status (VARCHAR)        │       │
  └─────────────────────────────────┘       │
                  ▲                         │
                  │ (1 : N)                 │ (1 : N)
  ┌───────────────┴─────────────────┐  ┌────┴────────────────────────────┐
  │           embeddings            │  │             events              │
  ├─────────────────────────────────┤  ├─────────────────────────────────┤
  │ id (PK, INTEGER)                │  │ id (PK, INTEGER)                │
  │ face_id (FK, VARCHAR)           │  │ face_id (FK, VARCHAR)           │
  │ embedding_data (BLOB/JSON)      │  │ track_id (INTEGER)              │
  │ created_at (DATETIME)           │  │ event_type (VARCHAR: ENTRY/EXIT)│
  └─────────────────────────────────┘  │ timestamp (DATETIME)            │
                                       │ image_path (VARCHAR)            │
                                       │ confidence (FLOAT)              │
                                       │ frame_number (INTEGER)          │
                                       └─────────────────────────────────┘
```
