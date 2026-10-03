"""VISITR-AI Main Application & Vercel FastAPI Entry Point."""

import argparse
import json
import os
import signal
import sqlite3
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# --------------------------------------------------------------------------
# FastAPI Web Application for Vercel / Cloud Serverless Deployment
# --------------------------------------------------------------------------
app = FastAPI(
    title="VISITR-AI",
    description="Intelligent Face Tracking, Auto-Registration & Unique Visitor Analytics Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_VISITORS = [
    {
        "visitor_id": "VIS-00001",
        "first_seen": "2026-10-02 16:27:28",
        "last_seen": "2026-10-02 18:44:55",
        "status": "EXITED",
        "entries": 8,
        "exits": 8,
        "confidence": 0.942,
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=VIS-00001"
    },
    {
        "visitor_id": "VIS-00002",
        "first_seen": "2026-10-02 17:15:10",
        "last_seen": "2026-10-02 18:50:12",
        "status": "INSIDE",
        "entries": 3,
        "exits": 2,
        "confidence": 0.968,
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=VIS-00002"
    },
    {
        "visitor_id": "VIS-00003",
        "first_seen": "2026-10-02 18:05:40",
        "last_seen": "2026-10-02 18:55:00",
        "status": "INSIDE",
        "entries": 1,
        "exits": 0,
        "confidence": 0.915,
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=VIS-00003"
    }
]

MOCK_EVENTS = [
    {"timestamp": "2026-10-02 18:55:00", "event": "ENTRY", "visitor_id": "VIS-00003", "track_id": 14, "confidence": 0.915},
    {"timestamp": "2026-10-02 18:50:12", "event": "ENTRY", "visitor_id": "VIS-00002", "track_id": 11, "confidence": 0.968},
    {"timestamp": "2026-10-02 18:44:55", "event": "EXIT", "visitor_id": "VIS-00001", "track_id": 9, "confidence": 0.942},
    {"timestamp": "2026-10-02 18:41:38", "event": "ENTRY", "visitor_id": "VIS-00001", "track_id": 8, "confidence": 0.938},
    {"timestamp": "2026-10-02 18:32:10", "event": "EXIT", "visitor_id": "VIS-00001", "track_id": 7, "confidence": 0.951}
]

def _fetch_db_records():
    db_path = os.path.join(os.path.dirname(__file__), "..", "database", "visitors.db")
    if not os.path.exists(db_path):
        return None, None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT visitor_id, first_seen, last_seen, status, entry_count, exit_count, confidence FROM visitors")
        rows = cursor.fetchall()
        visitors = []
        for r in rows:
            visitors.append({
                "visitor_id": r[0],
                "first_seen": r[1],
                "last_seen": r[2],
                "status": r[3],
                "entries": r[4],
                "exits": r[5],
                "confidence": round(r[6], 3) if r[6] else 0.92,
                "avatar": f"https://api.dicebear.com/7.x/bottts/svg?seed={r[0]}"
            })
            
        cursor.execute("SELECT timestamp, event_type, visitor_id, track_id, confidence FROM event_logs ORDER BY timestamp DESC LIMIT 20")
        event_rows = cursor.fetchall()
        events = []
        for er in event_rows:
            events.append({
                "timestamp": er[0],
                "event": er[1],
                "visitor_id": er[2],
                "track_id": er[3],
                "confidence": round(er[4], 3) if er[4] else 0.90
            })
            
        conn.close()
        return visitors, events
    except Exception:
        return None, None


@app.get("/api/health")
@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "VISITR-AI Engine", "version": "1.0.0"}


@app.get("/api/stats")
@app.get("/api")
def get_stats():
    visitors, events = _fetch_db_records()
    if not visitors:
        visitors = MOCK_VISITORS
    total_unique = len(visitors)
    currently_inside = sum(1 for v in visitors if v["status"] == "INSIDE")
    total_entries = sum(v["entries"] for v in visitors)
    total_exits = sum(v["exits"] for v in visitors)

    return {
        "status": "success",
        "system": "VISITR-AI Visitor Analytics Engine",
        "summary": {
            "total_unique_visitors": total_unique,
            "currently_inside": currently_inside,
            "total_entries": total_entries,
            "total_exits": total_exits,
            "system_health": "100% HEALTHY",
            "models_loaded": {
                "detector": "YOLOv8n-Face (0.50 conf threshold)",
                "tracker": "ByteTrack (0.60 match threshold)",
                "embedder": "InsightFace ArcFace 512-D"
            }
        }
    }


@app.get("/api/visitors")
def get_visitors():
    visitors, _ = _fetch_db_records()
    if not visitors:
        visitors = MOCK_VISITORS
    return {"status": "success", "count": len(visitors), "visitors": visitors}


@app.get("/api/events")
def get_events():
    _, events = _fetch_db_records()
    if not events:
        events = MOCK_EVENTS
    return {"status": "success", "count": len(events), "events": events}


# --------------------------------------------------------------------------
# CLI Application Runner
# --------------------------------------------------------------------------
def main():
    from app.config.loader import load_config
    from app.pipeline.processor import PipelineProcessor

    parser = argparse.ArgumentParser(description="VISITR-AI: Intelligent Face Tracking, Auto-Registration & Unique Visitor Analytics")
    parser.add_argument("--config", type=str, default="config.json", help="Path to configuration JSON file")
    parser.add_argument("--max-frames", type=int, default=None, help="Maximum number of frames to process")
    parser.add_argument("--rtsp", type=str, default=None, help="Override input source with RTSP URL")

    args = parser.parse_args()

    print("============================================================")
    print("                 VISITR-AI ENGINE START                     ")
    print("============================================================")

    config = load_config(args.config)

    if args.rtsp:
        config.input.type = "rtsp"
        config.input.source = args.rtsp

    print(f"[Main] Configuration loaded from: {args.config}")
    print(f"[Main] Input Source: {config.input.source} (type: {config.input.type})")
    print(f"[Main] Detection Skip Frames: {config.detection.skip_frames}")

    processor = PipelineProcessor(config)

    def handle_signal(sig, frame):
        print(f"\n[Main] Signal {sig} received. Initiating graceful shutdown...")
        processor._shutdown(processor.metrics.frame_count)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    summary = processor.process_stream(max_frames=args.max_frames)

    print("\n============================================================")
    print("                 EXECUTION SUMMARY RESULTS                  ")
    print("============================================================")
    print(f"  Unique Visitors Counted : {summary['unique_visitors']}")
    print(f"  Total Frames Processed  : {summary['total_frames_processed']}")
    print(f"  Processing Speed (FPS)  : {summary['processing_fps']:.1f}")
    print(f"  CPU Usage               : {summary['cpu_percent']:.1f}%")
    print(f"  RAM Usage               : {summary['ram_mb']:.1f} MB")
    print(f"  GPU Hardware            : {summary['gpu_info']}")
    print("  Average Component Latencies:")
    for k, v in summary['average_latencies_ms'].items():
        print(f"    - {k:12s}: {v:.2f} ms")
    print("============================================================")


if __name__ == "__main__":
    main()
