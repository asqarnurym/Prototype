from pathlib import Path

import pandas as pd

# We don't have fine-grained timing in job_meta.json,
# but we have B0 (ASR only) and B1 (Total).
# We know B1 = B0 + Scene Detect + description stage (Descriptions + Summary).
# We can estimate the split.


def _resolve_run_dir() -> Path:
    base_dir = Path("evaluation")
    run_dirs = sorted(
        (
            d
            for d in base_dir.iterdir()
            if d.is_dir() and d.name.startswith("run_") and (d / "per_video_metrics.csv").exists()
        ),
        key=lambda d: d.name,
    )
    if not run_dirs:
        raise FileNotFoundError("No evaluation/run_* directory with per_video_metrics.csv found.")
    return run_dirs[-1]


run_dir = _resolve_run_dir()
df = pd.read_csv(run_dir / "per_video_metrics.csv")

# B0 is strictly Audio (Extract + ASR)
df["audio_pipeline"] = df["b0_asr_sec"]

# Visual pipeline overhead is B1 - B0
df["visual_pipeline_overhead"] = df["b1_total_sec"] - df["b0_asr_sec"]

# Let's group by duration bucket to show how the overhead dominates
agg = (
    df.groupby("duration_bucket")[["audio_pipeline", "visual_pipeline_overhead", "b1_total_sec"]]
    .mean()
    .round(1)
)

print("=== Pipeline Overhead Breakdown ===")
print(agg)
agg.to_csv(run_dir / "pipeline_overhead.csv")
