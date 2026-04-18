from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
FIGURES_DIR = PROJECT_ROOT / "figures"
PAPER_RUN_POINTER = "paper_charts_run.txt"
CORPUS_MANIFEST = "corpus_manifest.csv"

CONTENT_ORDER = ["talking_head", "slide-centric", "screencast", "practical_demo"]
CONTENT_LABELS = ["Talking head", "Slide-centric", "Screencast", "Practical demo"]


def configure_plot_style() -> None:
    """Apply the shared chart style used for paper-ready figures."""
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman"],
            "font.size": 10,
            "axes.labelsize": 11,
            "axes.titlesize": 12,
            "figure.titlesize": 14,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "figure.dpi": 300,
            "savefig.dpi": 300,
        }
    )


def get_expected_corpus_size(evaluation_dir: Path = EVALUATION_DIR) -> int:
    """Return the number of videos declared in the paper corpus manifest."""
    manifest_path = evaluation_dir / CORPUS_MANIFEST
    if not manifest_path.exists():
        raise FileNotFoundError(f"Paper corpus manifest not found: {manifest_path}")

    with manifest_path.open(encoding="utf-8", newline="") as handle:
        row_count = sum(1 for _ in csv.DictReader(handle))

    if row_count <= 0:
        raise ValueError(f"Paper corpus manifest is empty: {manifest_path}")
    return row_count


def load_evaluation_report(run_dir: Path) -> dict:
    """Load the saved evaluation report for a paper evidence run."""
    report_path = run_dir / "evaluation_report.json"
    if not report_path.exists():
        raise FileNotFoundError(
            f"Evaluation report for the paper charts run not found: {report_path}"
        )
    with report_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def resolve_paper_run_dir(evaluation_dir: Path = EVALUATION_DIR) -> Path:
    """Return the pinned evaluation run used for paper-ready charts."""
    pointer_path = evaluation_dir / PAPER_RUN_POINTER
    if not pointer_path.exists():
        raise FileNotFoundError(f"Paper charts run pointer not found: {pointer_path}")

    run_name = pointer_path.read_text(encoding="utf-8").strip()
    if not run_name:
        raise ValueError(f"Paper charts run pointer is empty: {pointer_path}")
    if Path(run_name).name != run_name or not run_name.startswith("run_"):
        raise ValueError(
            f"Paper charts run pointer must contain a run_* directory name, got: {run_name!r}"
        )

    run_dir = evaluation_dir / run_name
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Pinned paper charts run directory not found: {run_dir}")
    if not (run_dir / "per_video_metrics.csv").exists():
        raise FileNotFoundError(
            f"Pinned paper charts run is missing per_video_metrics.csv: {run_dir}"
        )

    expected_video_count = get_expected_corpus_size(evaluation_dir)
    report = load_evaluation_report(run_dir)
    actual_video_count = report.get("corpus", {}).get("n_videos")
    if actual_video_count != expected_video_count:
        raise ValueError(
            "Pinned paper charts run "
            f"{run_name} reports {actual_video_count} videos, expected "
            f"{expected_video_count} from {evaluation_dir / CORPUS_MANIFEST}."
        )

    return run_dir


def load_metrics(run_dir: Path) -> pd.DataFrame:
    """Load per-video metrics for the selected evaluation run."""
    return pd.read_csv(run_dir / "per_video_metrics.csv")


def save_rtf_comparison_chart(df: pd.DataFrame, figures_dir: Path) -> Path:
    """Render the real-time factor comparison chart."""
    fig, ax = plt.subplots(figsize=(5.2, 3.9))
    plot_data = pd.melt(
        df,
        id_vars=["content_type"],
        value_vars=["b0_rtf", "b1_rtf"],
        var_name="Pipeline_Mode",
        value_name="RTF",
    )
    plot_data["Pipeline_Mode"] = plot_data["Pipeline_Mode"].map(
        {"b0_rtf": "B0: ASR Only", "b1_rtf": "B1: Full Pipeline"}
    )
    plot_data["content_type"] = pd.Categorical(
        plot_data["content_type"], categories=CONTENT_ORDER, ordered=True
    )

    sns.boxplot(
        x="content_type",
        y="RTF",
        hue="Pipeline_Mode",
        data=plot_data,
        order=CONTENT_ORDER,
        hue_order=["B0: ASR Only", "B1: Full Pipeline"],
        width=0.6,
        palette=["#D3D3D3", "#4C72B0"],
        ax=ax,
    )
    ax.axhline(
        y=1.0,
        color="r",
        linestyle="--",
        alpha=0.7,
        label="Real-time Threshold (1.0)",
    )

    ax.set_title("Processing Speed (Real-Time Factor)")
    ax.set_xlabel("Content type")
    ax.set_ylabel("RTF (lower is faster)")
    ax.set_xticks(ax.get_xticks(), labels=CONTENT_LABELS, rotation=18, ha="right")
    ax.tick_params(axis="x", labelsize=9)
    ax.set_ylim(0, 1.3)
    ax.legend(
        loc="upper left",
        frameon=True,
        fontsize=9,
    )
    fig.subplots_adjust(top=0.90, bottom=0.25, left=0.12, right=0.98)

    output_path = figures_dir / "fig_rtf_comparison.png"
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return output_path


def save_coverage_chart(df: pd.DataFrame, figures_dir: Path) -> Path:
    """Render the scene-coverage chart grouped by content type."""
    fig, ax = plt.subplots(figsize=(5.0, 3.3))
    plot_df = df.copy()
    plot_df["content_type"] = pd.Categorical(
        plot_df["content_type"], categories=CONTENT_ORDER, ordered=True
    )
    sns.barplot(
        x="content_type",
        y="coverage_15s_pct",
        hue="content_type",
        data=plot_df,
        order=CONTENT_ORDER,
        hue_order=CONTENT_ORDER,
        dodge=False,
        legend=False,
        errorbar=("ci", 95),
        capsize=0.1,
        palette="Blues_d",
        ax=ax,
    )
    ax.set_title("Scene Index Coverage (within 15 s)")
    ax.set_xlabel("Content type")
    ax.set_ylabel("Coverage (%)")
    ax.set_ylim(0, 112)
    ax.set_xticks(ax.get_xticks(), labels=CONTENT_LABELS, rotation=18, ha="right")
    ax.tick_params(axis="x", labelsize=9)

    for patch in ax.patches:
        ax.annotate(
            f"{patch.get_height():.1f}%",
            (patch.get_x() + patch.get_width() / 2.0, 5),
            ha="center",
            va="bottom",
            fontsize=9,
            color="white",
            fontweight="bold",
            xytext=(0, 0),
            textcoords="offset points",
        )

    fig.subplots_adjust(top=0.90, bottom=0.24, left=0.12, right=0.98)

    output_path = figures_dir / "fig_coverage.png"
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return output_path


def generate_charts(
    *,
    evaluation_dir: Path = EVALUATION_DIR,
    figures_dir: Path = FIGURES_DIR,
) -> Path:
    """Build both charts from the pinned paper evidence run and return that run directory."""
    configure_plot_style()
    expected_video_count = get_expected_corpus_size(evaluation_dir)
    run_dir = resolve_paper_run_dir(evaluation_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)
    metrics = load_metrics(run_dir)
    if len(metrics.index) != expected_video_count:
        raise ValueError(
            f"Pinned paper charts run {run_dir.name} contains {len(metrics.index)} metric rows, "
            f"expected {expected_video_count} rows from {evaluation_dir / CORPUS_MANIFEST}."
        )
    save_rtf_comparison_chart(metrics, figures_dir)
    save_coverage_chart(metrics, figures_dir)
    return run_dir


def main() -> int:
    """Generate the standard evaluation figures for the pinned paper evidence run."""
    run_dir = generate_charts()
    print(f"Charts generated successfully from the paper evidence run {run_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
