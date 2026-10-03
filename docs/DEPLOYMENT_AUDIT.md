# Deployment Audit Report - VISITR-AI

## 1. Current Architecture Overview

VISITR-AI is a modular computer vision application designed for persistent visitor tracking, auto-registration, and unique analytics.

- **Application Entry Point**: `app/main.py` (CLI runner) and `dashboard.py` (Streamlit web dashboard).
- **Python Version**: Python 3.11.15.
- **Core Dependencies**: `ultralytics` (YOLOv8), `insightface` (ArcFace 512-d), `supervision` (ByteTrack), `opencv-python`, `sqlalchemy` (SQLite ORM), `pytest`, `streamlit`, `psutil`.
- **Model Dependencies**: `yolov8n.pt` (YOLO face/object detection) and `buffalo_sc` ONNX models (InsightFace face detection & ArcFace feature extraction).
- **Database**: SQLite database stored at `database/visitors.db`.
- **Logging**: Structured events logged to `logs/events.log`.
- **Image Storage**: Atomic cropped face images stored in `logs/entries/YYYY-MM-DD/` and `logs/exits/YYYY-MM-DD/`.
- **Stream Inputs**: MP4 video files (`FileVideoSource`) and live RTSP camera feeds (`RTSPVideoSource`).

---

## 2. Deployment Audit Parameters

| Audit Domain | Parameter / Requirement | Deployment Status & Assessment |
| :--- | :--- | :--- |
| **Deployment Blockers** | Missing dependencies / System libraries | `ffmpeg`, `libgl1`, `libglib2.0-0` required in Linux container base for OpenCV and video writing. |
| **Dependency Risks** | Version mismatches / C++ build requirements | Pre-compiled wheels for `onnxruntime`, `opencv-python-headless`, and `sqlalchemy` eliminate host build tools requirement. |
| **Model Loading** | Local directory & cache paths | YOLO model `yolov8n.pt` downloaded to working directory; InsightFace models cached in `~/.insightface/`. |
| **Filesystem & Storage** | Persistent host mounts | Directories `database/`, `logs/`, `output/`, `models/` must be mounted as host volumes. |
| **Database Requirements** | Concurrent read/write safety | SQLite in WAL/read-only URI mode (`file:visitors.db?mode=ro`) for dashboard queries. |
| **Environment Variables** | Configuration overrides | `CONFIG_PATH`, `INPUT_TYPE`, `INPUT_SOURCE`, `RTSP_URL`, `DATABASE_URL`, `SKIP_FRAMES`, `SIMILARITY_THRESHOLD`. |
| **Ports** | Exposed service ports | Streamlit Web Dashboard: Port `8501`. |
| **CPU/GPU Telemetry** | Hardware requirements | Minimum 2 CPU cores, 4 GB RAM. Optional NVIDIA CUDA GPU via ONNX Runtime CUDA provider. |
| **Security & Privacy** | Biometric data & Git hygiene | Real face images, `visitors.db`, `.env`, and `events.log` filtered via `.gitignore`. |

---

## 3. Recommended Deployment Architecture

```
                       Host Environment / Docker Container
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│   ┌─────────────────────┐                  ┌───────────────────────────┐   │
│   │     VISITR-AI       │                  │    Streamlit Dashboard    │   │
│   │    (app/main.py)    │                  │      (dashboard.py)       │   │
│   └──────────┬──────────┘                  └─────────────┬─────────────┘   │
│              │                                           │                 │
│              ▼                                           ▼                 │
│      ┌───────────────┐                            ┌───────────────┐        │
│      │  Volume Mount │                            │  Read-Only    │        │
│      │  database/    │ ◄───────────────────────── │  URI Mode     │        │
│      └───────────────┘                            └───────────────┘        │
│              │                                                             │
│              ├─────────────────► logs/ (events.log, entries/, exits/)      │
│              └─────────────────► output/ (processed_video.mp4)           │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```
