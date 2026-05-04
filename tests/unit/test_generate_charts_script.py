import importlib.util
import json
from pathlib import Path


def _load_generate_charts_module():
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / "scripts" / "generate_charts.py"
    spec = importlib.util.spec_from_file_location("generate_charts_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_manifest(evaluation_dir: Path, *, n_videos: int) -> None:
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    header = (
        "id,path,language,duration_bucket,duration_sec,content_type,resolution,"
        "fps,audio_condition,source_license\n"
    )
    rows = [header]
    for index in range(n_videos):
        rows.append(
            f"vid_{index},./input/vid_{index}.mp4,en,short,60,talking_head,1280x720,30,clean,mixed\n"
        )
    (evaluation_dir / "corpus_manifest.csv").write_text("".join(rows), encoding="utf-8")


def _write_run(run_dir: Path, *, n_videos: int, report_videos: int | None = None) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    content_types = ["talking_head", "slide-centric", "screencast", "practical_demo"]
    metrics_rows = ["content_type,b0_rtf,b1_rtf,coverage_15s_pct\n"]
    for index in range(n_videos):
        content_type = content_types[index % len(content_types)]
        metrics_rows.append(
            f"{content_type},0.{(index % 4) + 2},0.{(index % 5) + 4},9{index % 10}.0\n"
        )
    (run_dir / "per_video_metrics.csv").write_text("".join(metrics_rows), encoding="utf-8")

    payload = {
        "corpus": {"n_videos": n_videos if report_videos is None else report_videos},
        "overall": {},
    }
    (run_dir / "evaluation_report.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_generate_charts_import_has_no_side_effects(tmp_path, monkeypatch):
    """Importing the script should not render charts or create the figures directory."""
    module = _load_generate_charts_module()
    figures_dir = tmp_path / "figures"
    evaluation_dir = tmp_path / "evaluation"

    monkeypatch.setattr(module, "FIGURES_DIR", figures_dir)
    monkeypatch.setattr(module, "EVALUATION_DIR", evaluation_dir)

    assert not figures_dir.exists()
    assert not evaluation_dir.exists()


def test_generate_charts_writes_to_repo_relative_figures_from_any_cwd(tmp_path, monkeypatch):
    """Chart generation should use the configured repo-relative directories, not cwd."""
    module = _load_generate_charts_module()
    evaluation_dir = tmp_path / "repo" / "evaluation"
    figures_dir = tmp_path / "repo" / "figures"
    run_dir = evaluation_dir / "run_001"

    _write_manifest(evaluation_dir, n_videos=24)
    _write_run(run_dir, n_videos=24)
    (evaluation_dir / "paper_charts_run.txt").write_text("run_001\n", encoding="utf-8")

    monkeypatch.setattr(module, "EVALUATION_DIR", evaluation_dir)
    monkeypatch.setattr(module, "FIGURES_DIR", figures_dir)
    (tmp_path / "outside-cwd").mkdir()
    monkeypatch.chdir(tmp_path / "outside-cwd")

    generated_run_dir = module.generate_charts(
        evaluation_dir=module.EVALUATION_DIR,
        figures_dir=module.FIGURES_DIR,
    )

    assert generated_run_dir == run_dir
    assert (figures_dir / "fig_rtf_comparison.png").exists()
    assert (figures_dir / "fig_coverage.png").exists()
    assert not (tmp_path / "outside-cwd" / "figures").exists()


def test_generate_charts_uses_pinned_paper_run_not_latest_run(tmp_path):
    module = _load_generate_charts_module()
    evaluation_dir = tmp_path / "evaluation"
    figures_dir = tmp_path / "figures"
    run_001 = evaluation_dir / "run_001"
    run_003 = evaluation_dir / "run_003"

    _write_manifest(evaluation_dir, n_videos=24)
    _write_run(run_001, n_videos=24)
    _write_run(run_003, n_videos=1)
    (evaluation_dir / "paper_charts_run.txt").write_text("run_001\n", encoding="utf-8")

    generated_run_dir = module.generate_charts(
        evaluation_dir=evaluation_dir,
        figures_dir=figures_dir,
    )

    assert generated_run_dir == run_001
    assert (figures_dir / "fig_rtf_comparison.png").exists()
    assert (figures_dir / "fig_coverage.png").exists()


def test_generate_charts_rejects_pinned_run_with_wrong_corpus_size(tmp_path):
    module = _load_generate_charts_module()
    evaluation_dir = tmp_path / "evaluation"
    figures_dir = tmp_path / "figures"
    run_003 = evaluation_dir / "run_003"

    _write_manifest(evaluation_dir, n_videos=24)
    _write_run(run_003, n_videos=1)
    (evaluation_dir / "paper_charts_run.txt").write_text("run_003\n", encoding="utf-8")

    try:
        module.generate_charts(evaluation_dir=evaluation_dir, figures_dir=figures_dir)
    except ValueError as error:
        assert "expected 24" in str(error)
    else:
        raise AssertionError("generate_charts() should reject a pinned smoke run")
