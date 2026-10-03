# VISITR-AI Deployment & Productionization Guide

This document provides step-by-step instructions for deploying VISITR-AI locally, within Docker containers, and in cloud environments.

---

## 1. Local Environment Deployment

### Prerequisites:
- Python 3.11+
- FFmpeg (for video rendering)
- 4 GB RAM minimum

### Step-by-Step Setup:

```bash
# 1. Clone repository
git clone https://github.com/user/VISITR-AI.git
cd VISITR-AI

# 2. Create virtual environment
python -m venv .venv

# Activate on Linux / macOS:
source .venv/bin/activate
# Activate on Windows:
.venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Perform environment health check
python scripts/health_check.py

# 5. Generate benchmark sample video
python scripts/generate_sample_video.py

# 6. Execute main pipeline on MP4
python -m app.main --config config.json

# 7. Launch Streamlit Web Analytics Dashboard
streamlit run dashboard.py
```

---

## 2. Docker Containerized Deployment

### Option A: Using Docker Compose (Recommended)

```bash
# Build and start engine + dashboard services in background
docker-compose up --build -d

# View real-time container logs
docker-compose logs -f

# Check container readiness status
docker-compose ps

# Restart services
docker-compose restart

# Stop container services
docker-compose down
```

### Option B: Standalone Docker CLI

```bash
# Build Docker image
docker build -t visitr-ai:latest .

# Run standalone container with volume mounts
docker run -d \
  --name visitr_ai_instance \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/database:/app/database \
  -v $(pwd)/output:/app/output \
  -e CONFIG_PATH=config.json \
  visitr-ai:latest
```

---

## 3. Persistent Volume Storage

The following host directories MUST be volume-mounted to survive container restarts:

| Host Path | Container Path | Description | Preserved Data |
| :--- | :--- | :--- | :--- |
| `./database/` | `/app/database/` | SQLite database | Registered visitors, embeddings, events, tracks |
| `./logs/` | `/app/logs/` | Audit logs & face crops | `events.log`, `logs/entries/`, `logs/exits/` |
| `./output/` | `/app/output/` | Video renderings | `output/processed/processed_video.mp4` |
| `./models/` | `/app/models/` | Local model weights | `yolov8n.pt` and InsightFace ONNX models |

---

## 4. Environment Configuration Overrides

Set the following environment variables in `.env` or container settings:

```env
# Input Configuration
INPUT_TYPE=file
INPUT_SOURCE=data/sample_video.mp4

# RTSP Stream Override (For Live Demo)
RTSP_URL=rtsp://admin:password@192.168.1.100:554/stream1

# Database Configuration
DATABASE_URL=sqlite:///database/visitors.db

# Performance & Threshold Overrides
DETECTION_SKIP_FRAMES=5
SIMILARITY_THRESHOLD=0.45
EXIT_TIMEOUT_FRAMES=30
```

---

## 5. RTSP Camera Setup for Interview Testing

To connect a live RTSP IP camera feed during an interview or live demo:

1. Update `config.json` or set `RTSP_URL`:
   ```json
   {
     "input": {
       "type": "rtsp",
       "source": "rtsp://admin:password@192.168.1.100:554/stream1"
     }
   }
   ```
2. Or pass `--rtsp` argument directly via CLI:
   ```bash
   python -m app.main --config config.json --rtsp "rtsp://admin:password@192.168.1.100:554/stream1"
   ```
3. **Resilience**: The system runs a background thread with non-blocking auto-reconnect logic, preventing application crashes during network jitter.

---

## 6. Pre-Deployment Health Diagnostic

Run the automated self-diagnostic check before pushing to production:

```bash
python scripts/health_check.py
```

Expected output:
```
============================================================
           VISITR-AI PRE-DEPLOYMENT HEALTH CHECK            
============================================================
[1/5] Checking Python Dependencies...
  [PASS] cv2: Available
  [PASS] ultralytics: Available
  [PASS] insightface: Available
  [PASS] sqlalchemy: Available
  [PASS] pydantic: Available
  [PASS] psutil: Available

[2/5] Checking Configuration Loader...
  [PASS] config.json: Valid (Input: data/sample_video.mp4, Skip: 5)

[3/5] Checking Database Initialization...
  [PASS] SQLite Engine & ORM: Operational

[4/5] Checking Filesystem Directory Permissions...
  [PASS] Directory data                : Writable
  [PASS] Directory database            : Writable
  [PASS] Directory logs/entries        : Writable
  [PASS] Directory logs/exits          : Writable
  [PASS] Directory output/processed    : Writable
  [PASS] Directory models              : Writable

[5/5] Checking Model Weights...
  [PASS] YOLO Weight File (yolov8n.pt): Present locally

============================================================
           HEALTH CHECK VERDICT: 100% HEALTHY               
============================================================
```

---

## 7. Troubleshooting Guide

### Issue A: InsightFace Model Download Timeout
- **Symptom**: `InsightFace engine fallback to synthetic feature extractor`.
- **Solution**: Ensure internet access for initial download (~20 MB) or manually place `buffalo_sc` weights in `~/.insightface/models/buffalo_sc/`.

### Issue B: SQLite Database Locked Error
- **Symptom**: `sqlite3.OperationalError: database is locked`.
- **Solution**: The Streamlit dashboard (`dashboard.py`) accesses SQLite using read-only URI mode (`file:visitors.db?mode=ro`). Verify read-only connection string.

### Issue C: OpenCV Headless Video Writer Failures
- **Symptom**: `VideoWriter` fails to write output MP4 frames.
- **Solution**: Install system media libraries: `apt-get install -y ffmpeg libgl1 libglib2.0-0`.
