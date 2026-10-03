import os
import json
import pytest
from app.config.loader import load_config, AppConfig


def test_default_config():
    config = load_config("non_existent_config.json")
    assert isinstance(config, AppConfig)
    assert config.detection.skip_frames == 5
    assert config.recognition.similarity_threshold == 0.45


def test_custom_config(tmp_path):
    cfg_file = tmp_path / "custom_config.json"
    data = {
        "detection": {"skip_frames": 10, "confidence": 0.60},
        "recognition": {"similarity_threshold": 0.50}
    }
    cfg_file.write_text(json.dumps(data))

    config = load_config(str(cfg_file))
    assert config.detection.skip_frames == 10
    assert config.detection.confidence == 0.60
    assert config.recognition.similarity_threshold == 0.50
