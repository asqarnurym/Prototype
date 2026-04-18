"""Extract a mono 16 kHz WAV track from a source video with FFmpeg."""

import logging
import subprocess
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_dir: str | None = None) -> str:
    """Extract a video's audio track and save it as WAV.

    Args:
        video_path: Path to the source video file.
        output_dir: Directory where the WAV file should be written.

    Returns:
        The absolute path to the extracted WAV file.

    Raises:
        FileNotFoundError: If the source video does not exist.
        RuntimeError: If FFmpeg fails or cannot be found.
    """
    video = Path(video_path)
    if not video.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Resolve the output directory and ensure it exists.
    out_dir = Path(output_dir) if output_dir else settings.temp_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Keep the source stem and switch the suffix to .wav.
    wav_path = out_dir / f"{video.stem}.wav"

    logger.info(f"Extracting audio: {video_path} -> {wav_path}")

    # ── FFmpeg command ────────────────────────────────────────────
    # -i: input file
    # -vn: drop the video stream
    # -acodec pcm_s16le: 16-bit PCM WAV output
    # -ar 16000: 16 kHz sample rate for ASR
    # -ac 1: mono output
    # -y: overwrite existing output
    cmd = [
        settings.ffmpeg_path,
        "-i",
        str(video),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-y",
        str(wav_path),
    ]

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(f"Audio extracted successfully: {wav_path}")
    except subprocess.CalledProcessError as exc:
        logger.error(f"FFmpeg error: {exc.stderr}")
        raise RuntimeError(f"Failed to extract audio: {exc.stderr}") from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"ffmpeg was not found at '{settings.ffmpeg_path}'. "
            "Make sure FFmpeg is installed and available on PATH."
        ) from exc

    return str(wav_path)
