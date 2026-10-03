FROM python:3.11-slim

# Prevent Python from writing bytecode and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CONFIG_PATH=config.json

WORKDIR /app

# Install system media and build dependencies for OpenCV and FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY config.json .
COPY dashboard.py .
COPY README.md .

# Create persistent runtime directory structure
RUN mkdir -p data models logs/entries logs/exits database output/processed
RUN chmod +x scripts/start_render.sh

# Default command runs the main computer vision pipeline
CMD ["python", "-m", "app.main", "--config", "config.json"]
