"""Measure end-to-end pipeline performance for manual evaluation runs.

Usage:
    python tests/evaluation/analyze_pipeline.py ./input/test.mp4
    python tests/evaluation/analyze_pipeline.py ./input/test.mp4 --language ru
"""

import argparse
import json
import logging
import subprocess
import time
from pathlib import Path

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()


def _load_runtime_deps():
    from core.config import settings
    from core.logging_config import setup_logging

    return settings, setup_logging


settings, setup_logging = _load_runtime_deps()
setup_logging()

logger = logging.getLogger(__name__)


def get_video_info(video_path: str) -> dict:
    """Read basic video metadata with ffprobe."""
    cmd = [
        settings.ffprobe_path,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(result.stdout)

    duration = float(info["format"]["duration"])
    size_bytes = int(info["format"]["size"])
    vstream = next((s for s in info["streams"] if s["codec_type"] == "video"), {})

    return {
        "file": Path(video_path).name,
        "duration_sec": round(duration, 2),
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "resolution": f"{vstream.get('width', '?')}x{vstream.get('height', '?')}",
        "fps": vstream.get("r_frame_rate", "?"),
        "codec": vstream.get("codec_name", "?"),
    }


def run_pipeline(video_path: str, language: str = "en") -> dict:
    """Run the pipeline stage by stage and return a timing report."""

    from pipeline.audio.aligner import align_phonemes
    from pipeline.audio.extractor import extract_audio
    from pipeline.audio.transcriber import transcribe
    from pipeline.exporters.json_export import export_timeline_json
    from pipeline.exporters.vtt import export_vtt
    from pipeline.visual.scene_detect import detect_scenes
    from pipeline.visual.scene_indexer import (
        build_scene_index,
        build_timeline_visual_events,
    )

    video = Path(video_path)
    if not video.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    job_id = f"{video.stem}_{int(time.time())}"
    out_dir = settings.output_dir / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    timings = {}
    total_start = time.time()

    # ── Stage 1: Audio extraction ─────────────────────────────────
    logger.info("Stage 1: Audio extraction...")
    t0 = time.time()
    wav_path = extract_audio(video_path)
    timings["audio_extraction"] = round(time.time() - t0, 3)
    logger.info(f"  Done in {timings['audio_extraction']}s")

    # ── Stage 2: ASR ──────────────────────────────────────────────
    logger.info("Stage 2: ASR (faster-whisper)...")
    t0 = time.time()
    transcript = transcribe(wav_path, language=language)
    timings["asr_transcription"] = round(time.time() - t0, 3)
    logger.info(f"  Done in {timings['asr_transcription']}s")

    # ── Stage 3: Phoneme alignment ────────────────────────────────
    logger.info("Stage 3: Phoneme alignment...")
    t0 = time.time()
    phonemes = align_phonemes(wav_path, transcript, language)
    timings["phoneme_alignment"] = round(time.time() - t0, 3)

    # ── Stage 4: Scene detection ──────────────────────────────────
    logger.info("Stage 4: Scene detection (PySceneDetect)...")
    t0 = time.time()
    raw_events = detect_scenes(video_path)
    timings["scene_detection"] = round(time.time() - t0, 3)
    logger.info(f"  Done in {timings['scene_detection']}s")

    # ── Stage 5: Scene indexing (Gemini) ──────────────────────────
    logger.info("Stage 5: Scene indexing (Gemini descriptions)...")
    t0 = time.time()
    scene_index_path = str(out_dir / "scene_index.json")
    scene_index = build_scene_index(
        raw_events,
        language=language,
        output_path=scene_index_path,
    )
    timings["scene_indexing_gemini"] = round(time.time() - t0, 3)
    logger.info(f"  Done in {timings['scene_indexing_gemini']}s")

    # ── Stage 6: Export ───────────────────────────────────────────
    logger.info("Stage 6: Export (VTT + JSON)...")
    t0 = time.time()

    final_timeline = {
        "language": language,
        "detected_language": transcript.get("language", language),
        "segments": transcript.get("segments", []),
        "words": transcript.get("words", []),
        "phonemes": phonemes,
        "visual_events": build_timeline_visual_events(scene_index),
    }

    vtt_path = str(out_dir / "subtitles.vtt")
    export_vtt(final_timeline, vtt_path)

    json_path = str(out_dir / "timeline.json")
    export_timeline_json(final_timeline, json_path)

    timings["export"] = round(time.time() - t0, 3)

    total_time = round(time.time() - total_start, 3)
    timings["total"] = total_time

    # ── Gemini per-call estimate ───────────────────────────────────
    gemini_calls = len(scene_index)
    gemini_per_call = (
        round(timings["scene_indexing_gemini"] / gemini_calls, 2) if gemini_calls > 0 else 0
    )

    # ── Build report ──────────────────────────────────────────────
    video_info = get_video_info(video_path)

    report = {
        "job_id": job_id,
        "video": video_info,
        "config": {
            "whisper_model": settings.whisper_model_size,
            "device": settings.whisper_device,
            "compute_type": settings.whisper_compute_type,
            "gemini_model": settings.gemini_model,
            "tts_provider": settings.tts_provider,
            "scene_threshold": settings.scene_threshold,
            "min_scene_interval": settings.min_scene_interval_sec,
        },
        "results": {
            "segments": len(transcript.get("segments", [])),
            "words": len(transcript.get("words", [])),
            "raw_scenes": len(raw_events),
            "filtered_scenes": len(scene_index),
            "scene_reduction_pct": round(
                (len(raw_events) - len(scene_index)) / max(len(raw_events), 1) * 100, 1
            ),
            "gemini_calls": gemini_calls,
            "gemini_avg_sec": gemini_per_call,
        },
        "timings_sec": timings,
        "performance": {
            "realtime_ratio": round(total_time / video_info["duration_sec"], 2),
            "asr_realtime_ratio": round(
                timings["asr_transcription"] / video_info["duration_sec"], 2
            ),
        },
        "output_dir": str(out_dir),
    }

    # ── Print ─────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  PIPELINE PERFORMANCE REPORT")
    print("=" * 60)
    print()
    print(f"Video:         {video_info['file']}")
    print(
        f"Duration:      {video_info['duration_sec']}s ({video_info['duration_sec'] / 60:.1f} min)"
    )
    print(f"Resolution:    {video_info['resolution']}")
    print(f"Size:          {video_info['size_mb']} MB")
    print()
    print(f"Device:        {settings.whisper_device} ({settings.whisper_compute_type})")
    print(f"Whisper model: {settings.whisper_model_size}")
    print(f"Gemini model:  {settings.gemini_model}")
    print()
    print("── Timing Breakdown ──")
    stages = [
        ("Audio extraction", "audio_extraction"),
        ("ASR (faster-whisper)", "asr_transcription"),
        ("Phoneme alignment", "phoneme_alignment"),
        ("Scene detection", "scene_detection"),
        ("Scene index (Gemini)", "scene_indexing_gemini"),
        ("Export (VTT + JSON)", "export"),
    ]
    for label, key in stages:
        t = timings[key]
        pct = t / total_time * 100
        bar = "#" * int(pct / 2)
        print(f"  {label:<25} {t:7.1f}s  ({pct:4.1f}%)  {bar}")
    print(f"  {'─' * 25} {'─' * 7}")
    print(f"  {'TOTAL':<25} {total_time:7.1f}s")
    print()
    print(f"Realtime ratio:  {report['performance']['realtime_ratio']}x (lower = faster)")
    print(f"ASR only:        {report['performance']['asr_realtime_ratio']}x")
    print()
    print("── Results ──")
    r = report["results"]
    print(f"  Segments:       {r['segments']}")
    print(f"  Words:          {r['words']}")
    print(f"  Raw scenes:     {r['raw_scenes']}")
    print(f"  Filtered:       {r['filtered_scenes']} (-{r['scene_reduction_pct']}%)")
    print(f"  Gemini calls:   {r['gemini_calls']} (avg {r['gemini_avg_sec']}s each)")

    # ── Save ──────────────────────────────────────────────────────
    report_path = out_dir / "pipeline_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print()
    print(f"Report saved: {report_path}")
    print(f"Output dir:   {out_dir}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark the full pipeline with per-stage timing"
    )
    parser.add_argument("video", help="Path to input video file")
    parser.add_argument(
        "--language",
        "-l",
        default="en",
        choices=["en", "ru"],
        help="Language (default: en)",
    )
    args = parser.parse_args()
    run_pipeline(args.video, args.language)
