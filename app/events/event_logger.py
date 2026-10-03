"""Structured event logger module for logging application events to logs/events.log."""

from datetime import datetime, timezone
import json
import logging
import os
from typing import Any, Dict, Optional


class EventLogger:
    """Centralized logger writing structured event logs to logs/events.log and console."""

    def __init__(self, log_file_path: str = "logs/events.log", level: int = logging.INFO):
        self.log_file_path = log_file_path
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        self.logger = logging.getLogger("VISITR_AI_EVENTS")
        self.logger.setLevel(level)
        self.logger.handlers.clear()

        # File Handler
        fh = logging.FileHandler(log_file_path, encoding="utf-8")
        fh.setLevel(level)

        # Console Handler
        ch = logging.StreamHandler()
        ch.setLevel(level)

        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def log_event(
        self,
        event_name: str,
        face_id: Optional[str] = None,
        track_id: Optional[int] = None,
        confidence: Optional[float] = None,
        level: str = "INFO",
        **kwargs: Any
    ) -> None:
        """Format and write structured log entry."""
        log_parts = [f"EVENT={event_name}"]
        if face_id:
            log_parts.append(f"face_id={face_id}")
        if track_id is not None:
            log_parts.append(f"track_id={track_id}")
        if confidence is not None:
            log_parts.append(f"confidence={confidence:.2f}")

        if "metadata" in kwargs and isinstance(kwargs["metadata"], dict):
            log_parts.append(f"metadata={json.dumps(kwargs['metadata'])}")
        elif kwargs:
            log_parts.append(f"metadata={json.dumps(kwargs)}")

        msg = " | ".join(log_parts)
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, msg)
