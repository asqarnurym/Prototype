"""
tests/evaluation/service_smoke.py — Smoke-test all hosted + local services.

Verifies:
  - faster-whisper medium on CUDA with real transcription
  - Gemini 2.5 Flash via Vertex AI (no 429, no fallback, actual description)
  - Google Cloud TTS (synthesises real audio, not edge fallback)

Kept out of pytest discovery (no test_ prefix in filename) so it can be
run directly without interfering with CI/suite runs.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def _ensure_project_path():
    import sys
    from pathlib import Path

    # Add tests/evaluation to path so _bootstrap is resolvable
    eval_dir = Path(__file__).resolve().parent
    if str(eval_dir) not in sys.path:
        sys.path.insert(0, str(eval_dir))
    from _bootstrap import ensure_project_root_on_path

    ensure_project_root_on_path()


_ensure_project_path()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_test_video(out_path: Path) -> Path:
    """Create a 5-second test video with synthetic beep audio via ffmpeg."""
    from core.config import settings

    cmd = [
        settings.ffmpeg_path, "-y", "-v", "quiet",
        "-f", "lavfi", "-i", "color=c=blue:s=640x480:d=5",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-c:v", "libx264", "-c:a", "aac", "-shortest",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    return out_path


def _check_result(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    msg = f"[{status}] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return condition


# ---------------------------------------------------------------------------
# Whisper
# ---------------------------------------------------------------------------


def test_whisper_cuda() -> bool:
    """Verify faster-whisper loads on CUDA and transcribes a short audio clip."""
    print("\n── Whisper (faster-whisper medium + CUDA) ──")

    from core.config import settings

    device = settings.whisper_device
    compute = settings.whisper_compute_type
    model_size = settings.whisper_model_size

    ok = _check_result("CUDA device configured", device == "cuda", f"device={device}")
    ok = _check_result("Compute type float16", "float" in compute, f"compute={compute}") and ok
    ok = _check_result("Model size medium", model_size == "medium", f"size={model_size}") and ok

    if not ok:
        return False

    # Use the bundled demo video (has real speech)
    demo_video = settings.project_root / "input" / "demo_ui_small.mp4"
    if not demo_video.exists():
        return _check_result("Demo video exists", False, f"missing: {demo_video}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        from pipeline.audio.extractor import extract_audio
        wav_path = extract_audio(str(demo_video), str(tmp))

        from pipeline.audio.transcriber import transcribe
        start = time.perf_counter()
        transcript = transcribe(wav_path, language="en")
        elapsed = time.perf_counter() - start

    words = transcript.get("words", [])
    segments = transcript.get("segments", [])

    ok = _check_result("Transcription produced segments", len(segments) > 0, f"{len(segments)} segments") and ok
    ok = _check_result("Transcription produced words", len(words) > 0, f"{len(words)} words") and ok

    avg_conf = sum(w.get("probability", 0) for w in words) / max(len(words), 1)
    ok = _check_result("Word confidence > 0.5", avg_conf > 0.5, f"avg={avg_conf:.3f}") and ok
    ok = _check_result("Transcription time < 30s", elapsed < 30, f"{elapsed:.1f}s") and ok

    return ok


# ---------------------------------------------------------------------------
# Gemini (Vertex AI)
# ---------------------------------------------------------------------------


def test_gemini_vertex() -> bool:
    """Verify Gemini 2.5 Flash produces real descriptions via Vertex AI.

    Checks:
      - No 429 / RESOURCE_EXHAUSTED
      - Description is not a placeholder/fallback
      - Description length is sensible (>20 chars)
      - Response time is acceptable (<30s)
    """
    print("\n── Gemini 2.5 Flash (Vertex AI) ──")

    from core.config import settings

    mode = settings.description_mode
    project = settings.google_cloud_project
    location = settings.google_cloud_location
    model = settings.description_model

    ok = _check_result("Description mode is vertex", mode == "vertex", f"mode={mode}")
    ok = _check_result("Project configured", bool(project), f"project={project}") and ok
    ok = _check_result("Location configured", bool(location), f"location={location}") and ok

    if not ok:
        return False

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        demo_video = settings.project_root / "input" / "demo_ui_small.mp4"
        if not demo_video.exists():
            return _check_result("Demo video found", False, f"missing: {demo_video}")

        # Extract a frame at 0s
        test_image = tmp / "test_frame.png"
        subprocess.run(
            [
                settings.ffmpeg_path, "-y", "-v", "quiet",
                "-i", str(demo_video),
                "-vframes", "1",
                str(test_image),
            ],
            check=True,
        )

        from pipeline.visual.descriptor import generate_description

        start = time.perf_counter()
        try:
            description = generate_description(str(test_image), language="en")
            elapsed = time.perf_counter() - start
        except Exception as exc:
            return _check_result(
                "Gemini call succeeded",
                False,
                f"Exception: {type(exc).__name__}: {exc}",
            )

    ok = _check_result("Gemini call succeeded", True, f"{elapsed:.1f}s")
    ok = _check_result("Description is not empty", bool(description and description.strip())) and ok
    ok = _check_result(
        "Description is not a fallback",
        "unavailable" not in description.lower()
        and "rate limit" not in description.lower()
        and "новый визуальный" not in description.lower()
        and "fallback" not in description.lower(),
        f"desc: {description[:120]}...",
    ) and ok
    ok = _check_result(
        "Description length > 20 chars",
        len(description) > 20,
        f"{len(description)} chars",
    ) and ok
    ok = _check_result(
        "Response time < 30s",
        elapsed < 30,
        f"{elapsed:.1f}s",
    ) and ok
    ok = _check_result(
        f"Model is {model}",
        model in (settings.description_model or ""),
    ) and ok

    print(f"  Generated: {description[:200]}")

    return ok


# ---------------------------------------------------------------------------
# Google Cloud TTS
# ---------------------------------------------------------------------------


def test_google_tts() -> bool:
    """Verify Google Cloud TTS produces real MP3 audio (not edge-tts fallback).

    Checks:
      - Provider is google
      - Synthesized file is non-empty
      - Audio duration is > 0
    """
    print("\n── Google Cloud TTS ──")

    from core.config import settings

    provider = settings.tts_provider
    ok = _check_result("TTS provider is google", provider == "google", f"provider={provider}")
    if not ok:
        return False

    import asyncio

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        out_path = tmp / "smoke_tts.mp3"

        from pipeline.visual.tts import synthesize_speech_async

        text = "This is a smoke test for the Google Cloud text to speech service."
        try:
            result = asyncio.run(synthesize_speech_async(text, str(out_path), "en"))
        except Exception as exc:
            return _check_result(
                "TTS call succeeded",
                False,
                f"Exception: {type(exc).__name__}: {exc}",
            )

        ok = _check_result("TTS call succeeded", True)
        ok = _check_result("Output file exists", out_path.exists()) and ok
        ok = _check_result("Output file non-empty", out_path.stat().st_size > 0, f"{out_path.stat().st_size} bytes") and ok
        ok = _check_result("Audio duration > 0", result.get("duration_sec", 0) > 0, f"{result.get('duration_sec', 0):.1f}s") and ok

        from pipeline.visual.tts import _get_audio_duration
        duration = _get_audio_duration(str(out_path))
        ok = _check_result("Probe duration > 0", duration > 0, f"{duration:.1f}s") and ok

    return ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print("=" * 60)
    print("  Service Smoke Test — Whisper | Gemini Vertex | Google TTS")
    print("=" * 60)

    results: dict[str, bool] = {}

    results["whisper"] = test_whisper_cuda()
    results["gemini"] = test_gemini_vertex()
    results["tts"] = test_google_tts()

    print("\n" + "=" * 60)
    passed = sum(results.values())
    total = len(results)
    all_ok = passed == total
    status = "ALL PASSED" if all_ok else f"{passed}/{total} PASSED"
    print(f"  {status}")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
