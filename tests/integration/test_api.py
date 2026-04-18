import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.server import app
from core.config import settings

OPENAPI_PATH = Path(__file__).resolve().parents[2] / "openapi.json"
EXPECTED_BINARY_ENDPOINTS = {
    "/jobs/{job_id}/video": {"video/mp4", "video/webm", "video/x-matroska"},
    "/jobs/{job_id}/subtitles": {"text/vtt"},
    "/jobs/{job_id}/tts/{scene_id}": {"audio/mpeg"},
}


@pytest.fixture
def client(tmp_path):
    """Fixture for FastAPI TestClient with isolated directories."""
    # Override paths to use tmp_path
    original_input = settings.input_dir
    original_output = settings.output_dir

    settings.input_dir = tmp_path / "input"
    settings.output_dir = tmp_path / "output"
    settings.input_dir.mkdir()
    settings.output_dir.mkdir()

    with TestClient(app) as c:
        yield c

    # Restore original settings
    settings.input_dir = original_input
    settings.output_dir = original_output


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["runtime"]["description"]["sdk"] == "google-genai"
    assert response.json()["runtime"]["tts"]["provider"] == settings.tts_provider


def test_list_jobs_empty(client):
    """Test list jobs when no jobs are present."""
    response = client.get("/jobs")
    assert response.status_code == 200
    assert response.json() == {"jobs": []}


def test_get_job_meta_sync_fix(client, tmp_path):
    """Verify Fix 2: job_id matches URL even if meta says otherwise."""
    job_id = "requested_id"
    job_dir = settings.output_dir / job_id
    job_dir.mkdir(parents=True)

    meta_content = {"job_id": "different_internal_id", "language": "en"}
    (job_dir / "job_meta.json").write_text(json.dumps(meta_content))

    response = client.get(f"/jobs/{job_id}/meta")
    assert response.status_code == 200
    assert response.json()["job_id"] == job_id  # Should be synchronized


def test_jobs_and_words_expose_canonical_language_and_detected_language(client):
    """Old jobs should no longer drift between /jobs and /words language fields."""
    job_id = "legacy_language_job"
    job_dir = settings.output_dir / job_id
    job_dir.mkdir(parents=True)

    (job_dir / "job_meta.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
                "language": "en",
                "status": "completed",
            }
        ),
        encoding="utf-8",
    )
    (job_dir / "timeline.json").write_text(
        json.dumps(
            {
                "language": "ru",
                "segments": [{"start": 0.0, "end": 1.0, "text": "Privet mir"}],
                "words": [
                    {"word": "Privet", "start": 0.0, "end": 0.4},
                    {"word": "mir", "start": 0.45, "end": 0.8},
                ],
                "visual_events": [],
            }
        ),
        encoding="utf-8",
    )

    jobs_response = client.get("/jobs")
    words_response = client.get(f"/jobs/{job_id}/words")
    meta_response = client.get(f"/jobs/{job_id}/meta")

    assert jobs_response.status_code == 200
    assert words_response.status_code == 200
    assert meta_response.status_code == 200

    listed_job = next(job for job in jobs_response.json()["jobs"] if job["job_id"] == job_id)
    words_payload = words_response.json()
    meta_payload = meta_response.json()

    assert listed_job["language"] == "en"
    assert listed_job["detected_language"] == "ru"
    assert words_payload["language"] == "en"
    assert words_payload["detected_language"] == "ru"
    assert meta_payload["language"] == "en"
    assert meta_payload["requested_language"] == "en"
    assert meta_payload["detected_language"] == "ru"


def test_get_video_external_path_fix(client, tmp_path):
    """Verify Fix 1: Video served from recorded absolute path."""
    job_id = "test_external"
    job_dir = settings.output_dir / job_id
    job_dir.mkdir(parents=True)

    # Create external video
    external_video = tmp_path / "somewhere_else" / "video.mp4"
    external_video.parent.mkdir()
    external_video.write_text("fake video")

    meta_content = {
        "job_id": job_id,
        "video_file": "video.mp4",
        "video_path": str(external_video.resolve()),
    }
    (job_dir / "job_meta.json").write_text(json.dumps(meta_content))

    response = client.get(f"/jobs/{job_id}/video")
    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    assert response.read() == b"fake video"


def test_get_video_fallback_uses_actual_media_type(client):
    """Verify video fallback keeps the real Content-Type."""
    job_id = "lesson_123456"
    job_dir = settings.output_dir / job_id
    job_dir.mkdir(parents=True)
    fallback_video = settings.input_dir / "lesson.webm"
    fallback_video.write_text("fake webm")

    response = client.get(f"/jobs/{job_id}/video")

    assert response.status_code == 200
    assert response.headers["content-type"] == "video/webm"
    assert response.read() == b"fake webm"


def test_artifacts_keys_standard(client):
    """Verify Fix 3: Standard artifact keys in /jobs response."""
    job_id = "test_artifacts"
    job_dir = settings.output_dir / job_id
    job_dir.mkdir(parents=True)

    (job_dir / "subtitles.vtt").write_text("subs")
    (job_dir / "timeline.json").write_text("{}")

    response = client.get("/jobs")
    jobs = response.json()["jobs"]
    job = jobs[0]

    # Check for standardized keys (no _vtt or _json suffix)
    assert "subtitles" in job["artifacts"]
    assert "timeline" in job["artifacts"]
    assert "subtitles_vtt" not in job["artifacts"]


def test_openapi_schema_binary_types(client):
    """Verify Fix 4: Correct media types in OpenAPI schema."""
    response = client.get("/openapi.json")
    schema = response.json()
    paths = schema["paths"]

    for endpoint, expected_media_types in EXPECTED_BINARY_ENDPOINTS.items():
        response_content = paths[endpoint]["get"]["responses"]["200"]["content"]
        assert set(response_content) == expected_media_types


def test_checked_in_openapi_matches_runtime_binary_types(client):
    """Prevent drift between exported OpenAPI and runtime schema."""
    runtime_paths = client.get("/openapi.json").json()["paths"]
    exported_paths = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))["paths"]

    for endpoint, expected_media_types in EXPECTED_BINARY_ENDPOINTS.items():
        runtime_content = runtime_paths[endpoint]["get"]["responses"]["200"]["content"]
        exported_content = exported_paths[endpoint]["get"]["responses"]["200"]["content"]
        assert set(runtime_content) == expected_media_types
        assert set(exported_content) == expected_media_types


def test_process_persists_completed_status_and_artifacts(client, monkeypatch):
    """Queued API jobs should persist a completed state after background execution."""
    video_path = settings.input_dir / "lesson.mp4"
    video_path.write_bytes(b"video")

    def fake_process_video(*, video_path, language, enable_visual, output_dir, job_id):
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        subtitles_path = output_dir_path / "subtitles.vtt"
        timeline_path = output_dir_path / "timeline.json"
        summary_path = output_dir_path / "summary.json"
        subtitles_path.write_text("WEBVTT")
        timeline_path.write_text("{}")
        summary_path.write_text(json.dumps({"summary_points": ["One"], "chapters": []}))
        return {
            "job_id": job_id,
            "status": "completed",
            "processing_time_sec": 1.23,
            "artifacts": {
                "subtitles": str(subtitles_path),
                "timeline": str(timeline_path),
            },
        }

    monkeypatch.setattr("api.server.process_video", fake_process_video)

    response = client.post(
        "/process",
        json={
            "video_path": str(video_path),
            "language": "en",
            "enable_visual": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"

    job_dir = settings.output_dir / payload["job_id"]
    meta = json.loads((job_dir / "job_meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "completed"
    assert meta["processing_time_sec"] == 1.23
    assert set(meta["artifacts"]) == {"subtitles", "timeline", "summary"}
    assert meta["description_runtime"]["sdk"] == "google-genai"
    assert meta["tts_runtime"]["provider"] == settings.tts_provider


def test_process_upload_persists_completed_status_and_artifacts(client, monkeypatch):
    """Uploaded videos should be saved and queued through the same processing pipeline."""

    def fake_process_video(*, video_path, language, enable_visual, output_dir, job_id):
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        subtitles_path = output_dir_path / "subtitles.vtt"
        timeline_path = output_dir_path / "timeline.json"
        subtitles_path.write_text("WEBVTT")
        timeline_path.write_text("{}")
        assert Path(video_path).exists()
        assert Path(video_path).name.endswith("demo.mp4")
        return {
            "job_id": job_id,
            "status": "completed",
            "processing_time_sec": 0.8,
            "artifacts": {
                "subtitles": str(subtitles_path),
                "timeline": str(timeline_path),
            },
        }

    monkeypatch.setattr("api.server.process_video", fake_process_video)

    response = client.post(
        "/process-upload?language=en&enable_visual=true",
        content=b"video-bytes",
        headers={
            "Content-Type": "video/mp4",
            "X-Upload-Filename": "demo.mp4",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    job_dir = settings.output_dir / payload["job_id"]
    meta = json.loads((job_dir / "job_meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "completed"
    assert meta["video_file"].endswith("demo.mp4")
    assert Path(meta["video_path"]).exists()
    assert meta["description_runtime"]["sdk"] == "google-genai"
    assert meta["tts_runtime"]["provider"] == settings.tts_provider


def test_process_persists_failed_status(client, monkeypatch):
    """Background failures should be visible via job metadata instead of disappearing."""
    video_path = settings.input_dir / "broken.mp4"
    video_path.write_bytes(b"video")

    def failing_process_video(*, video_path, language, enable_visual, output_dir, job_id):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("api.server.process_video", failing_process_video)

    response = client.post(
        "/process",
        json={
            "video_path": str(video_path),
            "language": "en",
            "enable_visual": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    job_dir = settings.output_dir / payload["job_id"]
    meta = json.loads((job_dir / "job_meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "failed"
    assert meta["error_type"] == "RuntimeError"
    assert "simulated failure" in meta["error_message"]
    assert meta["description_runtime"]["sdk"] == "google-genai"
    assert meta["tts_runtime"]["provider"] == settings.tts_provider


def test_process_job_ids_do_not_collide_for_fast_repeats(client, monkeypatch):
    """Back-to-back requests for the same video should get unique job ids."""
    video_path = settings.input_dir / "repeat.mp4"
    video_path.write_bytes(b"video")

    def fake_process_video(*, video_path, language, enable_visual, output_dir, job_id):
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        timeline_path = output_dir_path / "timeline.json"
        timeline_path.write_text("{}")
        return {
            "job_id": job_id,
            "status": "completed",
            "processing_time_sec": 0.1,
            "artifacts": {"timeline": str(timeline_path)},
        }

    monkeypatch.setattr("api.server.process_video", fake_process_video)

    first = client.post(
        "/process",
        json={"video_path": str(video_path), "language": "en", "enable_visual": False},
    )
    second = client.post(
        "/process",
        json={"video_path": str(video_path), "language": "en", "enable_visual": False},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["job_id"] != second.json()["job_id"]


def test_get_scenes_returns_processing_state_instead_of_404(client):
    """Missing scene_index during processing should surface as a lifecycle conflict."""
    job_id = "processing_job"
    job_dir = settings.output_dir / job_id
    job_dir.mkdir(parents=True)
    (job_dir / "job_meta.json").write_text(
        json.dumps({"job_id": job_id, "status": "processing", "language": "en"})
    )

    response = client.get(f"/jobs/{job_id}/scenes")

    assert response.status_code == 409
    assert "processing" in response.json()["detail"]


def test_get_summary_regenerates_stale_cached_placeholder_summary(client):
    """Stale placeholder summaries should be rebuilt from scene descriptions."""
    job_id = "stale_summary_job"
    job_dir = settings.output_dir / job_id
    job_dir.mkdir(parents=True)

    (job_dir / "summary.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
                "language": "en",
                "summary_points": ["Summary unavailable (no Gemini API key)."],
                "chapters": [],
            }
        ),
        encoding="utf-8",
    )
    (job_dir / "scene_index.json").write_text(
        json.dumps(
            [
                {
                    "scene_id": 0,
                    "time": 0.0,
                    "description": "Course title and learning goals appear on screen.",
                },
                {
                    "scene_id": 1,
                    "time": 45.0,
                    "description": "The instructor demonstrates keyboard shortcuts in the editor.",
                },
            ]
        ),
        encoding="utf-8",
    )

    response = client.get(f"/jobs/{job_id}/summary")

    assert response.status_code == 200
    payload = response.json()
    assert any("learning goals" in point.lower() for point in payload["summary_points"])
    assert not any("no gemini api key" in point.lower() for point in payload["summary_points"])


def test_root_ui_exposes_processing_form_and_separate_font_controls(client):
    """The bundled UI should let users start processing and adjust UI/subtitle text separately."""
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="processVideoForm"' in response.text
    assert 'name="video_path"' in response.text
    assert 'id="videoFileInput"' in response.text
    assert 'id="uiFontSizeValue"' in response.text
    assert 'id="subtitleFontSizeValue"' in response.text
    assert 'id="subtitleMode"' in response.text


def test_root_ui_uses_single_custom_subtitle_path_without_extra_time_monitor(client):
    """The player UI should avoid native/custom subtitle duplication and extra time text."""
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="subtitleTrack"' not in response.text
    assert 'id="timeDisplay"' not in response.text


def test_root_ui_contains_description_cancellation_guard(client):
    """The frontend should invalidate pending descriptions when playback resumes."""
    response = client.get("/")

    assert response.status_code == 200
    assert "descriptionFlowToken" in response.text
    assert "descriptionRequestPending || descriptionActive" in response.text
    assert "Description stopped because video playback resumed." in response.text


def test_root_ui_wide_spacing_affects_word_and_letter_spacing(client):
    """Wide spacing should visibly expand reading surfaces, not just line height."""
    response = client.get("/")

    assert response.status_code == 200
    assert "word-spacing: 0.16em;" in response.text
    assert "letter-spacing: 0.03em;" in response.text


def test_root_ui_contains_keyboard_accessible_tab_navigation(client):
    """ARIA tabs should include keyboard navigation behavior."""
    response = client.get("/")

    assert response.status_code == 200
    assert "ArrowRight" in response.text
    assert "ArrowLeft" in response.text
    assert "Home" in response.text
    assert "End" in response.text


def test_root_ui_has_high_contrast_primary_button_override(client):
    """High-contrast mode should not leave primary buttons as white text on a light accent."""
    response = client.get("/")

    assert response.status_code == 200
    assert "body.high-contrast .btn-primary" in response.text
    assert "color: #000;" in response.text


def test_describe_scopes_tts_cache_by_language(client, monkeypatch):
    """Different languages should not reuse the same cached scene audio."""
    job_id = "tts_job"
    job_dir = settings.output_dir / job_id
    job_dir.mkdir(parents=True)
    scene_index_path = job_dir / "scene_index.json"
    scene_index_path.write_text(
        json.dumps(
            [
                {
                    "scene_id": 0,
                    "time": 1.0,
                    "description": "A title slide appears.",
                    "tts_cached": False,
                }
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    async def fake_synthesize(text, output_path, language):
        Path(output_path).write_bytes(f"{language}:{text}".encode())
        return {"audio_path": output_path, "duration_sec": 1.5}

    monkeypatch.setattr("api.server.synthesize_speech_async", fake_synthesize)

    response_en = client.post(
        f"/jobs/{job_id}/describe",
        json={"time": 1.0, "language": "en"},
    )
    response_ru = client.post(
        f"/jobs/{job_id}/describe",
        json={"time": 1.0, "language": "ru"},
    )

    assert response_en.status_code == 200
    assert response_ru.status_code == 200
    assert response_en.json()["tts_audio_url"] != response_ru.json()["tts_audio_url"]

    audio_en = client.get(response_en.json()["tts_audio_url"])
    audio_ru = client.get(response_ru.json()["tts_audio_url"])
    assert audio_en.status_code == 200
    assert audio_ru.status_code == 200
    assert audio_en.read() == b"en:A title slide appears."
    assert audio_ru.read() == b"ru:A title slide appears."

    scene_index = json.loads(scene_index_path.read_text(encoding="utf-8"))
    assert scene_index[0]["tts_cached"] is True
    assert scene_index[0]["tts_cached_languages"] == ["en", "ru"]
