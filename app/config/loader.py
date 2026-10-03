"""Configuration loader module for VISITR-AI.

Loads settings from config.json and allows environment variable overrides for containerized deployment.
"""

import json
import os
from typing import Any, Dict
from pydantic import BaseModel, Field


class InputConfig(BaseModel):
    type: str = "file"
    source: str = "data/sample_video.mp4"
    rtsp_reconnect_delay: float = 3.0
    rtsp_max_retries: int = 10


class DetectionConfig(BaseModel):
    model: str = "yolov8n.pt"
    confidence: float = 0.50
    iou: float = 0.45
    skip_frames: int = 5


class TrackingConfig(BaseModel):
    tracker: str = "bytetrack"
    max_age: int = 30
    track_thresh: float = 0.50


class RecognitionConfig(BaseModel):
    model: str = "buffalo_sc"
    similarity_threshold: float = 0.45
    min_face_size: int = 50


class EventsConfig(BaseModel):
    exit_timeout_frames: int = 30
    save_images: bool = True
    entry_directory: str = "logs/entries"
    exit_directory: str = "logs/exits"
    event_log: str = "logs/events.log"


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///database/visitors.db"


class OutputConfig(BaseModel):
    save_video: bool = True
    path: str = "output/processed/processed_video.mp4"


class AppConfig(BaseModel):
    input: InputConfig = Field(default_factory=InputConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    recognition: RecognitionConfig = Field(default_factory=RecognitionConfig)
    events: EventsConfig = Field(default_factory=EventsConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def load_config(config_path: str = "config.json") -> AppConfig:
    """Load configuration from JSON file and apply environment variable overrides."""
    env_path = os.getenv("CONFIG_PATH", config_path)
    config = AppConfig()

    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            config = AppConfig(**data)
        except Exception as e:
            print(f"[Config] Warning: Error parsing {env_path}: {e}. Using default baseline settings.")

    # Environment Variable Overrides for Container Deployment
    if os.getenv("INPUT_TYPE"):
        config.input.type = os.getenv("INPUT_TYPE")
    if os.getenv("INPUT_SOURCE"):
        config.input.source = os.getenv("INPUT_SOURCE")
    if os.getenv("RTSP_URL"):
        config.input.type = "rtsp"
        config.input.source = os.getenv("RTSP_URL")
    if os.getenv("DATABASE_URL"):
        config.database.url = os.getenv("DATABASE_URL")
    if os.getenv("DETECTION_SKIP_FRAMES"):
        try:
            config.detection.skip_frames = int(os.getenv("DETECTION_SKIP_FRAMES"))
        except ValueError:
            pass
    if os.getenv("SIMILARITY_THRESHOLD"):
        try:
            config.recognition.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD"))
        except ValueError:
            pass
    if os.getenv("EXIT_TIMEOUT_FRAMES"):
        try:
            config.events.exit_timeout_frames = int(os.getenv("EXIT_TIMEOUT_FRAMES"))
        except ValueError:
            pass

    return config
