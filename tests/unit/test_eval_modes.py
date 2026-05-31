"""Unit tests for evaluation run modes — filter, init, resume, force-new."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

# Ensure the evaluation directory is on path so _bootstrap is importable
_EVAL_DIR = Path(__file__).resolve().parents[2] / "tests" / "evaluation"
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

import run_corpus_eval as eval_mod  # noqa: E402

# ---------------------------------------------------------------------------
# _filter_manifest
# ---------------------------------------------------------------------------


class TestFilterManifest:
    SAMPLE = [
        {"id": "en_short_talking_head", "language": "en", "duration_bucket": "short", "content_type": "talking_head"},
        {"id": "en_long_screencast", "language": "en", "duration_bucket": "long", "content_type": "screencast"},
        {"id": "ru_medium_practical_demo", "language": "ru", "duration_bucket": "medium", "content_type": "practical_demo"},
        {"id": "ru_short_slide-centric", "language": "ru", "duration_bucket": "short", "content_type": "slide-centric"},
    ]

    def test_no_filter_returns_all(self):
        result = eval_mod._filter_manifest(self.SAMPLE, lang=None, duration=None, content=None, vids=None)
        assert len(result) == 4

    def test_filter_by_language(self):
        result = eval_mod._filter_manifest(self.SAMPLE, lang="en", duration=None, content=None, vids=None)
        assert len(result) == 2
        assert all(r["language"] == "en" for r in result)

    def test_filter_by_duration(self):
        result = eval_mod._filter_manifest(self.SAMPLE, lang=None, duration="short", content=None, vids=None)
        assert len(result) == 2
        assert all(r["duration_bucket"] == "short" for r in result)

    def test_filter_by_content(self):
        result = eval_mod._filter_manifest(self.SAMPLE, lang=None, duration=None, content="screencast", vids=None)
        assert len(result) == 1
        assert result[0]["id"] == "en_long_screencast"

    def test_filter_by_vids(self):
        result = eval_mod._filter_manifest(self.SAMPLE, lang=None, duration=None, content=None, vids="en_long_screencast,ru_short_slide-centric")
        assert len(result) == 2

    def test_combined_filters(self):
        result = eval_mod._filter_manifest(self.SAMPLE, lang="ru", duration="short", content=None, vids=None)
        assert len(result) == 1
        assert result[0]["id"] == "ru_short_slide-centric"

    def test_empty_result(self):
        result = eval_mod._filter_manifest(self.SAMPLE, lang="fr", duration=None, content=None, vids=None)
        assert len(result) == 0

    def test_vids_with_spaces(self):
        result = eval_mod._filter_manifest(self.SAMPLE, lang=None, duration=None, content=None, vids=" en_short_talking_head , ru_medium_practical_demo ")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _init_run_dir
# ---------------------------------------------------------------------------


class TestInitRunDir:
    def test_new_when_no_runs(self, monkeypatch, tmp_path):
        monkeypatch.setattr(eval_mod, "BASE_EVAL_DIR", tmp_path)
        monkeypatch.setattr(eval_mod, "EVAL_DIR", None)

        eval_mod._init_run_dir(resume_run_name=None)
        assert eval_mod.EVAL_DIR == tmp_path / "run_001"
        assert eval_mod.EVAL_DIR.exists()

    def test_new_when_existing_runs(self, monkeypatch, tmp_path):
        (tmp_path / "run_001").mkdir()
        (tmp_path / "run_002").mkdir()
        monkeypatch.setattr(eval_mod, "BASE_EVAL_DIR", tmp_path)
        monkeypatch.setattr(eval_mod, "EVAL_DIR", None)

        eval_mod._init_run_dir(resume_run_name=None)
        assert eval_mod.EVAL_DIR == tmp_path / "run_003"

    def test_resume_creates_no_new_dir(self, monkeypatch, tmp_path):
        (tmp_path / "run_005").mkdir()
        monkeypatch.setattr(eval_mod, "BASE_EVAL_DIR", tmp_path)
        monkeypatch.setattr(eval_mod, "EVAL_DIR", None)

        eval_mod._init_run_dir(resume_run_name="run_005")
        assert eval_mod.EVAL_DIR == tmp_path / "run_005"
        dirs = [d.name for d in tmp_path.iterdir() if d.is_dir()]
        assert dirs == ["run_005"]  # no new dir created

    def test_resume_nonexistent_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr(eval_mod, "BASE_EVAL_DIR", tmp_path)
        monkeypatch.setattr(eval_mod, "EVAL_DIR", None)

        with pytest.raises(FileNotFoundError):
            eval_mod._init_run_dir(resume_run_name="run_999")

    def test_sets_output_paths(self, monkeypatch, tmp_path):
        monkeypatch.setattr(eval_mod, "BASE_EVAL_DIR", tmp_path)
        monkeypatch.setattr(eval_mod, "EVAL_DIR", None)

        eval_mod._init_run_dir(resume_run_name=None)
        assert eval_mod.METRICS_PATH is not None
        assert eval_mod.AGGREGATE_PATH is not None
        assert eval_mod.BASELINE_PATH is not None
        assert eval_mod.REPORT_PATH is not None
        assert "per_video_metrics.csv" in str(eval_mod.METRICS_PATH)

    def test_idempotent(self, monkeypatch, tmp_path):
        monkeypatch.setattr(eval_mod, "BASE_EVAL_DIR", tmp_path)
        monkeypatch.setattr(eval_mod, "EVAL_DIR", None)

        eval_mod._init_run_dir(resume_run_name=None)
        first = eval_mod.EVAL_DIR
        eval_mod._init_run_dir(resume_run_name=None)  # second call
        assert eval_mod.EVAL_DIR == first  # unchanged


# ---------------------------------------------------------------------------
# read_existing_metrics
# ---------------------------------------------------------------------------

CSV_CONTENT = (
    "vid_id,language,duration_bucket,content_type,video_duration_sec,b0_asr_sec,b0_rtf,b1_total_sec,b1_rtf,asr_confidence,low_conf_ratio,overlap_ratio,scene_count,scene_density_per_min,tail_uncovered_sec,coverage_15s_pct\n"
    "en_short,en,short,talking_head,100.0,20.0,0.20,50.0,0.50,0.95,0.01,0.0,10,5.0,0.0,90.0\n"
    "ru_short,ru,short,talking_head,100.0,25.0,0.25,55.0,0.55,0.93,0.02,0.0,12,5.0,0.0,92.0\n"
)


class TestReadExistingMetrics:
    def test_reads_from_latest_run(self, monkeypatch, tmp_path):
        run1 = tmp_path / "run_001"
        run1.mkdir()
        (run1 / "per_video_metrics.csv").write_text(CSV_CONTENT)

        monkeypatch.setattr(eval_mod, "BASE_EVAL_DIR", tmp_path)
        metrics = eval_mod.read_existing_metrics(run_name=None)
        assert len(metrics) == 2
        assert "en_short" in metrics
        assert "ru_short" in metrics

    def test_reads_from_specific_run(self, monkeypatch, tmp_path):
        run_a = tmp_path / "run_001"
        run_a.mkdir()
        (run_a / "per_video_metrics.csv").write_text(CSV_CONTENT)
        run_b = tmp_path / "run_002"
        run_b.mkdir()
        (run_b / "per_video_metrics.csv").write_text(
            CSV_CONTENT.replace("en_short", "en_other")
        )

        monkeypatch.setattr(eval_mod, "BASE_EVAL_DIR", tmp_path)
        metrics = eval_mod.read_existing_metrics(run_name="run_001")
        assert len(metrics) == 2
        assert "en_other" not in metrics  # only from run_001

    def test_empty_when_no_runs(self, monkeypatch, tmp_path):
        monkeypatch.setattr(eval_mod, "BASE_EVAL_DIR", tmp_path)
        metrics = eval_mod.read_existing_metrics(run_name=None)
        assert metrics == {}

    def test_skip_run_without_metrics(self, monkeypatch, tmp_path):
        # run_001 has no CSV, run_002 has CSV
        (tmp_path / "run_001").mkdir()
        run2 = tmp_path / "run_002"
        run2.mkdir()
        (run2 / "per_video_metrics.csv").write_text(CSV_CONTENT)

        monkeypatch.setattr(eval_mod, "BASE_EVAL_DIR", tmp_path)
        metrics = eval_mod.read_existing_metrics(run_name=None)
        assert len(metrics) == 2  # only from run_002


# ---------------------------------------------------------------------------
# needs_recompute
# ---------------------------------------------------------------------------


class TestNeedsRecompute:
    def test_empty_dict_needs_recompute(self):
        assert eval_mod.needs_recompute({}) is True

    def test_valid_metrics_but_no_artifacts(self):
        """Metrics look valid but B0/B1 output dirs don't exist — needs recompute."""
        row = {"vid_id": "test_video", "b0_asr_sec": "20.0", "b1_total_sec": "50.0", "video_duration_sec": "100.0"}
        assert eval_mod.needs_recompute(row) is True  # artifacts missing on disk

    def test_zero_values_recompute(self):
        row = {"b0_asr_sec": "0", "b1_total_sec": "50.0", "video_duration_sec": "100.0"}
        assert eval_mod.needs_recompute(row) is True

        row2 = {"b0_asr_sec": "20.0", "b1_total_sec": "0", "video_duration_sec": "100.0"}
        assert eval_mod.needs_recompute(row2) is True

    def test_invalid_values_recompute(self):
        row = {"b0_asr_sec": "abc", "b1_total_sec": "50.0", "video_duration_sec": "100.0"}
        assert eval_mod.needs_recompute(row) is True


# ---------------------------------------------------------------------------
# job_is_complete
# ---------------------------------------------------------------------------


class TestJobIsComplete:
    def test_complete_without_scenes(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        (job_dir / "job_meta.json").write_text("{}")
        (job_dir / "timeline.json").write_text("{}")
        (job_dir / "subtitles.vtt").write_text("WEBVTT")
        assert eval_mod.job_is_complete(job_dir, need_scenes=False) is True

    def test_incomplete_missing_timeline(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        (job_dir / "job_meta.json").write_text("{}")
        (job_dir / "subtitles.vtt").write_text("WEBVTT")
        assert eval_mod.job_is_complete(job_dir, need_scenes=False) is False

    def test_requires_scene_index(self, tmp_path):
        job_dir = tmp_path / "job"
        job_dir.mkdir()
        (job_dir / "job_meta.json").write_text("{}")
        (job_dir / "timeline.json").write_text("{}")
        (job_dir / "subtitles.vtt").write_text("WEBVTT")
        # No scene_index.json
        assert eval_mod.job_is_complete(job_dir, need_scenes=True) is False

    def test_nonexistent_dir(self, tmp_path):
        assert eval_mod.job_is_complete(tmp_path / "ghost", need_scenes=False) is False
