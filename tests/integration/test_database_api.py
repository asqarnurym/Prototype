"""Integration tests for new SQLite-backed API endpoints + dual-write."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import core.database as db_mod

ORIG_DB_PATH = db_mod.DB_PATH


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "test.db"
        monkeypatch.setattr(db_mod, "DB_PATH", tmp)
        db_mod._init_db()
        yield
        monkeypatch.setattr(db_mod, "DB_PATH", ORIG_DB_PATH)


@pytest.fixture
def client(tmp_path):
    from api.server import app
    from core.config import settings

    original_input = settings.input_dir
    original_output = settings.output_dir

    settings.input_dir = tmp_path / "input"
    settings.output_dir = tmp_path / "output"
    settings.input_dir.mkdir()
    settings.output_dir.mkdir()

    with TestClient(app) as c:
        yield c

    settings.input_dir = original_input
    settings.output_dir = original_output


class TestMetricsEndpoint:
    def test_empty_db_returns_message(self, client):
        response = client.get("/api/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_metrics_with_data(self, client):
        # Seed an evaluation run with metrics
        run_id = db_mod.create_evaluation_run("run_test", total_videos=2)
        db_mod.upsert_evaluation_metric(run_id, "en_short", language="en",
            b0_rtf=0.15, b1_rtf=0.35, asr_confidence=0.95, coverage_15s_pct=90.0)
        db_mod.upsert_evaluation_metric(run_id, "ru_short", language="ru",
            b0_rtf=0.25, b1_rtf=0.55, asr_confidence=0.93, coverage_15s_pct=92.0)

        response = client.get(f"/api/metrics?run_id={run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert len(data["metrics"]) == 2

    def test_metrics_filter_by_language(self, client):
        run_id = db_mod.create_evaluation_run("run_filter", total_videos=2)
        db_mod.upsert_evaluation_metric(run_id, "en_short", language="en",
            b0_rtf=0.15, b1_rtf=0.35, asr_confidence=0.95, coverage_15s_pct=90.0)
        db_mod.upsert_evaluation_metric(run_id, "ru_short", language="ru",
            b0_rtf=0.25, b1_rtf=0.55, asr_confidence=0.93, coverage_15s_pct=92.0)

        response = client.get(f"/api/metrics?run_id={run_id}&language=ru")
        assert response.status_code == 200
        data = response.json()
        assert len(data["metrics"]) == 1
        assert data["metrics"][0]["video_id"] == "ru_short"


class TestRunsEndpoint:
    def test_empty_runs(self, client):
        response = client.get("/api/runs")
        assert response.status_code == 200
        assert response.json()["runs"] == []

    def test_list_runs(self, client):
        db_mod.create_evaluation_run("alpha")
        db_mod.create_evaluation_run("beta")
        response = client.get("/api/runs")
        assert response.status_code == 200
        names = [r["run_name"] for r in response.json()["runs"]]
        assert "alpha" in names
        assert "beta" in names


class TestDualWriteOnJobFinish:
    def test_successful_job_persisted_in_db(self, client, monkeypatch):
        """Simulate a completed process-upload job and verify SQLite mirror."""
        video_path = Path(db_mod.DB_PATH).parent.parent / "input" / "lesson.mp4"
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b"fake")

        def fake_process_video(*, video_path, language, enable_visual, output_dir, job_id):
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            (out / "subtitles.vtt").write_text("WEBVTT")
            (out / "timeline.json").write_text("{}")
            (out / "scene_index.json").write_text("[]")
            return {
                "job_id": job_id,
                "status": "completed",
                "processing_time_sec": 3.14,
                "artifacts": {
                    "subtitles": str(out / "subtitles.vtt"),
                    "timeline": str(out / "timeline.json"),
                },
            }

        monkeypatch.setattr("api.server.process_video", fake_process_video)

        response = client.post(
            "/process",
            json={"video_path": str(video_path), "language": "en", "enable_visual": True},
        )
        assert response.status_code == 200

        # Verify job appeared in SQLite
        job_id = response.json()["job_id"]
        job = db_mod.get_job(job_id)
        assert job is not None
        assert job["status"] == "completed"
        assert job["processing_time_sec"] == 3.14

    def test_failed_job_persisted_in_db(self, client, monkeypatch):
        video_path = Path(db_mod.DB_PATH).parent.parent / "input" / "broken.mp4"
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b"bad")

        def failing_process(*, video_path, language, enable_visual, output_dir, job_id):
            raise RuntimeError("simulated crash")

        monkeypatch.setattr("api.server.process_video", failing_process)

        response = client.post(
            "/process",
            json={"video_path": str(video_path), "language": "en", "enable_visual": False},
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]

        job = db_mod.get_job(job_id)
        assert job is not None
        assert job["status"] == "failed"
        assert job["error_type"] == "RuntimeError"
        assert "simulated crash" in job["error_message"]


class TestIntegrationEndpoints:
    """Smoke test existing endpoints still work after changes."""

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_list_jobs_empty(self, client):
        response = client.get("/jobs")
        assert response.status_code == 200
        assert response.json() == {"jobs": []}

    def test_root_ui(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_health_has_new_fields(self, client):
        response = client.get("/health")
        data = response.json()
        assert "runtime" in data
        assert "tts_provider" in data
        assert "description_mode" in data
