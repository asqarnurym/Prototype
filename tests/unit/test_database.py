"""Unit tests for core/database.py — SQLite persistence layer."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest

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
def sample_video():
    db_mod.ensure_video("v_test", filename="test.mp4", file_path="/tmp/test.mp4", language="en")
    return "v_test"


class TestSchemaIntegrity:
    def test_all_tables_exist(self):
        with db_mod.get_db() as db:
            rows = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            tables = {r[0] for r in rows}
        assert "videos" in tables
        assert "jobs" in tables
        assert "artifacts" in tables
        assert "scenes" in tables
        assert "tts_cache" in tables
        assert "evaluation_runs" in tables
        assert "evaluation_metrics" in tables

    def test_foreign_keys_enabled(self):
        with db_mod.get_db() as db:
            row = db.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1


class TestVideoCRUD:
    def test_ensure_video_inserts(self):
        db_mod.ensure_video("vid_1", filename="a.mp4", file_path="/tmp/a.mp4", language="en")
        with db_mod.get_db() as db:
            row = db.execute("SELECT * FROM videos WHERE id = 'vid_1'").fetchone()
        assert row is not None
        assert row["language"] == "en"
        assert row["source"] == "corpus"

    def test_ensure_video_idempotent(self):
        db_mod.ensure_video("vid_2", filename="b.mp4", file_path="/tmp/b.mp4")
        db_mod.ensure_video("vid_2", filename="b_v2.mp4", file_path="/tmp/b_v2.mp4")
        with db_mod.get_db() as db:
            row = db.execute("SELECT * FROM videos WHERE id = 'vid_2'").fetchone()
        assert row["filename"] == "b.mp4"

    def test_seed_corpus_from_manifest(self):
        actual_manifest = ORIG_DB_PATH.parent.parent / "evaluation" / "corpus_manifest.csv"
        if not actual_manifest.exists():
            pytest.skip("corpus_manifest.csv not found")
        with actual_manifest.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        for row in rows:
            db_mod.ensure_video(
                row["id"],
                filename=Path(row["path"]).name,
                file_path="dummy/" + row["path"],
                language=row["language"],
                duration_bucket=row["duration_bucket"],
                content_type=row.get("content_type", ""),
            )
        with db_mod.get_db() as db:
            count = db.execute("SELECT count(*) FROM videos").fetchone()[0]
        assert count == 24


class TestJobCRUD:
    def test_create_and_get(self, sample_video):
        db_mod.create_job("job_1", sample_video, config="B1", language="en")
        job = db_mod.get_job("job_1")
        assert job["status"] == "queued"
        assert job["config"] == "B1"
        assert job["video_id"] == sample_video

    def test_update_fields(self, sample_video):
        db_mod.create_job("job_2", sample_video)
        db_mod.update_job("job_2", status="completed", processing_time_sec=99.9)
        job = db_mod.get_job("job_2")
        assert job["status"] == "completed"
        assert job["processing_time_sec"] == 99.9

    def test_list_by_status(self, sample_video):
        db_mod.create_job("j_a", sample_video, config="B0")
        db_mod.create_job("j_b", sample_video, config="B1")
        db_mod.update_job("j_a", status="completed")
        completed = db_mod.list_jobs(status="completed")
        assert len(completed) == 1
        assert completed[0]["id"] == "j_a"

    def test_get_nonexistent(self):
        assert db_mod.get_job("ghost") is None


class TestArtifacts:
    def test_upsert_and_get(self, sample_video):
        db_mod.create_job("job_art", sample_video)
        db_mod.upsert_artifact("job_art", "subtitles", "/out/sub.vtt")
        db_mod.upsert_artifact("job_art", "timeline", "/out/timeline.json")
        arts = db_mod.get_artifacts("job_art")
        assert arts["subtitles"] == "/out/sub.vtt"
        assert arts["timeline"] == "/out/timeline.json"

    def test_upsert_replace(self, sample_video):
        db_mod.create_job("job_rep", sample_video)
        db_mod.upsert_artifact("job_rep", "subtitles", "/out/old.vtt")
        db_mod.upsert_artifact("job_rep", "subtitles", "/out/new.vtt")
        arts = db_mod.get_artifacts("job_rep")
        assert arts["subtitles"] == "/out/new.vtt"


class TestScenes:
    def test_upsert_and_list(self, sample_video):
        db_mod.create_job("job_sc", sample_video)
        db_mod.upsert_scene("job_sc", 0, time_sec=0.0, description="Start")
        db_mod.upsert_scene("job_sc", 1, time_sec=42.0, description="Middle", has_screen_text=1)
        scenes = db_mod.get_scenes("job_sc")
        assert len(scenes) == 2
        assert scenes[1]["has_screen_text"] == 1

    def test_description_length_auto(self, sample_video):
        db_mod.create_job("job_len", sample_video)
        db_mod.upsert_scene("job_len", 0, time_sec=0.0, description="Hello")
        scene = db_mod.get_scene("job_len", 0)
        assert scene["description_length"] == 5

    def test_nearest_scene(self, sample_video):
        db_mod.create_job("job_near", sample_video)
        db_mod.upsert_scene("job_near", 0, time_sec=5.0, description="A")
        db_mod.upsert_scene("job_near", 1, time_sec=50.0, description="B")
        db_mod.upsert_scene("job_near", 2, time_sec=100.0, description="C")

        ns = db_mod.get_nearest_scene("job_near", 10.0, tolerance=30.0)
        assert ns is not None
        assert ns["scene_id"] == 0

        ns2 = db_mod.get_nearest_scene("job_near", 55.0, tolerance=30.0)
        assert ns2 is not None
        assert ns2["scene_id"] == 1

        ns3 = db_mod.get_nearest_scene("job_near", 200.0, tolerance=30.0)
        assert ns3 is None


class TestTTSCache:
    def test_insert_and_retrieve(self, sample_video):
        db_mod.create_job("job_tts", sample_video)
        db_mod.upsert_scene("job_tts", 0, time_sec=0.0, description="Test")
        scene_row = db_mod.get_scene("job_tts", 0)
        sid = scene_row["id"]

        db_mod.mark_scene_tts(sid, "en", "/cache/scene_0000_en.mp3", 2.5)
        cached = db_mod.get_tts_cache(sid, "en")
        assert cached is not None
        assert cached["audio_path"] == "/cache/scene_0000_en.mp3"
        assert cached["duration_sec"] == 2.5

        scene = db_mod.get_scene("job_tts", 0)
        assert scene["tts_cached"] == 1

        assert db_mod.get_tts_cache(sid, "ru") is None


class TestEvaluation:
    def test_create_run_and_upsert_metrics(self):
        run_id = db_mod.create_evaluation_run("test_run", total_videos=3)
        assert run_id > 0

        db_mod.upsert_evaluation_metric(run_id, "v1", language="en", b0_rtf=0.1, b1_rtf=0.5)
        db_mod.upsert_evaluation_metric(run_id, "v2", language="ru", b0_rtf=0.2, b1_rtf=0.6)
        db_mod.upsert_evaluation_metric(run_id, "v3", language="en", b0_rtf=0.15, b1_rtf=0.55)

        metrics = db_mod.get_evaluation_metrics(run_id)
        assert len(metrics) == 3

        db_mod.upsert_evaluation_metric(run_id, "v1", language="en", b0_rtf=0.99)
        metrics = db_mod.get_evaluation_metrics(run_id)
        v1 = next(m for m in metrics if m["video_id"] == "v1")
        assert v1["b0_rtf"] == 0.99
        assert v1["b1_rtf"] == 0.5

    def test_list_runs(self):
        db_mod.create_evaluation_run("alpha", total_videos=5)
        db_mod.create_evaluation_run("beta", total_videos=10)
        runs = db_mod.list_evaluation_runs()
        assert len(runs) >= 2
        names = {r["run_name"] for r in runs}
        assert "alpha" in names
        assert "beta" in names

    def test_idempotent_run_name(self):
        r1 = db_mod.create_evaluation_run("gamma", total_videos=5)
        r2 = db_mod.create_evaluation_run("gamma", total_videos=5)
        assert r1 == r2
