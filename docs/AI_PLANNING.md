# AI Planning & Design Rationale - VISITR-AI

## 1. Problem Understanding & Requirements Analysis

The Katomaran Hackathon challenge requires building an intelligent, computer vision-based face tracking, auto-registration, and unique visitor analytics system named **VISITR-AI**.

### Core Technical Objectives:
1. **Persistent Face Identity vs Temporary Tracking**: Strict separation of temporary tracker IDs (`track_id`) assigned frame-by-frame by ByteTrack from persistent Face IDs (`face_id` like `VIS-00001`). Re-identified visitors MUST retain their original `face_id` across temporary track loss or return visits.
2. **Auto-Registration of Unknown Faces**: Genuinely new faces must be evaluated for image quality (bounding box size, sharpness, confidence) and automatically registered without manual intervention.
3. **Exactly-Once Event Integrity**: Every visitor visit cycle must generate exactly 1 `ENTRY` event and 1 `EXIT` event. State machine guards prevent duplicate events.
4. **Unique Visitor Analytics**: Returning visitors increment their `total_visits` counter, but the system's `count_unique_visitors()` query must remain unchanged.
5. **Production Reliability & Auditability**: Atomic file persistence (temp write -> rename), database-backed SQLite/SQLAlchemy schema, and structured event logging to `logs/events.log`.

---

## 2. Technology Stack & Architectural Justification

| Layer | Chosen Technology | Rationale & Justification |
| :--- | :--- | :--- |
| **Language** | Python 3.11 | Modern typing, high performance, full ecosystem support. |
| **Face Detector** | OpenCV + Ultralytics YOLOv8 | High-precision real-time face bounding box localization with configurable confidence & frame skipping (`skip_frames = 5`). |
| **Tracker** | ByteTrack | Multi-object tracking maintaining target spatial continuity across frames and temporary occlusions. |
| **Recognition Engine** | InsightFace ArcFace (`buffalo_sc`) | State-of-the-art 512-dimensional facial embedding extraction with cosine similarity matching. (Explicitly avoids prohibited `face_recognition` library). |
| **Database** | SQLite + SQLAlchemy ORM | Relational metadata storage for visitors, embeddings, events, and tracks. |
| **Logging** | Python `logging` | Structured event stream written to `logs/events.log`. |
| **Test Suite** | `pytest` | 18 automated unit and integration tests verifying all core components. |

---

## 3. Data Flow & Pipeline Architecture

```
                 Video Stream (MP4 / RTSP)
                            │
                            ▼
                     VideoSource Layer
                            │
                            ▼
                 YOLO Face Detector (Skip Frames)
                            │
                            ▼
                 ByteTrack Multi-Object Tracker
                            │
                            ▼
                 Face Quality Evaluator
                            │
                            ▼
                 InsightFace ArcFace Engine (512-d)
                            │
                            ▼
                 Cosine Similarity Matcher
             ┌──────────────┴──────────────┐
          KNOWN                         UNKNOWN
             │                             │
             │                    Auto-Registration Engine
             │                   (VIS-XXXXX, Best-Frame Crop)
             └──────────────┬──────────────┘
                            │
                            ▼
                 Visitor State Machine (OUTSIDE -> INSIDE -> OUTSIDE)
                            │
             ┌──────────────┴──────────────┐
           ENTRY                         EXIT (Exit Timeout)
             └──────────────┬──────────────┘
                            │
                            ▼
                 Event & Storage Layer (SQLite + events.log + Image Crops)
```

---

## 4. Key Engineering Decisions & Trade-offs

1. **Best-Frame Candidate Selection**:
   - Rather than registering the first detected frame (which might be blurry or angled), candidate crops are buffered over 3 frames for new tracks. The crop with the highest composite quality score (`confidence * (sharpness + 1) * sqrt(area)`) is selected for persistent embedding generation and registration.

2. **Frame Skipping Optimization**:
   - Running deep learning object detection on every frame is computationally expensive. Setting `"skip_frames": 5` runs YOLO detection once every 6 frames, relying on lightweight ByteTrack association between detection cycles.
   - **Compute vs Responsiveness Trade-off**: High `skip_frames` reduces CPU/GPU latency by ~70% while maintaining target continuity.

3. **Atomic Persistence Flow**:
   - Image crops are saved to `target_path.tmp` first, validated to ensure size > 0, and then renamed atomically (`os.replace`) before committing the database transaction and appending to `logs/events.log`.

---

## 5. Limitations & Future Scope

- **Severe Face Occlusions**: Extreme angles (>60 degrees) or heavy facial masks reduce recognition accuracy.
- **RTSP Latency**: High-latency network RTSP feeds benefit from queue buffering to avoid frame drops.
