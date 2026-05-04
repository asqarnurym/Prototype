from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean, median

from generate_charts import EVALUATION_DIR, PROJECT_ROOT, resolve_paper_run_dir

OUTPUT_DIR = EVALUATION_DIR / "paper_extensions"


def read_metric_rows(run_dir: Path) -> list[dict[str, str]]:
    """Load per-video metrics as plain dictionaries."""
    metrics_path = run_dir / "per_video_metrics.csv"
    with metrics_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_scenes(vid_id: str) -> list[dict]:
    """Load the saved B1 scene index for a video."""
    scene_path = PROJECT_ROOT / "output" / f"{vid_id}_B1" / "scene_index.json"
    if not scene_path.exists():
        raise FileNotFoundError(f"Missing scene index for {vid_id}: {scene_path}")
    return json.loads(scene_path.read_text(encoding="utf-8"))


def float_field(row: dict[str, str], name: str) -> float:
    return float(row[name])


def choose_lowest_coverage(rows: list[dict[str, str]]) -> dict[str, str]:
    return min(rows, key=lambda row: float_field(row, "coverage_15s_pct"))


def choose_dense_practical_demo(rows: list[dict[str, str]]) -> dict[str, str]:
    practical = [row for row in rows if row["content_type"] == "practical_demo"]
    candidates = practical or rows
    return max(candidates, key=lambda row: float_field(row, "scene_count"))


def choose_screencast_case(rows: list[dict[str, str]]) -> dict[str, str]:
    screencasts = [row for row in rows if row["content_type"] == "screencast"]
    candidates = screencasts or rows
    # Prefer sparse scene density with preserved coverage because it illustrates the low-motion case.
    return min(
        candidates,
        key=lambda row: (
            abs(float_field(row, "coverage_15s_pct") - 95.0),
            float_field(row, "scene_density_per_min"),
        ),
    )


def choose_talking_head_reference(rows: list[dict[str, str]]) -> dict[str, str]:
    talking_heads = [row for row in rows if row["content_type"] == "talking_head"]
    candidates = talking_heads or rows
    mean_rtf = mean(float_field(row, "b1_rtf") for row in candidates)
    mean_coverage = mean(float_field(row, "coverage_15s_pct") for row in candidates)
    return min(
        candidates,
        key=lambda row: abs(float_field(row, "b1_rtf") - mean_rtf) / mean_rtf
        + abs(float_field(row, "coverage_15s_pct") - mean_coverage) / mean_coverage,
    )


def scene_interval_stats(scenes: list[dict]) -> dict[str, float]:
    times = sorted(float(scene["time"]) for scene in scenes)
    intervals = [times[i + 1] - times[i] for i in range(len(times) - 1)]
    if not intervals:
        return {"min": 0.0, "median": 0.0, "max": 0.0}
    return {
        "min": min(intervals),
        "median": median(intervals),
        "max": max(intervals),
    }


def truncate(text: str, max_chars: int = 150) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def representative_scene_snippets(scenes: list[dict]) -> str:
    """Return compact first/middle/last description snippets for qualitative inspection."""
    if not scenes:
        return ""

    indices = [0, len(scenes) // 2, len(scenes) - 1]
    unique_indices: list[int] = []
    for index in indices:
        if index not in unique_indices:
            unique_indices.append(index)

    snippets = []
    for index in unique_indices:
        scene = scenes[index]
        snippets.append(
            f"@{float(scene['time']):.1f}s: {truncate(str(scene.get('description', '')))}"
        )
    return " | ".join(snippets)


def make_case(
    *,
    case_id: str,
    selection_rule: str,
    row: dict[str, str],
    observed_behavior: str,
    implication: str,
) -> dict[str, str]:
    scenes = load_scenes(row["vid_id"])
    intervals = scene_interval_stats(scenes)
    return {
        "case_id": case_id,
        "vid_id": row["vid_id"],
        "language": row["language"],
        "duration_bucket": row["duration_bucket"],
        "content_type": row["content_type"],
        "selection_rule": selection_rule,
        "b1_total_sec": row["b1_total_sec"],
        "b1_rtf": row["b1_rtf"],
        "coverage_15s_pct": row["coverage_15s_pct"],
        "scene_count": row["scene_count"],
        "scene_density_per_min": row["scene_density_per_min"],
        "tail_uncovered_sec": row["tail_uncovered_sec"],
        "median_interval_sec": f"{intervals['median']:.2f}",
        "max_interval_sec": f"{intervals['max']:.2f}",
        "observed_behavior": observed_behavior,
        "method_implication": implication,
        "representative_scene_snippets": representative_scene_snippets(scenes),
    }


def build_cases(run_dir: Path) -> list[dict[str, str]]:
    rows = read_metric_rows(run_dir)
    lowest = choose_lowest_coverage(rows)
    screencast = choose_screencast_case(rows)
    dense_demo = choose_dense_practical_demo(rows)
    talking_head = choose_talking_head_reference(rows)

    return [
        make_case(
            case_id="lowest_coverage",
            selection_rule="Minimum coverage_15s_pct in the corpus.",
            row=lowest,
            observed_behavior=(
                "The weakest coverage case occurs where visual transitions leave larger uncovered gaps."
            ),
            implication=(
                "Slide-centric or low-transition material may need periodic anchors, OCR-aware cues, "
                "or a lower scene-detection threshold when coverage is prioritized."
            ),
        ),
        make_case(
            case_id="screencast_reference",
            selection_rule="Screencast case closest to 95% coverage with sparse scene density.",
            row=screencast,
            observed_behavior=(
                "Coverage remains high in a low-motion content type, consistent with the role of "
                "fallback anchors when detector triggers are sparse."
            ),
            implication=(
                "Adaptive density is useful for avoiding long uncovered spans, but it should be "
                "reported as a coverage mechanism rather than a semantic-quality guarantee."
            ),
        ),
        make_case(
            case_id="dense_practical_demo",
            selection_rule="Practical-demo video with the largest scene count.",
            row=dense_demo,
            observed_behavior=(
                "The richest visual content produces many indexed scenes and a high absolute "
                "processing workload."
            ),
            implication=(
                "Static scene caps risk removing anchors from visually dense content; this motivates "
                "a coverage-cost trade-off analysis rather than a single fixed scene budget."
            ),
        ),
        make_case(
            case_id="talking_head_reference",
            selection_rule="Talking-head video closest to the content-type mean B1 RTF.",
            row=talking_head,
            observed_behavior=(
                "The conversational format behaves as a relatively stable reference case for the pipeline."
            ),
            implication=(
                "The main stress cases are not generic speech videos but low-transition slides and "
                "high-variation demonstrations."
            ),
        ),
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, cases: list[dict[str, str]], source_run: str) -> None:
    lines = [
        "# Qualitative Scene-Indexing Case Notes",
        "",
        f"Source run: `{source_run}`",
        "",
        "These notes are selected from saved B1 artifacts and are intended for paper drafting. "
        "They are qualitative engineering observations, not human judgments of accessibility quality.",
        "",
    ]

    for case in cases:
        lines.extend(
            [
                f"## {case['case_id']}",
                "",
                f"- Video: `{case['vid_id']}`",
                f"- Content type: `{case['content_type']}`; duration bucket: `{case['duration_bucket']}`; language: `{case['language']}`",
                f"- Selection rule: {case['selection_rule']}",
                f"- Metrics: B1 total={case['b1_total_sec']}s, B1 RTF={case['b1_rtf']}, coverage={case['coverage_15s_pct']}%, scenes={case['scene_count']}, density={case['scene_density_per_min']}/min, tail={case['tail_uncovered_sec']}s",
                f"- Scene spacing: median={case['median_interval_sec']}s, max={case['max_interval_sec']}s",
                f"- Observation: {case['observed_behavior']}",
                f"- Method implication: {case['method_implication']}",
                f"- Representative snippets: {case['representative_scene_snippets']}",
                "",
            ]
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def run_case_extraction(
    *,
    evaluation_dir: Path = EVALUATION_DIR,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Path]:
    run_dir = resolve_paper_run_dir(evaluation_dir)
    cases = build_cases(run_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "csv": output_dir / "qualitative_scene_cases.csv",
        "markdown": output_dir / "qualitative_scene_cases.md",
    }
    write_csv(paths["csv"], cases)
    write_markdown(paths["markdown"], cases, run_dir.name)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract qualitative scene-indexing cases for paper drafting."
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
        help="Directory for generated qualitative case artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = run_case_extraction(evaluation_dir=args.evaluation_dir, output_dir=args.output_dir)
    print("Qualitative case notes generated:")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
