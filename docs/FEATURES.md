# Feature Documentation - VISITR-AI

This document provides complete documentation for all features implemented in **VISITR-AI**.

---

## Feature Index

1. [Video Input Abstraction](#1-video-input-abstraction)
2. [MP4 Video Processing](#2-mp4-video-processing)
3. [RTSP Live Stream Support & Auto-Reconnection](#3-rtsp-live-stream-support--auto-reconnection)
4. [YOLO Face Detection](#4-yolo-face-detection)
5. [Configurable Frame Skipping](#5-configurable-frame-skipping)
6. [ByteTrack Multi-Object Face Tracking](#6-bytetrack-multi-object-face-tracking)
7. [InsightFace ArcFace 512-d Embedding Generation](#7-insightface-arcface-512-d-embedding-generation)
8. [Cosine Similarity Facial Matching](#8-cosine-similarity-facial-matching)
9. [Automatic Registration of Unknown Faces](#9-automatic-registration-of-unknown-faces)
10. [Persistent Face ID Assignment (`VIS-XXXXX`)](#10-persistent-face-id-assignment-vis-xxxxx)
11. [Tracker ID Handling (`track_id`)](#11-tracker-id-handling-track_id)
12. [Visitor Re-identification](#12-visitor-re-identification)
13. [Visitor State Machine](#13-visitor-state-machine)
14. [Entry Event Detection](#14-entry-event-detection)
15. [Exit Event Detection](#15-exit-event-detection)
16. [Unique Visitor Analytics Counting](#16-unique-visitor-analytics-counting)
17. [Cropped Entry Image Persistence](#17-cropped-entry-image-persistence)
18. [Cropped Exit Image Persistence](#18-cropped-exit-image-persistence)
19. [Structured Event Logging](#19-structured-event-logging)
20. [Centralized `events.log` Audit Trail](#20-centralized-eventslog-audit-trail)
21. [Database Persistence (SQLite + SQLAlchemy ORM)](#21-database-persistence-sqlite--sqlalchemy-orm)
22. [Pydantic Configuration Validation](#22-pydantic-configuration-validation)
23. [Error Handling & Failure Recovery](#23-error-handling--failure-recovery)
24. [Restart Persistence](#24-restart-persistence)
25. [Telemetry Latency Metrics](#25-telemetry-latency-metrics)
26. [Health Check Script & Streamlit Dashboard](#26-health-check-script--streamlit-dashboard)

---

## Detailed Feature Specifications

### 1. Video Input Abstraction
- **Purpose**: Unified interface for reading video frames from static files or live IP cameras.
- **Implementation Module**: [app/input/video_source.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/input/video_source.py)
- **Input**: Configuration dictionary or video source URI.
- **Output**: Generator yielding OpenCV BGR frame arrays (`numpy.ndarray`).
- **Configuration**: `"input": {"type": "file" | "rtsp", "source": "path/or/url"}`
- **Failure Handling**: Raises `FileNotFoundError` for missing video files; attempts thread reconnection for network streams.

### 2. MP4 Video Processing
- **Purpose**: High-speed batch processing of static MP4 video files.
- **Implementation Module**: [app/input/file_source.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/input/file_source.py)
- **Input**: Absolute or relative file path to MP4 video.
- **Output**: Sequential frame reader.
- **Configuration**: `"source": "data/sample_video.mp4"`
- **Failure Handling**: Validates file existence and OpenCV `VideoCapture.isOpened()` status before pipeline execution.

### 3. RTSP Live Stream Support & Auto-Reconnection
- **Purpose**: Threaded client for reading live IP camera streams with background frame buffering and connection retry logic.
- **Implementation Module**: [app/input/rtsp_source.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/input/rtsp_source.py)
- **Input**: RTSP URL (`rtsp://admin:pass@ip:554/stream`).
- **Output**: Latest available frame from queue.
- **Configuration**: `"rtsp_reconnect_delay": 3.0`, `"rtsp_max_retries": 10`
- **Failure Handling**: Background thread detects socket drop, waits `rtsp_reconnect_delay` seconds, and retries up to `rtsp_max_retries` times.

### 4. YOLO Face Detection
- **Purpose**: Bounding box localization of faces in video frames.
- **Implementation Module**: [app/detection/yolo_detector.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/detection/yolo_detector.py)
- **Input**: BGR image frame.
- **Output**: List of bounding box coordinates `[x1, y1, x2, y2]` and detection confidence scores.
- **Configuration**: `"detection": {"model": "yolov8n.pt", "confidence": 0.50, "iou": 0.45}`
- **Failure Handling**: Falls back to empty detection list if no faces meet `confidence` threshold.

### 5. Configurable Frame Skipping
- **Purpose**: Computational load reduction by executing deep learning detection every N frames.
- **Implementation Module**: [app/detection/yolo_detector.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/detection/yolo_detector.py)
- **Input**: Frame index counter.
- **Output**: Detection execution flag.
- **Configuration**: `"skip_frames": 5` (executes detection once every 6 frames).
- **Failure Handling**: Interim frames rely on spatial tracking propagation.

### 6. ByteTrack Multi-Object Face Tracking
- **Purpose**: Continuous spatial association of face bounding boxes across consecutive frames.
- **Implementation Module**: [app/tracking/byte_tracker.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/tracking/byte_tracker.py)
- **Input**: Frame image + detection bounding boxes.
- **Output**: Tracked targets with temporary integer `track_id` assignments.
- **Configuration**: `"tracking": {"max_age": 30, "track_thresh": 0.50}`
- **Failure Handling**: Target track is retained during brief occlusion up to `max_age` frames.

### 7. InsightFace ArcFace 512-d Embedding Generation
- **Purpose**: Extraction of deep 512-dimensional facial feature representation vectors.
- **Implementation Module**: [app/recognition/insightface_engine.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/recognition/insightface_engine.py)
- **Input**: Cropped face image array.
- **Output**: L2-normalized 512-element NumPy float32 array.
- **Configuration**: `"recognition": {"model": "buffalo_sc"}`
- **Failure Handling**: Validates face crop dimensions (`min_face_size >= 50px`) before embedding extraction.

### 8. Cosine Similarity Facial Matching
- **Purpose**: Comparing query facial embeddings against registered gallery database.
- **Implementation Module**: [app/recognition/matcher.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/recognition/matcher.py)
- **Input**: Query embedding vector + database gallery.
- **Output**: Matched persistent `face_id` + similarity score or `None` if unknown.
- **Configuration**: `"similarity_threshold": 0.45`
- **Failure Handling**: Returns `None` if maximum similarity score is below `0.45`.

### 9. Automatic Registration of Unknown Faces
- **Purpose**: Best-frame candidate selection and persistent ID registration for unrecognized targets.
- **Implementation Module**: [app/registration/auto_registration.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/registration/auto_registration.py)
- **Input**: Candidate face crops over 3 detection frames.
- **Output**: Newly registered `Visitor` record and embedding in SQLite database.
- **Configuration**: Quality metric `confidence * (sharpness + 1) * sqrt(area)`.
- **Failure Handling**: Discards low-quality or blurry face crops.

### 10. Persistent Face ID Assignment (`VIS-XXXXX`)
- **Purpose**: Unique string identity string assigned permanently to every visitor.
- **Implementation Module**: [app/database/repository.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/database/repository.py)
- **Input**: Registration trigger.
- **Output**: Formatted string `VIS-00001`, `VIS-00002`, etc.
- **Configuration**: Database autoincrement sequence with `VIS-%05d` formatting.
- **Failure Handling**: Database unique constraints prevent duplicate Face ID assignments.

### 11. Tracker ID Handling (`track_id`)
- **Purpose**: Temporary spatial identifier maintained per continuous video track.
- **Implementation Module**: [app/tracking/byte_tracker.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/tracking/byte_tracker.py)
- **Input**: Spatial bounding box stream.
- **Output**: Integer `track_id` (e.g. `1`, `4`, `17`).
- **Configuration**: Tracker internal lifecycle.
- **Failure Handling**: Destroyed upon track termination without affecting persistent `face_id`.

### 12. Visitor Re-identification
- **Purpose**: Resolving returning visitors back to their original `face_id` across stream interruptions or return visits.
- **Implementation Module**: [app/visitors/visitor_manager.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/visitors/visitor_manager.py)
- **Input**: Facial embedding from new spatial track.
- **Output**: Re-linked `face_id` and incremented `total_visits` counter.
- **Configuration**: Cosine matching threshold `0.45`.
- **Failure Handling**: If similarity is ambiguous, target is flagged for quality re-evaluation.

### 13. Visitor State Machine
- **Purpose**: Managing visitor status (`OUTSIDE` vs `INSIDE`) to enforce exactly-once events.
- **Implementation Module**: [app/visitors/visitor_state.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/visitors/visitor_state.py)
- **Input**: Detection updates and frame inactivity counters.
- **Output**: State transition triggers (`ENTRY` / `EXIT`).
- **Configuration**: `"exit_timeout_frames": 30`
- **Failure Handling**: Prevents duplicate entry events while visitor remains `INSIDE`.

### 14. Entry Event Detection
- **Purpose**: Logging an `ENTRY` event when an `OUTSIDE` visitor is detected and recognized.
- **Implementation Module**: [app/events/event_manager.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/events/event_manager.py)
- **Input**: Valid face recognition match.
- **Output**: Database `Event` record + entry image crop.
- **Configuration**: `"save_images": true`
- **Failure Handling**: Transactional database write guarantees atomic recording.

### 15. Exit Event Detection
- **Purpose**: Logging an `EXIT` event when an `INSIDE` visitor is unseen for > `exit_timeout_frames`.
- **Implementation Module**: [app/events/event_manager.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/events/event_manager.py)
- **Input**: Inactivity timeout counter reaching threshold.
- **Output**: Database `Event` record + exit image crop.
- **Configuration**: `"exit_timeout_frames": 30`
- **Failure Handling**: Pipeline flush forces exit events for active visitors on video termination.

### 16. Unique Visitor Analytics Counting
- **Purpose**: Calculating accurate unique visitor counts immune to identity fragmentation.
- **Implementation Module**: [app/database/repository.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/database/repository.py)
- **Input**: Query request.
- **Output**: `session.query(Visitor).count()` integer.
- **Configuration**: SQLite ORM query.
- **Failure Handling**: Evaluated directly against persistent database entities.

### 17. Cropped Entry Image Persistence
- **Purpose**: Saving high-quality entry face crops to disk.
- **Implementation Module**: [app/utils/image_utils.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/utils/image_utils.py)
- **Input**: BGR frame + bounding box.
- **Output**: JPEG image stored in `logs/entries/YYYY-MM-DD/`.
- **Configuration**: `"entry_directory": "logs/entries"`
- **Failure Handling**: Writes to `.tmp` file before atomic rename (`os.replace`).

### 18. Cropped Exit Image Persistence
- **Purpose**: Saving last-seen exit face crops to disk.
- **Implementation Module**: [app/utils/image_utils.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/utils/image_utils.py)
- **Input**: Last known face crop buffer.
- **Output**: JPEG image stored in `logs/exits/YYYY-MM-DD/`.
- **Configuration**: `"exit_directory": "logs/exits"`
- **Failure Handling**: Fallback to last valid detected frame if target disappears abruptly.

### 19. Structured Event Logging
- **Purpose**: Formatting structured event log entries with standardized attributes.
- **Implementation Module**: [app/events/event_logger.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/events/event_logger.py)
- **Input**: Event metadata (timestamp, face_id, track_id, event_type, confidence, frame).
- **Output**: Formatted log record.
- **Configuration**: Pipe-separated structured format.
- **Failure Handling**: File handler error trapping prevents application crash.

### 20. Centralized `events.log` Audit Trail
- **Purpose**: Maintaining a persistent audit log file for system activity.
- **Implementation Module**: [app/events/event_logger.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/events/event_logger.py)
- **Input**: Application event stream.
- **Output**: `logs/events.log` file on disk.
- **Configuration**: `"event_log": "logs/events.log"`
- **Failure Handling**: Automatic directory creation on startup.

### 21. Database Persistence (SQLite + SQLAlchemy ORM)
- **Purpose**: Transactional storage of system relational metadata.
- **Implementation Module**: [app/database/database.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/database/database.py)
- **Input**: ORM model objects (`Visitor`, `Embedding`, `Event`, `Track`).
- **Output**: `database/visitors.db` SQLite file.
- **Configuration**: `"database": {"url": "sqlite:///database/visitors.db"}`
- **Failure Handling**: Automatic rollbacks on database commit failures.

### 22. Pydantic Configuration Validation
- **Purpose**: Strictly validating application configuration settings on load.
- **Implementation Module**: [app/config/loader.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/config/loader.py)
- **Input**: `config.json` file.
- **Output**: Validated `AppConfig` Pydantic instance.
- **Configuration**: `config.json` file path.
- **Failure Handling**: Provides clear validation error messages for missing or invalid configuration keys.

### 23. Error Handling & Failure Recovery
- **Purpose**: Ensuring system resilience against corrupt frames, missing models, or invalid input paths.
- **Implementation Module**: [app/pipeline/processor.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/pipeline/processor.py)
- **Input**: Exceptions raised during execution.
- **Output**: Safe error logging and resource cleanup.
- **Configuration**: Try-except blocks wrapping pipeline stages.
- **Failure Handling**: Skips bad frames without terminating overall processing loop.

### 24. Restart Persistence
- **Purpose**: Reloading existing facial embedding gallery from database upon application restart.
- **Implementation Module**: [app/recognition/matcher.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/recognition/matcher.py)
- **Input**: Existing SQLite `visitors.db`.
- **Output**: In-memory similarity gallery populated on boot.
- **Configuration**: Automatic gallery load in `pipeline/processor.py`.
- **Failure Handling**: Re-initializes empty gallery if database is empty.

### 25. Telemetry Latency Metrics
- **Purpose**: Real-time measurement of per-stage computational latencies and memory usage.
- **Implementation Module**: [app/monitoring/metrics.py](file:///d:/4th%20yr/Katomaran_Proj/proj/app/monitoring/metrics.py)
- **Input**: Stage execution timing timestamps (`time.perf_counter()`).
- **Output**: Summary latency breakdown report (detection, tracking, recognition, total ms/frame, FPS, RAM MB).
- **Configuration**: Automatic collection during pipeline execution.
- **Failure Handling**: Gracefully handles missing `psutil` on restricted environments.

### 26. Health Check Script & Streamlit Dashboard
- **Purpose**: System diagnostics and interactive analytical web user interface.
- **Implementation Module**: [scripts/health_check.py](file:///d:/4th%20yr/Katomaran_Proj/proj/scripts/health_check.py), [dashboard.py](file:///d:/4th%20yr/Katomaran_Proj/proj/dashboard.py)
- **Input**: Database & log files.
- **Output**: Streamlit web dashboard with metric KPIs, image carousels, and health status indicators.
- **Configuration**: Streamlit runner (`streamlit run dashboard.py`).
- **Failure Handling**: Displays informative status messages if database is empty.
