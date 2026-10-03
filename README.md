# VISITR-AI

> Intelligent Face Tracking, Auto-Registration & Unique Visitor Analytics System

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests: Pytest](https://img.shields.io/badge/Tests-26%20Passed-brightgreen.svg)](docs/TESTING.md)

---

## Project Overview

**VISITR-AI** is a modular, production-style computer vision system engineered for real-time video feeds (MP4 video files and live RTSP IP camera streams). It detects faces using YOLOv8, tracks targets continuously using ByteTrack, auto-registers genuinely new visitors with persistent Face IDs (`VIS-XXXXX`), recognizes returning faces via InsightFace ArcFace 512-d embeddings, and maintains audit-defensible unique visitor analytics with exactly-once `ENTRY` and `EXIT` event logging.

---

## Problem Statement

Traditional video analytics systems suffer from **identity fragmentation**: when a person is temporarily occluded, turns away, or leaves and returns, traditional trackers assign a new temporary ID. This causes **inflated unique visitor counts**, **duplicate entry/exit logs**, and **corrupted analytics**.

---

## Objective

The primary objective of VISITR-AI is to decouple temporary spatial tracking from persistent facial identity. By pairing Supervision ByteTrack for continuous spatial tracking with InsightFace ArcFace 512-d embeddings and SQLite persistence, VISITR-AI accurately recognizes returning visitors, records re-entry visits, and maintains an uncorrupted unique visitor count (`count_unique_visitors()`).

---

## Features

- **Dual Source Support**: Process static MP4 video files or live RTSP streams with auto-reconnection.
- **YOLO Face Detection**: Configurable confidence (`0.50`), IoU (`0.45`), and frame skipping (`skip_frames = 5`).
- **ByteTrack Tracking**: Continuous multi-object spatial tracking handling temporary occlusions (`max_age = 30`).
- **ArcFace Recognition**: SOTA 512-dimensional normalized feature embedding extraction (`buffalo_sc`).
- **Best-Frame Auto-Registration**: Quality filtering (sharpness, size, confidence) selecting optimal crops before ID assignment (`VIS-XXXXX`).
- **Visitor State Machine**: Strict `OUTSIDE` -> `INSIDE` -> `OUTSIDE` state guards guaranteeing exactly-once `ENTRY` and `EXIT` events.
- **Atomic Persistence**: Image crops saved atomically (`.tmp` write -> rename) to `logs/entries/` and `logs/exits/` alongside SQLite ORM transactions.
- **Structured Logging**: Standardized audit logs written to `logs/events.log`.
- **Streamlit Web Dashboard**: Real-time analytics web dashboard with metric KPIs and image crop carousels.

---

## Architecture

VISITR-AI uses a decoupled pipeline architecture separating temporary frame-to-frame spatial tracking (`track_id`) from permanent facial biometric identity (`face_id`).

For full details, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

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

## Technology Stack

- **Core**: Python 3.11, OpenCV (`cv2`)
- **Detection & Tracking**: YOLOv8 (`ultralytics`), ByteTrack (`supervision`)
- **Face Recognition**: InsightFace (`buffalo_sc` ArcFace 512-d), ONNX Runtime
- **Database & ORM**: SQLite, SQLAlchemy 2.0 ORM
- **Monitoring & Metrics**: Python `logging`, `psutil`
- **Testing**: `pytest` (26 automated test modules)
- **UI & Dashboard**: Streamlit (`dashboard.py`)
- **Deployment**: Docker, Docker Compose

---

## Project Structure

```
VISITR-AI/
├── app/
│   ├── main.py                    # Application CLI entry point
│   ├── config/loader.py           # Configuration schema validator & loader
│   ├── input/                     # File and RTSP video source abstractions
│   ├── detection/yolo_detector.py # YOLO face detector with skip frames
│   ├── tracking/byte_tracker.py   # ByteTrack tracker wrapper
│   ├── recognition/               # InsightFace ArcFace & cosine similarity matcher
│   ├── registration/              # Quality filter & best-frame auto-registration
│   ├── visitors/                  # Visitor state machine & temporal prediction history
│   ├── events/                    # Event manager & structured event logger
│   ├── database/                  # SQLAlchemy models & repository layer
│   ├── pipeline/processor.py      # Main pipeline orchestrator
│   ├── monitoring/metrics.py      # Telemetry & latency monitoring
│   └── utils/                     # Image crop, sharpness, and similarity utilities
├── tests/                         # 26 automated pytest test modules
├── data/                          # Video stream input directory
├── models/                        # Pre-trained model weight cache
├── logs/                          # Runtime logs, entry crops, exit crops
├── database/visitors.db           # SQLite database
├── output/processed/              # Annotated output video file
├── sample_output/                 # Exported empirical execution outputs
├── docs/                          # Compliance matrix, architecture, AI planning, compute analysis
├── scripts/                       # Benchmark video, health check, sample exporter scripts
├── dashboard.py                   # Streamlit web UI dashboard
├── config.json                    # Application configuration settings
├── requirements.txt               # Dependencies specification
├── Dockerfile                     # Docker container definition
├── docker-compose.yml             # Docker Compose orchestrator
├── .env.example                   # Environment variables sample
├── .gitignore                     # Git hygiene & privacy filters
├── README.md                      # Project README
└── LICENSE                        # MIT License
```

---

## AI Planning

Detailed development workflow, problem analysis, architecture choices, and 18-stage planning documentation are recorded in [docs/AI_PLANNING.md](docs/AI_PLANNING.md).

---

## AI-Assisted Development

VISITR-AI was constructed using prompt-driven AI development workflows. Engineering directives specified strict application architecture rules (e.g. prohibited libraries, atomic file persistence, state machine guards). AI-generated modular components were systematically validated against automated unit tests. Documented prompts are cataloged in [docs/AI_PROMPTS.md](docs/AI_PROMPTS.md).

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- FFmpeg (for video rendering)
- 4 GB RAM minimum

---

## Requirements

Dependencies are specified in `requirements.txt`:
- `opencv-python>=4.8.0`
- `ultralytics>=8.0.0`
- `insightface>=0.7.3`
- `onnxruntime>=1.16.0`
- `sqlalchemy>=2.0.0`
- `scipy>=1.10.0`
- `numpy>=1.24.0`
- `pillow>=10.0.0`
- `pydantic>=2.0.0`
- `psutil>=5.9.0`
- `pytest>=7.4.0`
- `supervision>=0.18.0`
- `streamlit>=1.28.0`

---

## Installation

```bash
# 1. Clone repository
git clone https://github.com/user/VISITR-AI.git
cd VISITR-AI

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run pre-deployment health check
python scripts/health_check.py
```

---

## Configuration

All system parameters and thresholds are controlled via `config.json`.

---

## Sample config.json

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

## Running with MP4

```bash
# Execute main processing pipeline on MP4 file
python -m app.main --config config.json

# Export empirical execution output artifacts
python scripts/export_sample_output.py

# Run Streamlit Web Analytics Dashboard
streamlit run dashboard.py
```

---

## Running with RTSP

To process a live RTSP IP camera feed:

```bash
python -m app.main --config config.json --rtsp "rtsp://admin:password@192.168.1.100:554/stream1"
```

---

## Database

VISITR-AI uses SQLite with SQLAlchemy ORM comprising 4 core tables:
- `visitors`: `face_id` (PK), `first_seen`, `last_seen`, `total_visits`, `current_status`.
- `embeddings`: `id` (PK), `face_id` (FK), `embedding_data` (BLOB vector).
- `events`: `id` (PK), `face_id` (FK), `track_id`, `event_type`, `timestamp`, `image_path`, `confidence`, `frame_number`.
- `tracks`: `id` (PK), `face_id` (FK), `track_id`, `started_at`, `ended_at`.

---

## Logging

Structured audit logs are appended to `logs/events.log`. Each record contains timestamp, event type (`ENTRY` / `EXIT` / `RECOGNIZED` / `NEW_FACE_REGISTERED`), persistent `face_id`, spatial `track_id`, confidence score, frame number, and image path.

---

## Sample Output

Empirical output artifacts generated from processing `data/sample_video.mp4` are included in `sample_output/`:
- `sample_output/logs/events.log`: Structured audit logs.
- `sample_output/entries/`: Cropped entry face images.
- `sample_output/exits/`: Cropped exit face images.
- `sample_output/database/sample_database_export.txt`: Human-readable SQL database dump.
- `sample_output/database_snapshot.sql`: Full SQLite SQL snapshot dump.
- `sample_output/summary.md`: Execution benchmark summary.

---

## Compute Analysis

Detailed latency measurements and 3 hardware scenarios (Low-End CPU, Mid-Range CPU, GPU) are documented in [docs/COMPUTE_ANALYSIS.md](docs/COMPUTE_ANALYSIS.md).
- **Detection Latency**: **36.41 – 65.69 ms / frame** (YOLOv8n CPU)
- **Tracking Latency**: **1.59 – 2.69 ms / frame** (ByteTrack)
- **Recognition Latency**: **21.88 – 35.42 ms / frame** (ArcFace 512-d)
- **RAM Footprint**: **549.8 MB**

---

## Testing

Run all 26 automated unit and integration tests:

```bash
python -m pytest tests/ -v
```

All 26 test modules pass cleanly (100% pass rate).

---

## Performance

Measured execution telemetry on 360-frame benchmark video:
- **Processing Speed**: **11.1 – 20.3 FPS**
- **Total Pipeline Latency**: **60.71 – 105.71 ms / frame**
- **Memory Footprint**: **549.8 MB RAM**
- **Unique Visitor Count Accuracy**: **100%** (0 false count inflations)

---

## Assumptions

1. Video streams have sufficient lighting and camera framing for face localization.
2. Minimum detected face bounding box size is at least 50x50 pixels.
3. Network RTSP streams provide standard H.264 / H.265 encoded video streams.

---

## Limitations

1. **Extreme Occlusions**: Facial side profile angles exceeding 60 degrees reduce ArcFace embedding confidence below threshold `0.45`.
2. **CPU Scalability at 4K**: High-resolution 4K feeds benefit from higher frame skipping (`skip_frames = 8`) or GPU hardware acceleration.

---

## Deployment

Deploy using Docker Compose:

```bash
# Build and launch engine and web dashboard services
docker-compose up --build -d
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full containerization, volume mounting, and cloud setup details.

---

## Demo Video

- **Video Demonstration Script**: [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)
- **Explanatory Video URL**: `VIDEO LINK REQUIRED BEFORE SUBMISSION`

---

## AI Prompts

A catalog of all development prompts organized into 14 distinct functional prompt categories is documented in [docs/AI_PROMPTS.md](docs/AI_PROMPTS.md).

---

## Interview Preparation

A 24-question technical defense guide explaining algorithm selection, cosine similarity formulas, state machine guards, and failure recoveries is available in [docs/INTERVIEW_GUIDE.md](docs/INTERVIEW_GUIDE.md).

---

## Future Improvements

- TensorRT / CUDA ONNX GPU acceleration providers.
- Multi-camera cross-camera re-identification across spatial camera networks.
- Vector database integration (Milvus / pgvector) for scaling to millions of embeddings.

---

This project is a part of a hackathon run by https://katomaran.com
