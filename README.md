# VISITR-AI

> Intelligent Face Tracking, Auto-Registration & Unique Visitor Analytics System

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests: Pytest](https://img.shields.io/badge/Tests-18%20Passed-brightgreen.svg)](docs/TESTING.md)

---

## Overview

**VISITR-AI** is a modular, production-style computer vision system engineered for real-time video feeds (MP4 and RTSP IP cameras). It detects faces, tracks targets continuously using ByteTrack, auto-registers genuinely new visitors with persistent Face IDs (`VIS-XXXXX`), recognizes returning faces via InsightFace ArcFace 512-d embeddings, and maintains audit-defensible unique visitor analytics with exactly-once ENTRY/EXIT event logging.

---

## Problem Statement

Traditional video analytics systems struggle with identity fragmentation: when a person is temporarily occluded or leaves and returns, traditional trackers assign a new temporary ID, causing **inflated unique visitor counts**, **duplicate entry/exit logs**, and **corrupted analytics**.

---

## Solution

VISITR-AI solves this through a **Decoupled Identity Architecture**:
- **Temporary Spatial Tracking**: `track_id` (assigned by ByteTrack per continuous track)
- **Persistent Facial Identity**: `face_id` (format: `VIS-00001`, assigned by InsightFace / ArcFace cosine matching)

When a visitor exits and re-enters under a new `track_id` (e.g. `track_id = 31`), ArcFace embedding matching resolves the target back to their original `face_id` (`VIS-00001`). This records a re-entry visit while preserving the exact `count_unique_visitors()` metric without count inflation.

---

## Features

- **Dual Source Support**: Process static MP4 video files or live RTSP streams with auto-reconnection.
- **YOLO Face Detection**: Configurable confidence, IoU, and detection frame skipping (`skip_frames`).
- **ByteTrack Tracking**: Smooth target tracking handling temporary occlusions.
- **ArcFace Recognition**: SOTA 512-dimensional normalized feature embedding extraction.
- **Best-Frame Auto-Registration**: Quality filtering (minimum size, sharpness, confidence) selecting the optimal crop before ID assignment.
- **Visitor State Machine**: Strict `OUTSIDE` -> `INSIDE` -> `OUTSIDE` state guards guaranteeing exactly-once `ENTRY` and `EXIT` events.
- **Atomic Persistence**: Image crops saved atomically (`.tmp` write -> rename) to `logs/entries/` and `logs/exits/` alongside SQLite DB transactions.
- **Structured Logging**: Standardized audit log written to `logs/events.log`.
- **Streamlit UI**: Real-time analytics dashboard with metric KPIs and image carousels.

---

## Architecture

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

## Technology Stack

- **Core**: Python 3.11, OpenCV
- **Detection & Tracking**: YOLOv8 (`ultralytics`), ByteTrack (`supervision`)
- **Face Recognition**: InsightFace (`buffalo_sc` ArcFace 512-d), ONNX Runtime
- **Database**: SQLite, SQLAlchemy ORM
- **Logging & Monitoring**: Python `logging`, `psutil`
- **Testing**: `pytest`
- **Dashboard**: Streamlit

---

## Project Structure

```
VISITR-AI/
├── app/
│   ├── main.py                    # Main CLI application entry point
│   ├── config/loader.py           # Configuration schema validator & loader
│   ├── input/                     # File and RTSP video source abstractions
│   ├── detection/yolo_detector.py # YOLO face detector with skip frames
│   ├── tracking/byte_tracker.py   # ByteTrack tracker wrapper
│   ├── recognition/               # InsightFace ArcFace & cosine similarity matcher
│   ├── registration/              # Quality filter & best-frame auto-registration
│   ├── visitors/                  # Visitor state machine & temporal history
│   ├── events/                    # Event manager & structured event logger
│   ├── database/                  # SQLAlchemy models & repository layer
│   ├── pipeline/processor.py      # Main pipeline orchestrator
│   ├── monitoring/metrics.py      # Telemetry & compute latency monitor
│   └── utils/                     # Image crop, sharpness, and similarity utilities
├── tests/                         # 18 automated pytest test modules
├── data/                          # Video stream input directory
├── models/                        # Pre-trained model weight cache
├── logs/                          # Runtime logs, entry crops, exit crops
├── database/visitors.db           # SQLite database
├── output/processed/              # Annotated output video file
├── sample_output/                 # Exported actual execution benchmark outputs
├── docs/                          # Architecture, AI planning, compute analysis, compliance matrix
├── scripts/                       # Benchmark video & sample output exporter scripts
├── dashboard.py                   # Streamlit web UI dashboard
├── config.json                    # Application configuration
├── requirements.txt               # Dependencies specification
├── Dockerfile                     # Docker container definition
├── docker-compose.yml             # Docker Compose orchestrator
├── .env.example                   # Environment variables sample
├── .gitignore                     # Git hygiene & privacy filters
├── README.md                      # Project README
└── LICENSE                        # MIT License
```

---

## Requirements

- Python 3.11+
- FFmpeg (for video rendering)
- 4 GB RAM minimum

---

## Installation

```bash
# Clone the repository
git clone https://github.com/user/VISITR-AI.git
cd VISITR-AI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Model Setup

Pre-trained YOLO and InsightFace model weights automatically initialize and download on first launch into the local cache (`~/.insightface/models/` and `./yolov8n.pt`).

---

## Configuration

All system thresholds are configured via `config.json`:

```json
{
  "input": {
    "type": "file",
    "source": "data/sample_video.mp4",
    "rtsp_reconnect_delay": 3.0,
    "rtsp_max_retries": 10
  },
  "detection": {
    "model": "yolov8n.pt",
    "confidence": 0.50,
    "iou": 0.45,
    "skip_frames": 5
  },
  "tracking": {
    "tracker": "bytetrack",
    "max_age": 30,
    "track_thresh": 0.50
  },
  "recognition": {
    "model": "buffalo_sc",
    "similarity_threshold": 0.45,
    "min_face_size": 50
  },
  "events": {
    "exit_timeout_frames": 30,
    "save_images": true,
    "entry_directory": "logs/entries",
    "exit_directory": "logs/exits",
    "event_log": "logs/events.log"
  },
  "database": {
    "url": "sqlite:///database/visitors.db"
  },
  "output": {
    "save_video": true,
    "path": "output/processed/processed_video.mp4"
  }
}
```

---

## MP4 Usage

To run the application on a video file:

```bash
# Generate benchmark sample video
python scripts/generate_sample_video.py

# Run main processing pipeline
python -m app.main --config config.json
```

---

## RTSP Usage

To run live against an RTSP IP camera feed:

```bash
python -m app.main --config config.json --rtsp "rtsp://admin:pass@192.168.1.100:554/stream1"
```

---

## Database

VISITR-AI uses SQLite with SQLAlchemy ORM comprising 4 core tables:
- `visitors`: `face_id`, `first_seen`, `last_seen`, `total_visits`, `current_status`.
- `embeddings`: `id`, `face_id`, `embedding_data`.
- `events`: `id`, `face_id`, `track_id`, `event_type`, `timestamp`, `image_path`, `confidence`, `frame_number`.
- `tracks`: `id`, `face_id`, `track_id`, `started_at`, `ended_at`.

---

## Auto Registration

When an unknown target is detected, candidate crops are collected over 3 frames. The candidate with the highest composite quality score (`confidence * (sharpness + 1) * sqrt(area)`) is selected, assigned a persistent Face ID (`VIS-XXXXX`), and registered in the database.

---

## Recognition

Feature vectors (512-d L2-normalized) extracted by InsightFace ArcFace are matched against the gallery using Cosine Similarity:

$$\text{similarity}(u, v) = \frac{u \cdot v}{\|u\| \|v\|}$$

If `similarity >= similarity_threshold` (default `0.45`), identity is matched.

---

## Tracking

ByteTrack maintains bounding box spatial association across frames, assigning temporary `track_id` values.

---

## Re-identification

When a previously registered visitor returns (even with a new `track_id`), ArcFace matching links the target back to their existing `face_id`. This records a new visit (`total_visits += 1`) while leaving `unique_visitors` unchanged.

---

## Entry / Exit Logging

Strict state machine rules (`OUTSIDE` -> `INSIDE` -> `OUTSIDE`) guarantee exactly one `ENTRY` event when entering and exactly one `EXIT` event after `exit_timeout_frames` of inactivity.

---

## Unique Visitor Counting

Unique visitors are calculated directly via database-backed persistent Face IDs:

```python
unique_count = session.query(Visitor).count()
```

---

## Sample Output

Execution outputs are exported in `sample_output/`:
- `sample_output/entries/`: Cropped entry face images.
- `sample_output/exits/`: Cropped exit face images.
- `sample_output/events.log`: Structured audit logs.
- `sample_output/database_snapshot.sql`: Complete SQL database dump.
- `sample_output/summary.json`: Measured telemetry JSON summary.

---

## Performance

Measured execution telemetry on 360 frames benchmark video:
- **Processing FPS**: **20.3 FPS**
- **Total Latency**: **60.71 ms / frame**
  - Detection Latency: 36.41 ms
  - Tracking Latency: 1.59 ms
  - Recognition Latency: 21.88 ms
- **RAM Footprint**: **541.5 MB**

---

## Testing

Run the 18 automated tests:

```bash
python -m pytest tests/ -v
```

See [docs/TESTING.md](docs/TESTING.md) for detailed descriptions.

---

## AI Planning

Detailed design rationale, trade-offs, and requirement matrices are documented in [docs/AI_PLANNING.md](docs/AI_PLANNING.md).

---

## Assumptions

1. Video input streams have adequate lighting for face localization.
2. Minimum face crop size is at least 50x50 pixels.

---

## Limitations

1. Extreme facial occlusions (>60 degree side profiles) reduce ArcFace embedding accuracy.
2. CPU processing speed scales with resolution; `skip_frames = 5` is recommended for 1080p feeds.

---

## Demo Video

- **Explanatory Loom Video Demo**: [https://loom.com/share/visitr-ai-demo-placeholder](https://loom.com/share/visitr-ai-demo-placeholder)

---

## Future Improvements

- GPU Acceleration with TensorRT / CUDA ONNX Execution Providers.
- Multi-camera re-identification across spatial camera networks.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

This project is a part of a hackathon run by https://katomaran.com
