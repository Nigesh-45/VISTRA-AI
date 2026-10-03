#!/bin/bash
set -e

echo "=========================================="
echo "  Starting VISITR-AI Web Service on Render"
echo "=========================================="

# Ensure data directory exists
mkdir -p data logs/entries logs/exits database output

# Generate sample video if missing
if [ ! -f "data/sample_video.mp4" ]; then
    echo "[RENDER] Generating synthetic sample video..."
    python scripts/generate_sample_video.py || true
fi

# Start background pipeline processor
echo "[RENDER] Starting VISITR-AI pipeline in background..."
python -m app.main --config config.json &

# Read port assigned by Render (default 8501)
TARGET_PORT="${PORT:-8501}"
echo "[RENDER] Launching Streamlit Dashboard on port ${TARGET_PORT}..."

exec streamlit run dashboard.py \
    --server.port="${TARGET_PORT}" \
    --server.address="0.0.0.0" \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
