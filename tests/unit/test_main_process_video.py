import json
from pathlib import Path

import pytest

import main as main_module
from core.config import settings
from core.job_state import update_job_meta


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    original_output = settings.output_dir
    original_temp = settings.temp_dir

    output_dir = tmp_path / "output"
    temp_dir = tmp_path / "temp"
    output_dir.mkdir()
    temp_dir.mkdir()

    monkeypatch.setattr(settings, "output_dir", output_dir)
    monkeypatch.setattr(settings, "temp_dir", temp_dir)

    yield tmp_path

    settings.output_dir = original_output
    settings.temp_dir = original_temp


def _write_summary(*, scenes, job_id, language, output_path, transcript_segments=None):
    Path(output_path).write_text(
        json.dumps(
            {
                "job_id": job_id,
                "language": language,
                "summary_version": 2,
                "summary_points": [f"{len(scenes)} scenes"],
                "chapters": [{"time": scenes[0]["time"], "title": "Intro"}],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_process_video_no_visual_returns_current_artifact_contract(isolated_settings, monkeypatch):
    tmp_path = isolated_settings
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"fake")

    monkeypatch.setattr(main_module, "extract_audio", lambda *args, **kwargs: "audio.wav")
    monkeypatch.setattr(
        main_module,
        "transcribe",
        lambda *args, **kwargs: {
            "language": "en",
            "segments": [{"start": 0.0, "end": 1.0, "text": "Hello world"}],
            "words": [
                {
                    "word": "Hello",
                    "start": 0.0,
                    "end": 0.4,
                    "probability": 0.99,
                },
                {
                    "word": "world",
                    "start": 0.45,
                    "end": 0.9,
                    "probability": 0.98,
                },
            ],
        },
    )
    monkeypatch.setattr(main_module, "align_phonemes", lambda *args, **kwargs: [])
    monkeypatch.setattr(main_module, "generate_summary", _write_summary)

    result = main_module.process_video(
        video_path=str(video_path),
        language="en",
        enable_visual=False,
    )

    assert result["status"] == "completed"
    assert set(result["artifacts"]) == {"subtitles", "timeline"}

    timeline = json.loads(Path(result["artifacts"]["timeline"]).read_text(encoding="utf-8"))
    assert timeline["language"] == "en"
    assert timeline["detected_language"] == "en"
    assert timeline["visual_events"] == []
    assert len(timeline["words"]) == 2


def test_process_video_visual_exports_scene_index_as_visual_events(isolated_settings, monkeypatch):
    tmp_path = isolated_settings
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"fake")

    monkeypatch.setattr(main_module, "extract_audio", lambda *args, **kwargs: "audio.wav")
    monkeypatch.setattr(
        main_module,
        "transcribe",
        lambda *args, **kwargs: {
            "language": "en",
            "segments": [{"start": 0.0, "end": 1.0, "text": "Look here"}],
            "words": [
                {
                    "word": "Look",
                    "start": 0.0,
                    "end": 0.4,
                    "probability": 0.99,
                },
                {
                    "word": "here",
                    "start": 0.45,
                    "end": 0.9,
                    "probability": 0.98,
                },
            ],
        },
    )
    monkeypatch.setattr(main_module, "align_phonemes", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        main_module,
        "detect_scenes",
        lambda *args, **kwargs: [
            {"event_time": 12.25, "frame_path": "frame.png", "scene_index": 0}
        ],
    )

    def fake_build_scene_index(raw_events, language="en", output_path=None):
        scene_index = [
            {
                "scene_id": 0,
                "time": raw_events[0]["event_time"],
                "description": "A chart appears on the slide.",
                "tts_cached": False,
            }
        ]
        if output_path is not None:
            Path(output_path).write_text(
                json.dumps(scene_index, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return scene_index

    monkeypatch.setattr(main_module, "build_scene_index", fake_build_scene_index)
    monkeypatch.setattr(main_module, "generate_summary", _write_summary)

    result = main_module.process_video(
        video_path=str(video_path),
        language="en",
        enable_visual=True,
    )

    assert result["status"] == "completed"
    assert set(result["artifacts"]) == {"subtitles", "timeline", "scene_index", "summary"}

    timeline = json.loads(Path(result["artifacts"]["timeline"]).read_text(encoding="utf-8"))
    assert timeline["visual_events"] == [
        {
            "event_time": 12.25,
            "type": "scene_change",
            "description_text": "A chart appears on the slide.",
        }
    ]

    assert Path(result["artifacts"]["summary"]).exists()


def test_process_video_keeps_requested_language_and_persists_detected_language(
    isolated_settings, monkeypatch
):
    tmp_path = isolated_settings
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"fake")

    monkeypatch.setattr(main_module, "extract_audio", lambda *args, **kwargs: "audio.wav")
    monkeypatch.setattr(
        main_module,
        "transcribe",
        lambda *args, **kwargs: {
            "language": "ru",
            "segments": [{"start": 0.0, "end": 1.0, "text": "Privet"}],
            "words": [{"word": "Privet", "start": 0.0, "end": 0.8, "probability": 0.99}],
        },
    )
    monkeypatch.setattr(main_module, "align_phonemes", lambda *args, **kwargs: [])
    monkeypatch.setattr(main_module, "generate_summary", _write_summary)

    result = main_module.process_video(
        video_path=str(video_path),
        language="en",
        enable_visual=False,
    )

    job_dir = settings.output_dir / result["job_id"]
    timeline = json.loads(Path(result["artifacts"]["timeline"]).read_text(encoding="utf-8"))
    meta = json.loads((job_dir / "job_meta.json").read_text(encoding="utf-8"))

    assert timeline["language"] == "en"
    assert timeline["detected_language"] == "ru"
    assert meta["language"] == "en"
    assert meta["requested_language"] == "en"
    assert meta["detected_language"] == "ru"
    assert meta["description_runtime"]["sdk"] == "google-genai"
    assert meta["description_runtime"]["mode"] in {"vertex", "developer", "fallback"}
    assert meta["tts_runtime"]["provider"] == settings.tts_provider


def test_process_video_preserves_existing_job_timestamps_and_writes_completed_status(
    isolated_settings, monkeypatch
):
    tmp_path = isolated_settings
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"fake")
    job_dir = settings.output_dir / "precreated_job"
    job_dir.mkdir(parents=True)
    update_job_meta(
        job_dir,
        job_id="precreated_job",
        status="processing",
        created_at="2026-04-07T00:00:00.000Z",
        started_at="2026-04-07T00:00:01.000Z",
    )

    monkeypatch.setattr(main_module, "extract_audio", lambda *args, **kwargs: "audio.wav")
    monkeypatch.setattr(
        main_module,
        "transcribe",
        lambda *args, **kwargs: {
            "language": "en",
            "segments": [{"start": 0.0, "end": 1.0, "text": "Hello world"}],
            "words": [],
        },
    )
    monkeypatch.setattr(main_module, "align_phonemes", lambda *args, **kwargs: [])
    monkeypatch.setattr(main_module, "generate_summary", _write_summary)

    result = main_module.process_video(
        video_path=str(video_path),
        language="en",
        enable_visual=False,
        output_dir=str(job_dir),
        job_id="precreated_job",
    )

    meta = json.loads((job_dir / "job_meta.json").read_text(encoding="utf-8"))
    assert result["status"] == "completed"
    assert meta["status"] == "completed"
    assert meta["created_at"] == "2026-04-07T00:00:00.000Z"
    assert meta["started_at"] == "2026-04-07T00:00:01.000Z"
    assert meta["artifacts"]["timeline"].endswith("timeline.json")
    assert meta["description_runtime"]["sdk"] == "google-genai"
    assert meta["tts_runtime"]["provider"] == settings.tts_provider
