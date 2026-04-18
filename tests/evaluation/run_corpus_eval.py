import csv
import json
import time
from pathlib import Path
from statistics import mean, median

from _bootstrap import PROJECT_ROOT, ensure_project_root_on_path

ensure_project_root_on_path()


def _load_runtime_deps():
    import analyze_alignment
    import analyze_scenes

    from main import process_video

    return analyze_alignment, analyze_scenes, process_video


analyze_alignment, analyze_scenes, process_video = _load_runtime_deps()

# ── Versioned evaluation outputs ──────────────────────────────────
BASE_EVAL_DIR = PROJECT_ROOT / "evaluation"
BASE_EVAL_DIR.mkdir(exist_ok=True)

MANIFEST_PATH = PROJECT_ROOT / "evaluation" / "corpus_manifest.csv"

# NOTE: EVAL_DIR is created only when results are actually written.
# See finalize_run; this avoids empty run_XXX directories.
EVAL_DIR = None
METRICS_PATH = None
AGGREGATE_PATH = None
BASELINE_PATH = None
REPORT_PATH = None


def _init_run_dir():
    """Create the next run_XXX directory lazily and configure output paths."""
    global EVAL_DIR, METRICS_PATH, AGGREGATE_PATH, BASELINE_PATH, REPORT_PATH

    if EVAL_DIR is not None:
        return

    existing_runs = [d for d in BASE_EVAL_DIR.iterdir() if d.is_dir() and d.name.startswith("run_")]
    if not existing_runs:
        next_id = 1
    else:
        ids = [int(d.name.split("_")[1]) for d in existing_runs if d.name.split("_")[1].isdigit()]
        next_id = max(ids) + 1 if ids else 1

    EVAL_DIR = BASE_EVAL_DIR / f"run_{next_id:03d}"
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    METRICS_PATH = EVAL_DIR / "per_video_metrics.csv"
    AGGREGATE_PATH = EVAL_DIR / "aggregate_metrics.csv"
    BASELINE_PATH = EVAL_DIR / "baseline_comparison.csv"
    REPORT_PATH = EVAL_DIR / "evaluation_report.json"

    print(f"[*] Results will be saved to: {EVAL_DIR}")


def get_job_meta(job_dir: Path):
    meta_file = job_dir / "job_meta.json"
    if meta_file.exists():
        with open(meta_file, encoding="utf-8") as f:
            return json.load(f)
    return {}


def job_is_complete(job_dir: Path, *, need_scenes: bool = False) -> bool:
    """Check whether cached outputs contain the required artifacts."""
    if not job_dir.exists():
        return False
    required = ["job_meta.json", "timeline.json", "subtitles.vtt"]
    if need_scenes:
        required.append("scene_index.json")
    return all((job_dir / f).exists() for f in required)


def read_existing_metrics() -> dict:
    """Look for cached metrics in the latest existing run_XXX directory."""
    existing_runs = sorted(
        [d for d in BASE_EVAL_DIR.iterdir() if d.is_dir() and d.name.startswith("run_")],
        key=lambda d: d.name,
    )
    for run_dir in reversed(existing_runs):
        metrics_file = run_dir / "per_video_metrics.csv"
        if metrics_file.exists():
            out = {}
            with open(metrics_file, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    out[row["vid_id"]] = row
            if out:
                print(f"[*] Found cached metrics in {run_dir.name} ({len(out)} videos)")
                return out
    return {}


def needs_recompute(existing: dict) -> bool:
    if not existing:
        return True

    try:
        b0 = float(existing.get("b0_asr_sec", 0) or 0)
        b1 = float(existing.get("b1_total_sec", 0) or 0)
        dur = float(existing.get("video_duration_sec", 0) or 0)
    except ValueError:
        return True

    return b0 <= 0 or b1 <= 0 or dur <= 0


def get_or_run_job_time(
    job_dir: Path, *, video_path: Path, language: str, enable_visual: bool
) -> float:
    """Return processing time, reusing cached outputs only when they are complete."""
    if job_is_complete(job_dir, need_scenes=enable_visual):
        meta = get_job_meta(job_dir)
        cached_time = meta.get("processing_time_sec", 0)
        if cached_time and cached_time > 0:
            return float(cached_time)

    print(f"    [!] Cache incomplete for {job_dir.name}, running process_video...")
    start = time.time()
    process_video(
        video_path=str(video_path),
        language=language,
        enable_visual=enable_visual,
        output_dir=str(job_dir),
    )
    elapsed = time.time() - start
    return elapsed


def run_evaluation(limit: int | None = None):
    if not MANIFEST_PATH.exists():
        print(f"Manifest not found: {MANIFEST_PATH}")
        return

    existing_metrics = read_existing_metrics()

    headers = [
        "vid_id",
        "language",
        "duration_bucket",
        "content_type",
        "video_duration_sec",
        "b0_asr_sec",
        "b0_rtf",
        "b1_total_sec",
        "b1_rtf",
        "asr_confidence",
        "low_conf_ratio",
        "overlap_ratio",
        "scene_count",
        "scene_density_per_min",
        "tail_uncovered_sec",
        "coverage_15s_pct",
    ]

    output_rows = []
    skipped = []

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))

    if limit is not None:
        manifest = manifest[:limit]

    manifest_ids = [row["id"] for row in manifest]
    if len(manifest_ids) != len(set(manifest_ids)):
        raise ValueError("Duplicate ids found in evaluation/corpus_manifest.csv")

    for row in manifest:
        vid_id = row["id"]
        existing = existing_metrics.get(vid_id)
        if existing and not needs_recompute(existing):
            print(f"  ✓ Using cached metrics for {vid_id}")
            output_rows.append(existing)
            continue

        print(
            f"\n{'=' * 50}\nEvaluating: {vid_id} ({row['language']}, {row['duration_bucket']})\n{'=' * 50}"
        )

        video_path = PROJECT_ROOT / row["path"].lstrip("./")
        if not video_path.exists():
            print(f"  [!] Video missing: {video_path}")
            skipped.append(vid_id)
            continue

        # --- B0: ASR ONLY ---
        b0_job_id = f"{vid_id}_B0"
        b0_dir = PROJECT_ROOT / "output" / b0_job_id

        try:
            print("  Ensuring B0 (ASR-only) metrics...")
            b0_time = get_or_run_job_time(
                b0_dir,
                video_path=video_path,
                language=row["language"],
                enable_visual=False,
            )
        except Exception as e:
            print(f"  [!] B0 failed: {e}")
            skipped.append(vid_id)
            continue

        # --- B1: FULL PIPELINE ---
        b1_job_id = f"{vid_id}_B1"
        b1_dir = PROJECT_ROOT / "output" / b1_job_id

        try:
            print("  Ensuring B1 (Full Pipeline) metrics...")
            b1_time = get_or_run_job_time(
                b1_dir,
                video_path=video_path,
                language=row["language"],
                enable_visual=True,
            )
        except Exception as e:
            print(f"  [!] B1 failed: {e}")
            skipped.append(vid_id)
            continue

        # --- Analysis ---
        print("  Running analysis...")
        try:
            # Double-check that the expected artifacts exist before analysis.
            if not (b1_dir / "timeline.json").exists():
                raise FileNotFoundError(f"timeline.json missing in {b1_dir}")

            align_stats = analyze_alignment.analyze(str(b1_dir))
            scene_stats = analyze_scenes.analyze(str(b1_dir))

            vid_dur = scene_stats["video_duration_sec"]
            if vid_dur <= 0:
                vid_dur = float(row.get("duration_sec", 0))
            if vid_dur <= 0:
                raise ValueError(f"Could not determine video duration for {vid_id}")

            b0_rtf = b0_time / vid_dur if b0_time > 0 else 0
            b1_rtf = b1_time / vid_dur if b1_time > 0 else 0

            total_words = align_stats["summary"]["total_words"]
            low_conf = align_stats["confidence"]["low_confidence_count"]
            low_conf_ratio = low_conf / total_words if total_words > 0 else 0

            # Overlap ratio across adjacent words.
            overlaps = align_stats["gaps_between_words"]["overlap_count"]
            gaps = max(total_words - 1, 1)
            overlap_ratio = overlaps / gaps

            scene_count = scene_stats["scene_count"]
            vid_dur_min = vid_dur / 60
            scene_density = scene_count / vid_dur_min if vid_dur_min > 0 else 0
            last_scene = scene_stats["time_distribution"]["last_scene_sec"]
            tail = max(0, vid_dur - last_scene)

            out_row = {
                "vid_id": vid_id,
                "language": row["language"],
                "duration_bucket": row["duration_bucket"],
                "content_type": row["content_type"],
                "video_duration_sec": round(vid_dur, 2),
                "b0_asr_sec": round(b0_time, 2),
                "b0_rtf": round(b0_rtf, 4),
                "b1_total_sec": round(b1_time, 2),
                "b1_rtf": round(b1_rtf, 4),
                "asr_confidence": round(align_stats["confidence"]["avg"], 4),
                "low_conf_ratio": round(low_conf_ratio, 4),
                "overlap_ratio": round(overlap_ratio, 4),
                "scene_count": scene_count,
                "scene_density_per_min": round(scene_density, 2),
                "tail_uncovered_sec": round(tail, 2),
                "coverage_15s_pct": round(scene_stats["coverage"]["within_15s_pct"], 2),
            }

            output_rows.append(out_row)
            print("  [+] Metrics saved.")
        except Exception as e:
            print(f"  [!] Analysis failed for {vid_id}: {e}")
            skipped.append(vid_id)

    # ── Stop early when nothing was computed ──────────────────────
    if not output_rows:
        print("\n[!] No metrics were computed. Aborting (no run directory created).")
        return

    # ── Create the run directory only once there is data to write ─
    _init_run_dir()

    output_rows_sorted = []
    by_id = {row["vid_id"]: row for row in output_rows}
    for manifest_row in manifest:
        row = by_id.get(manifest_row["id"])
        if row is not None:
            output_rows_sorted.append(row)

    with open(METRICS_PATH, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=headers)
        writer.writeheader()
        writer.writerows(output_rows_sorted)

    if skipped:
        print(f"\n[!] Skipped {len(skipped)} videos: {', '.join(skipped)}")
        print(f"[*] Metrics saved for {len(output_rows_sorted)}/{len(manifest)} videos.")
    else:
        consistency_checks(output_rows_sorted, manifest)

    # ── Aggregate run-level metrics ───────────────────────────────
    print("\nEvaluating aggregates...")
    aggregate_metrics()
    write_baseline_comparison()
    write_report_json()


def aggregate_metrics():
    import pandas as pd

    if not METRICS_PATH.exists():
        return

    df = pd.read_csv(METRICS_PATH)

    # Group by language
    lang_agg = (
        df.groupby("language")
        .agg(
            {
                "b0_rtf": ["mean", "median", "std"],
                "b1_rtf": ["mean", "median", "std"],
                "asr_confidence": ["mean", "median"],
                "coverage_15s_pct": ["mean", "median", "std"],
                "scene_density_per_min": ["mean"],
            }
        )
        .round(3)
    )

    # Group by duration
    dur_agg = (
        df.groupby("duration_bucket")
        .agg(
            {
                "b0_rtf": ["mean", "median"],
                "b1_rtf": ["mean", "median"],
                "coverage_15s_pct": ["mean", "median"],
            }
        )
        .round(3)
    )

    # Overall
    overall = df.agg(
        {
            "b0_rtf": ["mean", "median", "std"],
            "b1_rtf": ["mean", "median", "std"],
            "asr_confidence": ["mean", "std"],
            "coverage_15s_pct": ["mean", "std"],
        }
    ).round(3)

    # Save to CSV
    with open(AGGREGATE_PATH, "w", encoding="utf-8") as f:
        f.write("=== BY LANGUAGE ===\n")
        lang_agg.to_csv(f)
        f.write("\n=== BY DURATION ===\n")
        dur_agg.to_csv(f)
        f.write("\n=== OVERALL ===\n")
        overall.to_csv(f)

    print(f"Aggregates saved to {AGGREGATE_PATH}")


def write_baseline_comparison():
    import pandas as pd

    if not METRICS_PATH.exists():
        return

    df = pd.read_csv(METRICS_PATH)
    rows = []

    def build_row(scope_name: str, part):
        b0_mean = float(part["b0_rtf"].mean())
        b1_mean = float(part["b1_rtf"].mean())
        b0_median = float(part["b0_rtf"].median())
        b1_median = float(part["b1_rtf"].median())
        delta = b1_mean - b0_mean
        speed_ratio = b1_mean / b0_mean if b0_mean > 0 else 0
        rows.append(
            {
                "scope": scope_name,
                "n": int(len(part)),
                "b0_rtf_mean": round(b0_mean, 4),
                "b1_rtf_mean": round(b1_mean, 4),
                "delta_rtf_mean": round(delta, 4),
                "b0_rtf_median": round(b0_median, 4),
                "b1_rtf_median": round(b1_median, 4),
                "b1_vs_b0_ratio": round(speed_ratio, 3),
            }
        )

    build_row("overall", df)
    for lang in sorted(df["language"].unique()):
        build_row(f"language:{lang}", df[df["language"] == lang])
    for bucket in ["short", "medium", "long"]:
        part = df[df["duration_bucket"] == bucket]
        if len(part) > 0:
            build_row(f"duration:{bucket}", part)

    with open(BASELINE_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Baseline comparison saved to {BASELINE_PATH}")


def consistency_checks(rows: list, manifest: list):
    issues = []

    if len(rows) != len(manifest):
        issues.append(f"Expected {len(manifest)} rows, got {len(rows)}")

    manifest_ids = {m["id"] for m in manifest}
    row_ids = {r["vid_id"] for r in rows}
    missing = sorted(manifest_ids - row_ids)
    if missing:
        issues.append(f"Missing rows for ids: {', '.join(missing)}")

    bad_b0 = [r["vid_id"] for r in rows if float(r["b0_asr_sec"]) <= 0]
    if bad_b0:
        issues.append(f"Non-positive b0_asr_sec for: {', '.join(bad_b0)}")

    bad_b1 = [r["vid_id"] for r in rows if float(r["b1_total_sec"]) <= 0]
    if bad_b1:
        issues.append(f"Non-positive b1_total_sec for: {', '.join(bad_b1)}")

    bad_cov = [r["vid_id"] for r in rows if not (0 <= float(r["coverage_15s_pct"]) <= 100)]
    if bad_cov:
        issues.append(f"Coverage outside [0,100] for: {', '.join(bad_cov)}")

    if issues:
        raise RuntimeError("Consistency checks failed:\n- " + "\n- ".join(issues))

    print("Consistency checks passed.")


def write_report_json():
    import pandas as pd

    if not METRICS_PATH.exists():
        return

    df = pd.read_csv(METRICS_PATH)

    by_lang = {}
    for lang, part in df.groupby("language"):
        by_lang[lang] = {
            "n": int(len(part)),
            "b0_rtf_mean": round(float(part["b0_rtf"].mean()), 4),
            "b1_rtf_mean": round(float(part["b1_rtf"].mean()), 4),
            "asr_confidence_mean": round(float(part["asr_confidence"].mean()), 4),
            "coverage_15s_mean": round(float(part["coverage_15s_pct"].mean()), 2),
        }

    b0_vals = [float(x) for x in df["b0_rtf"].tolist()]
    b1_vals = [float(x) for x in df["b1_rtf"].tolist()]
    conf_vals = [float(x) for x in df["asr_confidence"].tolist()]
    cov_vals = [float(x) for x in df["coverage_15s_pct"].tolist()]

    report = {
        "corpus": {
            "n_videos": int(len(df)),
            "languages": sorted(df["language"].unique().tolist()),
            "duration_buckets": sorted(df["duration_bucket"].unique().tolist()),
            "content_types": sorted(df["content_type"].unique().tolist()),
        },
        "overall": {
            "b0_rtf_mean": round(mean(b0_vals), 4),
            "b0_rtf_median": round(median(b0_vals), 4),
            "b1_rtf_mean": round(mean(b1_vals), 4),
            "b1_rtf_median": round(median(b1_vals), 4),
            "b1_vs_b0_ratio": round((mean(b1_vals) / mean(b0_vals)), 3) if mean(b0_vals) > 0 else 0,
            "asr_confidence_mean": round(mean(conf_vals), 4),
            "coverage_15s_mean": round(mean(cov_vals), 2),
            "videos_b1_rtf_ge_1": int((df["b1_rtf"] >= 1.0).sum()),
            "videos_with_zero_scenes": int((df["scene_count"] == 0).sum()),
        },
        "by_language": by_lang,
        "notes": [
            "Metrics are engineering proxies, not direct learning-outcome measures.",
            "B0 = ASR-only baseline (enable_visual=false).",
            "B1 = full pipeline (enable_visual=true).",
        ],
    }

    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Evaluation report saved to {REPORT_PATH}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run corpus evaluation over the bilingual manifest"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Evaluate only the first N manifest rows (useful for smoke checks).",
    )
    args = parser.parse_args()
    run_evaluation(limit=args.limit)
