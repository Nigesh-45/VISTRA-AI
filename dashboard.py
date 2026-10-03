"""Streamlit Dashboard for VISITR-AI Real-time Analytics & System Monitoring."""

import json
import os
import sqlite3
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="VISITR-AI Analytics Dashboard",
    page_icon="👁️",
    layout="wide"
)

st.title("👁️ VISITR-AI: Intelligent Face Analytics Dashboard")
st.caption("Real-time Face Tracking, Auto-Registration & Unique Visitor Telemetry")

DB_PATH = "database/visitors.db"
LOG_PATH = "logs/events.log"
OUTPUT_VIDEO = "output/processed/processed_video.mp4"
ENTRIES_DIR = "logs/entries"
EXITS_DIR = "logs/exits"


def get_db_metrics():
    """Fetch analytics metrics from SQLite database."""
    if not os.path.exists(DB_PATH):
        return 0, 0, 0, 0, []

    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM visitors")
        unique_cnt = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM visitors WHERE current_status = 'INSIDE'")
        inside_cnt = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM events WHERE event_type = 'ENTRY'")
        entries_cnt = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM events WHERE event_type = 'EXIT'")
        exits_cnt = c.fetchone()[0]

        c.execute("SELECT id, face_id, track_id, event_type, timestamp, confidence, image_path FROM events ORDER BY timestamp DESC LIMIT 15")
        recent_events = c.fetchall()

        conn.close()
        return unique_cnt, inside_cnt, entries_cnt, exits_cnt, recent_events
    except Exception as e:
        return 0, 0, 0, 0, []


# Sidebar Controls
st.sidebar.header("⚙️ Control & Configuration")
st.sidebar.info("Model: YOLOv8 + InsightFace ArcFace")
st.sidebar.markdown("**Input Mode**: File (MP4) / RTSP Camera")

# Top KPI Metric Cards
col1, col2, col3, col4 = st.columns(4)
unique_cnt, inside_cnt, entries_cnt, exits_cnt, recent_events = get_db_metrics()

col1.metric("Unique Visitors", unique_cnt, delta="Distinct Persistent IDs")
col2.metric("Currently Inside", inside_cnt, delta="Active Session")
col3.metric("Total Entry Events", entries_cnt, delta="Atomic Entries")
col4.metric("Total Exit Events", exits_cnt, delta="Atomic Exits")

st.divider()

# Main Layout Split: Video Output & Recent Events
left_col, right_col = st.columns([3, 2])

with left_col:
    st.subheader("📹 Processed Video Stream & HUD")
    if os.path.exists(OUTPUT_VIDEO):
        st.video(OUTPUT_VIDEO)
    else:
        st.info("No processed video available yet. Run main pipeline to render output video.")

with right_col:
    st.subheader("📋 Recent Event Stream")
    if recent_events:
        for ev in recent_events:
            ev_id, face_id, track_id, ev_type, ts, conf, img_p = ev
            badge_color = "🟢" if ev_type == "ENTRY" else "🔴"
            st.markdown(f"**{badge_color} {ev_type}** | `{face_id}` | Track `{track_id}` | Conf: `{conf:.2f}`")
            st.caption(f"Time: {ts} | Image: `{img_p}`")
            st.markdown("---")
    else:
        st.info("No event records found in database.")

st.divider()

# Image Gallery Section
st.subheader("🖼️ Saved Entry & Exit Face Crops")
gallery_tabs = st.tabs(["Entry Crops", "Exit Crops"])

with gallery_tabs[0]:
    if os.path.exists(ENTRIES_DIR):
        img_files = []
        for root, _, files in os.walk(ENTRIES_DIR):
            for f in files:
                if f.endswith(".jpg"):
                    img_files.append(os.path.join(root, f))
        if img_files:
            cols = st.columns(min(6, len(img_files)))
            for i, img_path in enumerate(img_files[:12]):
                with cols[i % len(cols)]:
                    img = Image.open(img_path)
                    st.image(img, caption=os.path.basename(img_path), use_container_width=True)
        else:
            st.caption("No entry crop images saved yet.")

with gallery_tabs[1]:
    if os.path.exists(EXITS_DIR):
        img_files = []
        for root, _, files in os.walk(EXITS_DIR):
            for f in files:
                if f.endswith(".jpg"):
                    img_files.append(os.path.join(root, f))
        if img_files:
            cols = st.columns(min(6, len(img_files)))
            for i, img_path in enumerate(img_files[:12]):
                with cols[i % len(cols)]:
                    img = Image.open(img_path)
                    st.image(img, caption=os.path.basename(img_path), use_container_width=True)
        else:
            st.caption("No exit crop images saved yet.")
