# System Architecture - VISITR-AI

## Overview

VISITR-AI is structured as a decoupled, event-driven computer vision pipeline designed for persistent visitor tracking and unique analytics.

```
                    MP4 / RTSP Stream
                            │
                            ▼
                     VideoSource Layer
             (FileVideoSource / RTSPVideoSource)
                            │
                            ▼
                 YOLO Face Detector (skip_frames)
                            │
                            ▼
                 ByteTrack Multi-Object Tracker
                     (assigns temporary track_id)
                            │
                            ▼
                 Face Quality Evaluator
               (min_size, sharpness, confidence)
                            │
                            ▼
                 InsightFace ArcFace Engine
                 (extracts 512-d L2-norm embedding)
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
                 Visitor State Machine
             ┌──────────────┴──────────────┐
           ENTRY                         EXIT (exit_timeout_frames)
             └──────────────┬──────────────┘
                            │
                            ▼
                 Event & Persistence Manager
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  Cropped Images     SQLite Database       events.log
(logs/entries|exits) (visitors, events)   (structured)
```

---

## Identity Model: TRACK ID vs FACE ID

| Property | TRACK ID | FACE ID |
| :--- | :--- | :--- |
| **Origin** | ByteTrack Spatial Tracking | InsightFace Matcher / Auto-Registration |
| **Scope** | Temporary (current continuous stream segment) | Persistent across system restarts & visits |
| **Format** | Integer (e.g. `17`, `31`) | String (e.g. `VIS-00001`, `VIS-00002`) |
| **Lifecycle** | Destroyed on track loss / exit timeout | Saved permanently in SQLite Database |

### Re-identification Flow Example:
1. `VIS-00001` enters with `track_id = 17` -> `ENTRY` event #1 logged -> `total_visits = 1`, `unique_visitors = 1`.
2. `VIS-00001` exits -> `EXIT` event logged -> status becomes `OUTSIDE`.
3. `VIS-00001` returns 5 minutes later with `track_id = 31`.
4. InsightFace matches embedding to `VIS-00001`.
5. `ENTRY` event #2 logged -> `total_visits = 2`.
6. **Unique Visitor Count**: Query `COUNT(DISTINCT face_id)` from database returns `1`. Count is NOT inflated!

---

## Visitor State Machine Transitions

```
               ┌────────────────────────┐
               │        OUTSIDE         │
               └───────────┬────────────┘
                           │ Valid Detection / Recognized Face
                           ▼
               ┌────────────────────────┐
               │         ENTRY          │
               │   (Save Image + Log)   │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │        INSIDE          │
               └───────────┬────────────┘
                           │ Missing > exit_timeout_frames
                           ▼
               ┌────────────────────────┐
               │          EXIT          │
               │   (Save Image + Log)   │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │        OUTSIDE         │
               └────────────────────────┘
```

---

## Database ER Schema Diagram

- **`visitors`**: `face_id` (PK), `first_seen`, `last_seen`, `total_visits`, `current_status`.
- **`embeddings`**: `id` (PK), `face_id` (FK), `embedding_data` (JSON/binary).
- **`events`**: `id` (PK), `face_id` (FK), `track_id`, `event_type`, `timestamp`, `image_path`, `confidence`, `frame_number`.
- **`tracks`**: `id` (PK), `face_id` (FK), `track_id`, `started_at`, `ended_at`.
