# 3-5 Minute Video Demonstration Script - VISITR-AI

> [!IMPORTANT]
> **VIDEO LINK STATUS**: `VIDEO LINK REQUIRED BEFORE SUBMISSION`
> 
> This document provides the complete video demonstration recording script required for submitting the Loom or YouTube explanatory video for the Katomaran Hackathon.

---

## Video Metadata & Target Duration
- **Target Duration**: 3 to 5 minutes (300 seconds)
- **Target Audience**: Katomaran Hackathon Technical Evaluators & Senior Engineers
- **Demonstrator**: Hackathon Developer / Presenter

---

## Step-by-Step Recording Script & Timeline

### Section 1: Project Overview & Problem Statement (0:00 - 0:30)
- **Action**: Display `README.md` and repository overview.
- **Narrator**:
  > "Hello evaluators! Welcome to **VISITR-AI**, an intelligent computer vision system built for Katomaran Hackathon. Traditional video analytics software suffers from identity fragmentation—when a visitor is occluded or leaves the camera view, traditional trackers assign a new ID, inflating unique visitor counts and corrupting analytics. VISITR-AI solves this by decoupling temporary spatial track IDs from persistent facial identities using ArcFace embeddings and SQLite persistence."

### Section 2: Architecture & Technology Stack (0:30 - 1:00)
- **Action**: Display the system architecture flow diagram in `docs/ARCHITECTURE.md`.
- **Narrator**:
  > "Here is our architecture. Video frames flow from MP4 files or RTSP streams into a Frame Manager. YOLOv8 localizes face bounding boxes, Supervision ByteTrack maintains continuous spatial tracks, and InsightFace ArcFace extracts 512-dimensional feature vectors. Cosine similarity matching classifies faces as known or unknown. Unrecognized faces trigger auto-registration with best-frame selection, assigning a permanent Face ID (`VIS-00001`). A state machine guarantees exactly-once ENTRY and EXIT events committed to SQLite DB, `events.log`, and image crops."

### Section 3: Configuration & System Setup (1:00 - 1:15)
- **Action**: Open `config.json` in VS Code.
- **Narrator**:
  > "System thresholds are fully configurable via `config.json`. We specify `skip_frames: 5` to optimize CPU throughput, detection confidence `0.50`, recognition cosine similarity threshold `0.45`, and `exit_timeout_frames: 30`."

### Section 4: Application Startup & Execution (1:15 - 1:45)
- **Action**: Run `python -m app.main --config config.json` in the terminal.
- **Narrator**:
  > "Let's launch the pipeline against `data/sample_video.mp4`. Notice the clean console initialization logging detector, ByteTrack tracker, InsightFace model, and existing database gallery. The pipeline processes 360 frames seamlessly."

### Section 5: Face Detection & Spatial Tracking (1:45 - 2:05)
- **Action**: Show processing logs or open annotated output video `output/processed/processed_video.mp4`.
- **Narrator**:
  > "As frames process, YOLO detects face bounding boxes, and ByteTrack assigns a continuous `track_id` (e.g. `track_id = 1`). Notice how spatial continuity is maintained across frames."

### Section 6: Unknown Face Quality Evaluation & Auto-Registration (2:05 - 2:25)
- **Action**: Highlight `EVENT=NEW_FACE_REGISTERED` log line in console.
- **Narrator**:
  > "When an unknown target enters, our auto-registration engine buffers candidate crops over 3 frames. It evaluates sharpness, confidence, and size, selecting the best frame crop and assigning persistent Face ID `VIS-00001`."

### Section 7: Persistent Face ID vs Tracker ID (2:25 - 2:45)
- **Action**: Point to log lines showing `face_id=VIS-00001` paired with `track_id=1` and later `track_id=4`.
- **Narrator**:
  > "Here is the critical distinction: `track_id` is temporary spatial tracking assigned by ByteTrack, while `face_id` is persistent across visits. Even when a target gets a new `track_id = 4`, ArcFace matching correctly resolves them back to `VIS-00001`."

### Section 8: Entry Event Detection & Image Crop (2:45 - 3:00)
- **Action**: Show `EVENT=ENTRY` log line and open saved entry image in `logs/entries/`.
- **Narrator**:
  > "Upon initial recognition, the Visitor State Machine transitions from `OUTSIDE` to `INSIDE`, logging an `ENTRY` event and saving an atomic cropped face JPEG to `logs/entries/` with ISO timestamp."

### Section 9: Visitor Re-identification (3:00 - 3:20)
- **Action**: Point out re-identification log event `EVENT=RECOGNIZED` with similarity score `0.98`.
- **Narrator**:
  > "When the visitor re-appears later in the stream under a new spatial track, ArcFace calculates cosine similarity (`0.98 >= 0.45`), recognizing `VIS-00001`. Their `total_visits` counter increments, but unique visitor count remains exactly 1."

### Section 10: Exit Event Detection & Image Crop (3:20 - 3:35)
- **Action**: Show `EVENT=EXIT` log line and open saved exit image in `logs/exits/`.
- **Narrator**:
  > "When the target is inactive for > 30 frames, the state machine triggers an `EXIT` event, saving the final exit crop and transitioning visitor state to `OUTSIDE`."

### Section 11: Structured Audit Logs (`events.log`) (3:35 - 3:50)
- **Action**: Open `logs/events.log`.
- **Narrator**:
  > "All events are recorded in structured format inside `logs/events.log`, containing ISO timestamps, event types, Face IDs, Track IDs, confidences, frame numbers, and image paths."

### Section 12: Database Records Evidence (3:50 - 4:10)
- **Action**: Open `sample_output/database/sample_database_export.txt` or query SQLite via DB viewer.
- **Narrator**:
  > "Here are the database records in `visitors.db`. Table `visitors` stores persistent identities; `embeddings` stores 512-d ArcFace BLOB vectors; `events` logs every entry/exit audit record; and `tracks` logs spatial track duration."

### Section 13: Unique Visitor Counting Query (4:10 - 4:25)
- **Action**: Highlight the summary count output in terminal or DB.
- **Narrator**:
  > "Querying `count_unique_visitors()` returns `1`. Despite multiple entry and exit events across different track IDs, our decoupled architecture guarantees zero unique count inflation!"

### Section 14: Automated Test Suite & Health Check (4:25 - 4:40)
- **Action**: Run `python -m pytest` in terminal showing 26/26 tests passing.
- **Narrator**:
  > "Our system includes 26 automated unit and integration tests covering detection, tracking, matching, registration, re-identification, state machine transitions, and database operations. All 26 tests pass cleanly."

### Section 15: Streamlit Web Dashboard (4:40 - 4:55)
- **Action**: Display Streamlit dashboard running via `streamlit run dashboard.py`.
- **Narrator**:
  > "We also built an interactive Streamlit dashboard (`dashboard.py`) providing live unique visitor KPIs, total visit charts, entry/exit logs, and image crop carousels."

### Section 16: Final Summary & Katomaran Conclusion (4:55 - 5:00)
- **Action**: Return to `README.md` bottom line.
- **Narrator**:
  > "In summary, VISITR-AI is a production-ready, modular, reproducible, and fully verified computer vision application. Thank you to the Katomaran Hackathon team!"
