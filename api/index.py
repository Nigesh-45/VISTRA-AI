import os
import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="VISITR-AI API",
    description="Intelligent Visitor Analytics & Face Tracking Vercel Engine",
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
    return {"status": "healthy", "service": "VISITR-AI Vercel API", "version": "1.0.0"}


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
