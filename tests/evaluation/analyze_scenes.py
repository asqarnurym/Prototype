"""
analyze_scenes.py — Analysis of scene detection and description quality.

Reads scene_index.json and timeline.json, analyzes:
- scene distribution over time
- description quality (length, informativeness)
- ratio of raw/filtered scenes
- video coverage by scenes

Usage:
    python tests/evaluation/analyze_scenes.py output/test_1770867214
    python tests/evaluation/analyze_scenes.py output/test_1770867214 --save
"""

import argparse
import json
import re
from pathlib import Path


def analyze(job_dir: str, save: bool = False) -> dict:
    """
    Analyzes scene detection and description quality.
    """
    job_path = Path(job_dir)
    scene_path = job_path / "scene_index.json"
    timeline_path = job_path / "timeline.json"

    scenes = []
    if scene_path.exists():
        scenes = json.loads(scene_path.read_text(encoding="utf-8"))

    # Get video duration from timeline (last word.end)
    video_duration = 0
    if timeline_path.exists():
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
        words = timeline.get("words", [])
        if words:
            video_duration = words[-1]["end"]
        segments = timeline.get("segments", [])
        if segments and segments[-1]["end"] > video_duration:
            video_duration = segments[-1]["end"]

    if not scenes:
        print("No scenes in scene_index.json")
        res = {
            "job_id": job_path.name,
            "video_duration_sec": round(video_duration, 2),
            "scene_count": 0,
            "time_distribution": {
                "first_scene_sec": 0,
                "last_scene_sec": 0,
                "avg_interval_sec": 0,
                "min_interval_sec": 0,
                "max_interval_sec": 0,
                "median_interval_sec": 0,
            },
            "description_quality": {
                "avg_length_chars": 0,
                "min_length_chars": 0,
                "max_length_chars": 0,
                "avg_word_count": 0,
                "has_quoted_screen_text": 0,
                "quoted_text_pct": 0,
                "avg_content_score": 0,
            },
            "coverage": {"within_15s_pct": 0.0},
            "tts_cache": {"cached": 0, "not_cached": 0},
            "scenes": [],
        }
        if save:
            out_path = job_path / "scenes_report.json"
            out_path.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        return res

    # ── Time distribution ─────────────────────────────────────────
    times = [s["time"] for s in scenes]
    intervals = [times[i + 1] - times[i] for i in range(len(times) - 1)]

    # ── Description quality ───────────────────────────────────────
    descriptions = [s["description"] for s in scenes]
    desc_lengths = [len(d) for d in descriptions]
    desc_word_counts = [len(d.split()) for d in descriptions]

    # Content analysis: does description mention text/data from screen?
    # Patterns for both languages (EN + RU)
    text_mention_patterns = [
        r'[«""][^»""]+?[»""]',  # quoted text (English "" and Russian «»)
        r"text|slide|title|слайд|заголовок|текст|надпис|озаглавлен",  # references to text
        r"chart|graph|diagram|table|диаграмм|график|таблиц|схем",  # data visuals
        r"shows|displays|reads|instructs|отображ|показ|гласит|написан",  # descriptive verbs
    ]
    content_scores = []
    for desc in descriptions:
        score = sum(1 for p in text_mention_patterns if re.search(p, desc, re.IGNORECASE))
        content_scores.append(score)

    # How many descriptions reference screen text (quoted)?
    has_quoted_text = sum(1 for d in descriptions if re.search(r'[«""][^»""]+?[»""]', d))

    # TTS cache status
    cached = sum(1 for s in scenes if s.get("tts_cached", False))

    # ── Coverage: % of video covered by scenes ────────────────────
    if video_duration > 0:
        # If user presses D at any second, how likely are they
        # within 15s of an indexed scene?
        covered_seconds = 0
        for t in range(int(video_duration)):
            min_dist = min(abs(t - st) for st in times)
            if min_dist <= 15:
                covered_seconds += 1
        coverage_15s = covered_seconds / video_duration
    else:
        coverage_15s = 0

    # ── Build report ──────────────────────────────────────────────
    report = {
        "job_id": job_path.name,
        "video_duration_sec": round(video_duration, 2),
        "scene_count": len(scenes),
        "time_distribution": {
            "first_scene_sec": round(times[0], 2),
            "last_scene_sec": round(times[-1], 2),
            "avg_interval_sec": round(sum(intervals) / len(intervals), 2) if intervals else 0,
            "min_interval_sec": round(min(intervals), 2) if intervals else 0,
            "max_interval_sec": round(max(intervals), 2) if intervals else 0,
            "median_interval_sec": round(sorted(intervals)[len(intervals) // 2], 2)
            if intervals
            else 0,
        },
        "description_quality": {
            "avg_length_chars": round(sum(desc_lengths) / len(desc_lengths), 1),
            "min_length_chars": min(desc_lengths),
            "max_length_chars": max(desc_lengths),
            "avg_word_count": round(sum(desc_word_counts) / len(desc_word_counts), 1),
            "has_quoted_screen_text": has_quoted_text,
            "quoted_text_pct": round(has_quoted_text / len(descriptions) * 100, 1),
            "avg_content_score": round(sum(content_scores) / len(content_scores), 2),
        },
        "coverage": {
            "within_15s_pct": round(coverage_15s * 100, 1),
        },
        "tts_cache": {
            "cached": cached,
            "not_cached": len(scenes) - cached,
        },
        "scenes": [
            {
                "scene_id": s["scene_id"],
                "time": s["time"],
                "desc_length": len(s["description"]),
                "desc_words": len(s["description"].split()),
                "content_score": content_scores[i],
                "description": s["description"],
            }
            for i, s in enumerate(scenes)
        ],
    }

    # ── Print ─────────────────────────────────────────────────────
    print("=" * 60)
    print("  SCENE DETECTION & DESCRIPTION ANALYSIS")
    print(f"  Job: {report['job_id']}")
    print("=" * 60)
    print()

    print(f"Video duration:     {video_duration:.1f}s ({video_duration / 60:.1f} min)")
    print(f"Scenes indexed:     {len(scenes)}")
    print(f"Avg scene interval: {report['time_distribution']['avg_interval_sec']}s")
    print()

    print("── Time Distribution ──")
    td = report["time_distribution"]
    print(f"  First scene:   {td['first_scene_sec']}s")
    print(f"  Last scene:    {td['last_scene_sec']}s")
    print(f"  Interval range: {td['min_interval_sec']}s – {td['max_interval_sec']}s")
    print(f"  Median interval: {td['median_interval_sec']}s")
    print()

    # Timeline visualization
    if video_duration > 0:
        print("  Timeline (. = 5s, # = scene):")
        timeline_str = list("." * int(video_duration / 5 + 1))
        for t in times:
            pos = int(t / 5)
            if pos < len(timeline_str):
                timeline_str[pos] = "#"
        print(f"  0s {''.join(timeline_str)} {int(video_duration)}s")
        print()

    print("── Description Quality ──")
    dq = report["description_quality"]
    print(f"  Avg length:      {dq['avg_length_chars']} chars, {dq['avg_word_count']} words")
    print(f"  Length range:    {dq['min_length_chars']}–{dq['max_length_chars']} chars")
    print(
        f"  Has screen text: {dq['has_quoted_screen_text']}/"
        f"{len(scenes)} ({dq['quoted_text_pct']}%)"
    )
    print(f"  Content score:   {dq['avg_content_score']}/4 avg")
    print()

    print("── Scene Coverage ──")
    print(f"  Within 15s of a scene: {report['coverage']['within_15s_pct']}% of video")
    print()

    print("── Individual Scenes ──")
    for s in report["scenes"]:
        desc_preview = s["description"][:70]
        if len(s["description"]) > 70:
            desc_preview += "..."
        print(
            f"  #{s['scene_id']:2d}  @{s['time']:6.1f}s  "
            f"[{s['desc_length']:3d}ch, score={s['content_score']}]  "
            f"{desc_preview}"
        )

    # ── Save ──────────────────────────────────────────────────────
    if save:
        report_path = job_path / "scenes_report.json"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print()
        print(f"Report saved to: {report_path}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze scene detection and description quality")
    parser.add_argument("job_dir", help="Path to job output directory")
    parser.add_argument("--save", action="store_true", help="Save report as scenes_report.json")
    args = parser.parse_args()
    analyze(args.job_dir, args.save)
