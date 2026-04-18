"""
vtt.py — Export subtitles in WebVTT format.

WebVTT (Web Video Text Tracks) is a standard subtitle format for HTML5 video.
Supported by all major browsers and video players.

Format:
    WEBVTT

    00:00:00.000 --> 00:00:04.500
    Hello and welcome to this lecture.

    00:00:04.500 --> 00:00:08.200
    Today we'll discuss machine learning.

This module exports standard speech subtitles without modifying the video stream.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_vtt(
    timeline: dict,
    output_path: str,
    mode: str = "segments",
) -> str:
    """
    Exports subtitles from the timeline in WebVTT format.

    Supports two modes:
    - "segments": one subtitle per segment (sentence) — standard view.
    - "words": one subtitle per word — for karaoke effect / high detail.

    Args:
        timeline: Final pipeline timeline.
        output_path: Path to save the .vtt file.
        mode: Subtitle mode — "segments" or "words".

    Returns:
        Path to the saved VTT file.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # -- Collect all cues (speech + visual) -----------------------
    all_cues = []

    # Speech segments/words
    items = timeline.get(mode, timeline.get("segments", []))
    for item in items:
        start = item.get("start", 0)
        end = item.get("end", 0)
        text = item.get("text", "") or item.get("word", "")
        if text.strip():
            all_cues.append((start, end, text.strip()))

    # -- Sort all cues by start time ------------------------------
    all_cues.sort(key=lambda c: c[0])

    # -- Generate VTT ---------------------------------------------
    lines = ["WEBVTT", ""]

    for i, (start, end, text) in enumerate(all_cues, start=1):
        start_str = _format_vtt_time(start)
        end_str = _format_vtt_time(end)

        lines.append(str(i))
        lines.append(f"{start_str} --> {end_str}")
        lines.append(text)
        lines.append("")  # Empty separator line (required in VTT)

    # -- Write file -----------------------------------------------
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"VTT subtitles saved: {output_path} ({len(all_cues)} cues)")
    return output_path


def _format_vtt_time(seconds: float) -> str:
    """
    Formats seconds into VTT timecode format: HH:MM:SS.mmm

    Example: 65.5 → "00:01:05.500"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
