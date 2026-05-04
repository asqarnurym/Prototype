from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from generate_charts import EVALUATION_DIR, PROJECT_ROOT, load_metrics, resolve_paper_run_dir

OUTPUT_DIR = EVALUATION_DIR / "paper_extensions"
COVERAGE_WINDOW_SEC = 15

STRATEGY_DESCRIPTIONS = {
    "adaptive_actual": "Saved adaptive scene index used by the manuscript evidence run.",
    "static_cap_10": "Post-hoc cap: evenly subsample at most 10 scenes from adaptive index.",
    "static_cap_20": "Post-hoc cap: evenly subsample at most 20 scenes from adaptive index.",
    "static_cap_30": "Post-hoc cap: evenly subsample at most 30 scenes from adaptive index.",
    "uniform_60s": "Synthetic time-grid baseline with one anchor every 60 seconds.",
    "uniform_30s": "Synthetic time-grid baseline with one anchor every 30 seconds.",
}

STRATEGY_ORDER = list(STRATEGY_DESCRIPTIONS)


def coverage_within_window(times: list[float], duration_sec: float, window_sec: int) -> float:
    """Compute second-level coverage using the same convention as analyze_scenes.py."""
    if duration_sec <= 0 or not times:
        return 0.0

    covered_seconds = 0
    for t in range(int(duration_sec)):
        min_dist = min(abs(t - scene_time) for scene_time in times)
        if min_dist <= window_sec:
            covered_seconds += 1
    return covered_seconds / duration_sec * 100


def cap_by_position(times: list[float], cap: int) -> list[float]:
    """Evenly subsample a saved scene index to simulate a static scene budget."""
    sorted_times = sorted(times)
    if len(sorted_times) <= cap:
        return sorted_times
    if cap <= 1:
        return [sorted_times[0]]

    indices: list[int] = []
    for i in range(cap):
        index = round(i * (len(sorted_times) - 1) / (cap - 1))
        if index not in indices:
            indices.append(index)
    return [sorted_times[index] for index in indices]


def uniform_grid(duration_sec: float, step_sec: int) -> list[float]:
    """Create a synthetic uniform time grid for coverage-only comparison."""
    times: list[float] = []
    current = 0.0
    while current < duration_sec:
        times.append(current)
        current += step_sec
    return times


def load_scene_times(vid_id: str) -> list[float]:
    """Load saved B1 scene times for a video from the output directory."""
    scene_path = PROJECT_ROOT / "output" / f"{vid_id}_B1" / "scene_index.json"
    if not scene_path.exists():
        raise FileNotFoundError(f"Missing scene index for {vid_id}: {scene_path}")

    scenes = json.loads(scene_path.read_text(encoding="utf-8"))
    return [float(scene["time"]) for scene in scenes]


def build_strategy_times(scene_times: list[float], duration_sec: float) -> dict[str, list[float]]:
    """Return all ablation strategies for a single video."""
    return {
        "adaptive_actual": sorted(scene_times),
        "static_cap_10": cap_by_position(scene_times, 10),
        "static_cap_20": cap_by_position(scene_times, 20),
        "static_cap_30": cap_by_position(scene_times, 30),
        "uniform_60s": uniform_grid(duration_sec, 60),
        "uniform_30s": uniform_grid(duration_sec, 30),
    }


def build_ablation_rows(run_dir: Path, window_sec: int) -> list[dict[str, str]]:
    """Build per-video ablation rows from the pinned evaluation run."""
    metrics = load_metrics(run_dir)
    rows: list[dict[str, str]] = []

    for _, metric in metrics.iterrows():
        vid_id = str(metric["vid_id"])
        duration_sec = float(metric["video_duration_sec"])
        scene_times = load_scene_times(vid_id)
        adaptive_count = len(scene_times)
        strategy_times = build_strategy_times(scene_times, duration_sec)

        for strategy in STRATEGY_ORDER:
            times = strategy_times[strategy]
            coverage = coverage_within_window(times, duration_sec, window_sec)
            reduction = (
                (adaptive_count - len(times)) / adaptive_count * 100 if adaptive_count else 0.0
            )
            rows.append(
                {
                    "vid_id": vid_id,
                    "language": str(metric["language"]),
                    "duration_bucket": str(metric["duration_bucket"]),
                    "content_type": str(metric["content_type"]),
                    "strategy": strategy,
                    "strategy_description": STRATEGY_DESCRIPTIONS[strategy],
                    "video_duration_sec": f"{duration_sec:.2f}",
                    "scene_count": str(len(times)),
                    "adaptive_scene_count": str(adaptive_count),
                    "scene_reduction_vs_adaptive_pct": f"{reduction:.2f}",
                    f"coverage_{window_sec}s_pct": f"{coverage:.2f}",
                }
            )

    return rows


def summarize_rows(
    rows: list[dict[str, str]], *, group_fields: list[str], window_sec: int
) -> list[dict[str, str]]:
    """Aggregate ablation rows overall or by selected metadata fields."""
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = tuple(row[field] for field in group_fields)
        grouped[key].append(row)

    summary_rows: list[dict[str, str]] = []
    coverage_field = f"coverage_{window_sec}s_pct"

    for key, part in grouped.items():
        for strategy in STRATEGY_ORDER:
            strategy_part = [row for row in part if row["strategy"] == strategy]
            if not strategy_part:
                continue
            scene_counts = [float(row["scene_count"]) for row in strategy_part]
            coverages = [float(row[coverage_field]) for row in strategy_part]
            reductions = [
                float(row["scene_reduction_vs_adaptive_pct"]) for row in strategy_part
            ]
            out = {
                "strategy": strategy,
                "strategy_description": STRATEGY_DESCRIPTIONS[strategy],
                "n_videos": str(len(strategy_part)),
                "mean_scene_count": f"{mean(scene_counts):.2f}",
                "median_scene_count": f"{median(scene_counts):.2f}",
                f"mean_coverage_{window_sec}s_pct": f"{mean(coverages):.2f}",
                f"median_coverage_{window_sec}s_pct": f"{median(coverages):.2f}",
                "mean_scene_reduction_vs_adaptive_pct": f"{mean(reductions):.2f}",
            }
            for field, value in zip(group_fields, key, strict=True):
                out[field] = value
            summary_rows.append(out)

    return summary_rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write rows to CSV, preserving field order from the first row."""
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_ablation(
    *,
    evaluation_dir: Path = EVALUATION_DIR,
    output_dir: Path = OUTPUT_DIR,
    window_sec: int = COVERAGE_WINDOW_SEC,
) -> dict[str, Path]:
    """Generate scene-selection ablation artifacts for the pinned paper run."""
    run_dir = resolve_paper_run_dir(evaluation_dir)
    rows = build_ablation_rows(run_dir, window_sec)
    overall = summarize_rows(rows, group_fields=[], window_sec=window_sec)
    by_content = summarize_rows(rows, group_fields=["content_type"], window_sec=window_sec)
    by_duration = summarize_rows(rows, group_fields=["duration_bucket"], window_sec=window_sec)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "per_video": output_dir / "scene_selection_ablation_per_video.csv",
        "overall": output_dir / "scene_selection_ablation_summary.csv",
        "by_content": output_dir / "scene_selection_ablation_by_content_type.csv",
        "by_duration": output_dir / "scene_selection_ablation_by_duration.csv",
        "report": output_dir / "scene_selection_ablation_report.json",
    }
    write_csv(paths["per_video"], rows)
    write_csv(paths["overall"], overall)
    write_csv(paths["by_content"], by_content)
    write_csv(paths["by_duration"], by_duration)

    report = {
        "source_run": run_dir.name,
        "coverage_window_sec": window_sec,
        "strategies": STRATEGY_DESCRIPTIONS,
        "interpretation_notes": [
            "Static caps are post-hoc subsamples of the saved adaptive scene index; they do not re-run scene detection.",
            "Uniform baselines are synthetic time grids used as coverage-only references, not semantic scene detectors.",
            "Uniform 30s naturally saturates a within-15s coverage metric and should be read as an upper coverage reference rather than a semantic-quality baseline.",
        ],
        "outputs": {name: str(path) for name, path in paths.items() if name != "report"},
    }
    paths["report"].write_text(json.dumps(report, indent=2), encoding="utf-8")
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate post-hoc scene-selection ablation data for the paper."
    )
    parser.add_argument(
        "--evaluation-dir",
        type=Path,
        default=EVALUATION_DIR,
        help="Evaluation directory containing paper_charts_run.txt.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for generated ablation CSV/JSON artifacts.",
    )
    parser.add_argument(
        "--window-sec",
        type=int,
        default=COVERAGE_WINDOW_SEC,
        help="Coverage window in seconds around each indexed scene.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = run_ablation(
        evaluation_dir=args.evaluation_dir,
        output_dir=args.output_dir,
        window_sec=args.window_sec,
    )
    print("Scene-selection ablation generated:")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
