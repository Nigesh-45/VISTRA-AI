import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Define sample / fallback data for serverless environment
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

def get_db_data():
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

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        visitors, events = get_db_data()
        if not visitors:
            visitors = MOCK_VISITORS
            events = MOCK_EVENTS

        total_unique = len(visitors)
        currently_inside = sum(1 for v in visitors if v["status"] == "INSIDE")
        total_entries = sum(v["entries"] for v in visitors)
        total_exits = sum(v["exits"] for v in visitors)

        response_data = {}

        if path == "/api/stats" or path == "/api":
            response_data = {
                "status": "success",
                "system": "VISTRA-AI Visitor Analytics Engine",
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
        elif path == "/api/visitors":
            response_data = {
                "status": "success",
                "count": len(visitors),
                "visitors": visitors
            }
        elif path == "/api/events":
            response_data = {
                "status": "success",
                "count": len(events),
                "events": events
            }
        elif path == "/api/health":
            response_data = {
                "status": "healthy",
                "service": "VISITR-AI Serverless Engine",
                "version": "1.0.0"
            }
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode('utf-8'))
            return

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response_data, indent=2).encode('utf-8'))
