"""Analyze word-level timing quality from a job's timeline.json.

Usage:
    python tests/evaluation/analyze_alignment.py output/test_1770867214
    python tests/evaluation/analyze_alignment.py output/test_1770867214 --save
"""

import argparse
import json
from pathlib import Path


def analyze(job_dir: str, save: bool = False) -> dict:
    """Analyze word-level alignment metrics from timeline.json.

    Args:
        job_dir: Path to the job artifact directory.
        save: When True, also write the report next to the artifacts.

    Returns:
        A dict containing the computed metrics.
    """
    job_path = Path(job_dir)
    timeline_path = job_path / "timeline.json"

    if not timeline_path.exists():
        raise FileNotFoundError(f"timeline.json not found in {job_dir}")

    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    words = timeline.get("words", [])
    segments = timeline.get("segments", [])

    if not words:
        raise ValueError(f"No words in timeline.json for {job_dir}")

    # ── Word-level metrics ────────────────────────────────────────
    durations = [w["end"] - w["start"] for w in words]
    probabilities = [w["probability"] for w in words]

    gaps = []
    overlaps = []
    for i in range(len(words) - 1):
        gap = words[i + 1]["start"] - words[i]["end"]
        gaps.append(gap)
        if gap < -0.001:
            overlaps.append(
                {
                    "word_a": words[i]["word"],
                    "word_b": words[i + 1]["word"],
                    "overlap_sec": abs(gap),
                    "position": i,
                }
            )

    zero_duration = [w for w in words if w["end"] - w["start"] < 0.001]
    low_confidence = [w for w in words if w["probability"] < 0.5]

    # ── Confidence distribution ───────────────────────────────────
    confidence_bins = {
        "0.0-0.3": len([p for p in probabilities if p < 0.3]),
        "0.3-0.5": len([p for p in probabilities if 0.3 <= p < 0.5]),
        "0.5-0.7": len([p for p in probabilities if 0.5 <= p < 0.7]),
        "0.7-0.9": len([p for p in probabilities if 0.7 <= p < 0.9]),
        "0.9-1.0": len([p for p in probabilities if p >= 0.9]),
    }

    # ── Segment-level metrics ─────────────────────────────────────
    seg_durations = [s["end"] - s["start"] for s in segments]
    seg_word_counts = []
    for seg in segments:
        seg_words = [w for w in words if w["start"] >= seg["start"] and w["end"] <= seg["end"]]
        seg_word_counts.append(len(seg_words))

    # ── Coverage: how much of audio duration is covered by words ──
    if words:
        audio_start = words[0]["start"]
        audio_end = words[-1]["end"]
        total_word_time = sum(durations)
        audio_span = audio_end - audio_start
        coverage = total_word_time / audio_span if audio_span > 0 else 0
    else:
        coverage = 0

    # ── Build report ──────────────────────────────────────────────
    report = {
        "job_id": job_path.name,
        "language": timeline.get("language", "unknown"),
        "summary": {
            "total_words": len(words),
            "total_segments": len(segments),
            "audio_coverage": round(coverage, 4),
        },
        "word_duration": {
            "avg_sec": round(sum(durations) / len(durations), 4),
            "min_sec": round(min(durations), 4),
            "max_sec": round(max(durations), 4),
            "median_sec": round(sorted(durations)[len(durations) // 2], 4),
            "zero_duration_words": len(zero_duration),
        },
        "confidence": {
            "avg": round(sum(probabilities) / len(probabilities), 4),
            "min": round(min(probabilities), 4),
            "max": round(max(probabilities), 4),
            "low_confidence_count": len(low_confidence),
            "low_confidence_pct": round(len(low_confidence) / len(words) * 100, 2),
            "distribution": confidence_bins,
        },
        "gaps_between_words": {
            "avg_gap_sec": round(sum(gaps) / len(gaps), 4) if gaps else 0,
            "max_gap_sec": round(max(gaps), 4) if gaps else 0,
            "min_gap_sec": round(min(gaps), 4) if gaps else 0,
            "overlap_count": len(overlaps),
            "overlap_pct": round(len(overlaps) / len(gaps) * 100, 2) if gaps else 0,
        },
        "segment_stats": {
            "avg_duration_sec": round(sum(seg_durations) / len(seg_durations), 2),
            "avg_words_per_segment": round(sum(seg_word_counts) / len(seg_word_counts), 1),
            "min_words_per_segment": min(seg_word_counts),
            "max_words_per_segment": max(seg_word_counts),
        },
    }

    if low_confidence:
        report["low_confidence_words"] = [
            {
                "word": w["word"],
                "probability": w["probability"],
                "start": w["start"],
                "end": w["end"],
            }
            for w in low_confidence
        ]

    if overlaps:
        report["overlapping_words"] = overlaps

    # ── Print report ──────────────────────────────────────────────
    print("=" * 60)
    print("  WORD ALIGNMENT ANALYSIS")
    print(f"  Job: {report['job_id']}")
    print(f"  Language: {report['language']}")
    print("=" * 60)
    print()

    s = report["summary"]
    print(f"Total words:        {s['total_words']}")
    print(f"Total segments:     {s['total_segments']}")
    print(f"Audio coverage:     {s['audio_coverage']:.1%}")
    print()

    wd = report["word_duration"]
    print("── Word Duration ──")
    print(f"  Average:          {wd['avg_sec']:.3f}s")
    print(f"  Median:           {wd['median_sec']:.3f}s")
    print(f"  Range:            {wd['min_sec']:.3f}s – {wd['max_sec']:.3f}s")
    print(f"  Zero-duration:    {wd['zero_duration_words']}")
    print()

    c = report["confidence"]
    print("── Confidence ──")
    print(f"  Average:          {c['avg']:.3f}")
    print(f"  Min:              {c['min']:.3f}")
    print(f"  Low (<0.5):       {c['low_confidence_count']} ({c['low_confidence_pct']}%)")
    print("  Distribution:")
    for bucket, count in c["distribution"].items():
        bar = "#" * int(count / len(words) * 40)
        print(f"    {bucket}: {count:>4}  {bar}")
    print()

    g = report["gaps_between_words"]
    print("── Inter-word Gaps ──")
    print(f"  Average gap:      {g['avg_gap_sec']:.3f}s")
    print(f"  Max gap:          {g['max_gap_sec']:.3f}s")
    print(f"  Overlaps:         {g['overlap_count']} ({g['overlap_pct']}%)")
    print()

    ss = report["segment_stats"]
    print("── Segments ──")
    print(f"  Avg duration:     {ss['avg_duration_sec']:.2f}s")
    print(f"  Avg words/seg:    {ss['avg_words_per_segment']}")
    print(f"  Words range:      {ss['min_words_per_segment']}–{ss['max_words_per_segment']}")

    if low_confidence:
        print()
        print("── Low Confidence Words ──")
        for w in report["low_confidence_words"]:
            print(f"  '{w['word']}' prob={w['probability']:.3f} @ {w['start']:.2f}–{w['end']:.2f}s")

    # ── Save report ───────────────────────────────────────────────
    if save:
        report_path = job_path / "alignment_report.json"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print()
        print(f"Report saved to: {report_path}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze word alignment quality from timeline.json"
    )
    parser.add_argument("job_dir", help="Path to job output directory")
    parser.add_argument("--save", action="store_true", help="Save report as alignment_report.json")
    args = parser.parse_args()
    analyze(args.job_dir, args.save)
