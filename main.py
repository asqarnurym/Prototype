"""CLI entry point and orchestrator for the Prototype preprocessing pipeline.

Data flow:
- input: source video path, requested language, and visual-pipeline toggle;
- processing: audio extraction -> ASR -> optional scene detection/indexing -> export;
- output: persisted artifacts in ``output/{job_id}`` plus ``job_meta.json`` metadata.
"""

import argparse
import logging
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from core.config import settings
from core.job_state import (
    JOB_STATUS_COMPLETED,
    build_job_artifacts,
    create_job_id,
    read_job_meta,
    update_job_meta,
    utc_now_iso,
)
from core.logging_config import setup_logging
from pipeline.audio.aligner import align_phonemes
from pipeline.audio.extractor import extract_audio
from pipeline.audio.transcriber import transcribe
from pipeline.exporters.json_export import export_timeline_json
from pipeline.exporters.vtt import export_vtt
from pipeline.summary import generate_summary
from pipeline.visual.scene_detect import detect_scenes
from pipeline.visual.scene_indexer import build_scene_index, build_timeline_visual_events

setup_logging()

logger = logging.getLogger(__name__)


def process_video(
    video_path: str,
    language: str = "en",
    enable_visual: bool = True,
    output_dir: str | None = None,
    job_id: str | None = None,
) -> dict:
    start_time = time.time()
    started_at = utc_now_iso()
    video = Path(video_path)
    runtime_snapshot = settings.runtime_snapshot()

    if not video.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if language not in settings.supported_languages:
        raise ValueError(
            f"Unsupported language '{language}'. Supported: {settings.supported_languages}"
        )

    # ── Prepare output and temporary directories ─────────────────
    if job_id is None:
        if output_dir:
            # Derive job_id from the directory name to avoid mismatch
            job_id = Path(output_dir).name
        else:
            job_id = create_job_id(video.stem)
    out_dir = Path(output_dir) if output_dir else settings.output_dir / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=settings.temp_dir) as _temp_dir_str:
        job_temp_dir = Path(_temp_dir_str)

        logger.info(f"{'=' * 60}")
        logger.info("Prototype Pipeline — Starting")
        logger.info(f"Video: {video_path} | Language: {language}")
        logger.info(
            "Runtime snapshot: description=%s model=%s project=%s location=%s auth=%s service_account=%s; tts=%s auth=%s service_account=%s",
            runtime_snapshot["description"]["provider"],
            runtime_snapshot["description"]["model"],
            runtime_snapshot["description"]["project"],
            runtime_snapshot["description"]["location"],
            runtime_snapshot["description"]["auth_mode"],
            runtime_snapshot["description"]["service_account_email"],
            runtime_snapshot["tts"]["provider"],
            runtime_snapshot["tts"]["auth_mode"],
            runtime_snapshot["tts"]["service_account_email"],
        )
        logger.info(f"{'=' * 60}")

        # ═══════════════════════════════════════════════════════════════
        # PARALLEL AUDIO AND VISUAL BRANCHES
        # ═══════════════════════════════════════════════════════════════

        def run_audio_branch():
            logger.info("▶ [Thread-Audio] Starting ASR branch...")
            wav_path = extract_audio(video_path, output_dir=str(job_temp_dir))
            transcript = transcribe(wav_path, language=language)
            phonemes = align_phonemes(wav_path, transcript, language)
            return transcript, phonemes

        def run_visual_branch():
            if not enable_visual:
                return []
            try:
                logger.info("▶ [Thread-Visual] Starting scene detection...")
                frames_dir = job_temp_dir / "frames"
                return detect_scenes(video_path, output_dir=str(frames_dir))
            except Exception as e:
                logger.error(f"Error in visual branch: {e}", exc_info=True)
                return []

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_audio = executor.submit(run_audio_branch)
            future_visual = executor.submit(run_visual_branch)

            # Wait for both branches before building final artifacts.
            transcript_data, phonemes = future_audio.result()
            raw_visual_events = future_visual.result()

        # ═══════════════════════════════════════════════════════════════
        # SEMANTIC ANALYSIS (Gemini + Summary)
        # ═══════════════════════════════════════════════════════════════

        scene_index = []

        if enable_visual and raw_visual_events:
            logger.info("▶ Stage 2.2: Building scene index (Gemini descriptions)...")
            scene_index_path = str(out_dir / "scene_index.json")
            scene_index = build_scene_index(
                raw_visual_events,
                language=language,
                output_path=scene_index_path,
            )
        else:
            logger.info("⏭ Visual pipeline skipped (--no-visual or no scenes detected)")

        # ═══════════════════════════════════════════════════════════════
        # STAGE 3: TIMELINE
        # ═══════════════════════════════════════════════════════════════

        logger.info("▶ Stage 3: Building timeline...")
        detected_language = transcript_data.get("language") or language
        if detected_language != language:
            logger.warning(
                "ASR detected language '%s' differs from requested pipeline language '%s'",
                detected_language,
                language,
            )
        final_timeline = {
            "language": language,
            "detected_language": detected_language,
            "segments": transcript_data.get("segments", []),
            "words": transcript_data.get("words", []),
            "phonemes": phonemes,
            "visual_events": build_timeline_visual_events(scene_index),
        }
        logger.info("  ✓ Timeline built")

        # ═══════════════════════════════════════════════════════════════
        # STAGE 4: EXPORT ARTIFACTS
        # ═══════════════════════════════════════════════════════════════

        logger.info("▶ Stage 4.1: Exporting VTT subtitles...")
        vtt_path = str(out_dir / "subtitles.vtt")
        export_vtt(final_timeline, vtt_path)

        logger.info("▶ Stage 4.2: Exporting timeline.json...")
        json_path = str(out_dir / "timeline.json")
        export_timeline_json(final_timeline, json_path)

        # ═══════════════════════════════════════════════════════════════
        # STAGE 5: SUMMARY FOR ADHD/DYSLEXIA (summary + chapters)
        # ═══════════════════════════════════════════════════════════════

        if enable_visual and scene_index:
            logger.info("▶ Stage 5: Generating summary + chapters...")
            summary_path = str(out_dir / "summary.json")
            try:
                generate_summary(
                    scenes=scene_index,
                    job_id=job_id,
                    language=language,
                    output_path=summary_path,
                    transcript_segments=[
                        segment.get("text", "") for segment in final_timeline.get("segments", [])
                    ],
                )
            except Exception as e:
                logger.warning(f"  ⚠ Summary generation failed: {e}")

        elapsed = time.time() - start_time

        artifacts = build_job_artifacts(out_dir)

        existing_meta = read_job_meta(out_dir)
        result = {
            "job_id": job_id,
            "status": JOB_STATUS_COMPLETED,
            "processing_time_sec": round(elapsed, 2),
            "artifacts": artifacts,
        }

        update_job_meta(
            out_dir,
            job_id=job_id,
            video_file=video.name,
            video_path=str(Path(video_path).resolve()),
            language=language,
            requested_language=language,
            detected_language=detected_language,
            enable_visual=enable_visual,
            status=JOB_STATUS_COMPLETED,
            created_at=existing_meta.get("created_at", started_at),
            started_at=existing_meta.get("started_at", started_at),
            completed_at=utc_now_iso(),
            processing_time_sec=round(elapsed, 2),
            scenes_count=len(scene_index),
            whisper_model=settings.whisper_model_size,
            whisper_device=settings.whisper_device,
            description_mode=settings.description_mode,
            description_runtime=runtime_snapshot["description"],
            tts_provider=settings.tts_provider,
            tts_runtime=runtime_snapshot["tts"],
            artifacts=artifacts,
            error_type=None,
            error_message=None,
        )

        logger.info(f"✅ Processing completed in {elapsed:.1f}s")
        return result


def main():
    parser = argparse.ArgumentParser(
        description="Prototype - preprocess educational videos for accessibility"
    )
    parser.add_argument("--video", "-v", required=True, help="Path to the input video file (.mp4)")
    parser.add_argument(
        "--language", "-l", default=settings.default_language, choices=settings.supported_languages
    )
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--no-visual", action="store_true")
    args = parser.parse_args()

    try:
        result = process_video(
            video_path=args.video,
            language=args.language,
            enable_visual=not args.no_visual,
            output_dir=args.output,
        )
        print(f"\n✅ Done! Job ID: {result['job_id']}")
    except Exception as exc:
        logger.error("❌ Error: %s", exc, exc_info=True)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
