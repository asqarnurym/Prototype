import json
from pathlib import Path

import pytest

from pipeline.exporters.json_export import _clean_visual_events, export_timeline_json
from pipeline.visual.scene_indexer import build_timeline_visual_events


def test_clean_visual_events():
    """Test cleaning of visual events for export."""
    raw_events = [
        {
            "event_time": 10.5,
            "type": "scene_change",
            "description_text": "A person explaining",
            "internal_path": "/tmp/frame_001.jpg",  # Should be removed
            "score": 0.95,  # Should be removed
        }
    ]

    cleaned = _clean_visual_events(raw_events)

    assert len(cleaned) == 1
    assert "event_time" in cleaned[0]
    assert "type" in cleaned[0]
    assert "description_text" in cleaned[0]
    assert "internal_path" not in cleaned[0]
    assert "score" not in cleaned[0]


def test_export_timeline_json(tmp_path):
    """Test full JSON export logic."""
    output_file = tmp_path / "test_timeline.json"
    timeline = {
        "language": "en",
        "detected_language": "en",
        "segments": [{"start": 0, "end": 1, "text": "Hello"}],
        "words": [{"word": "Hello", "start": 0, "end": 0.5}],
        "visual_events": [{"event_time": 0.5, "type": "scene", "description_text": "desc"}],
    }

    path = export_timeline_json(timeline, str(output_file))

    assert Path(path).exists()

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["language"] == "en"
    assert data["detected_language"] == "en"
    assert len(data["segments"]) == 1
    assert len(data["visual_events"]) == 1
    assert "description_text" in data["visual_events"][0]


def test_build_timeline_visual_events_from_scene_index():
    """Scene index entries should be converted to the public timeline schema."""
    scene_index = [
        {
            "scene_id": 0,
            "time": 12.25,
            "description": "A chart appears on the slide.",
            "tts_cached": False,
        }
    ]

    visual_events = build_timeline_visual_events(scene_index)

    assert visual_events == [
        {
            "event_time": 12.25,
            "type": "scene_change",
            "description_text": "A chart appears on the slide.",
        }
    ]


def test_clean_visual_events_rejects_scene_index_shape():
    """Exporter must fail loudly if scene_index objects are passed directly."""
    scene_index = [{"time": 12.25, "description": "A chart appears on the slide."}]

    with pytest.raises(ValueError, match="build_timeline_visual_events"):
        _clean_visual_events(scene_index)
