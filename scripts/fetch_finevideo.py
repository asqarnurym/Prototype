import csv
import json
import os
import subprocess
import sys
from pathlib import Path

from datasets import load_dataset
from dotenv import load_dotenv
from langdetect import LangDetectException, detect

# Configure repo-relative paths.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

EVAL_DIR = PROJECT_ROOT / "evaluation"
INPUT_DIR = PROJECT_ROOT / "input"
EVAL_DIR.mkdir(exist_ok=True)
INPUT_DIR.mkdir(exist_ok=True)
MANIFEST_PATH = EVAL_DIR / "corpus_manifest.csv"


def _load_settings():
    from core.config import settings

    return settings


# Target quotas for the 24-video corpus.
QUOTAS = {
    "en": {"short": 4, "medium": 4, "long": 4},
    "ru": {"short": 4, "medium": 4, "long": 4},
}
# The final corpus needs four items per language/bucket combination. To keep the
# streaming pass simple, this script first balances language and duration, then
# assigns content_type with a best-effort heuristic from metadata.


def get_duration_bucket(duration_sec):
    if duration_sec < 300:
        return "short"
    if duration_sec <= 600:
        return "medium"
    return "long"


def guess_content_type(meta):
    text = (
        meta.get("youtube_title", "")
        + " "
        + meta.get("youtube_description", "")
        + " "
        + meta.get("content_fine_category", "")
    ).lower()
    if (
        "programming" in text
        or "software" in text
        or "code" in text
        or "tutorial" in text
        and "screen" in text
    ):
        return "screencast"
    elif "lecture" in text or "presentation" in text or "slide" in text:
        return "slide-centric"
    elif (
        "diy" in text
        or "how to" in text
        or "demonstration" in text
        or "experiment" in text
        or "cook" in text
    ):
        return "practical_demo"
    else:
        return "talking_head"


def normalize_video(raw_path, out_path):
    """Normalize video to standard format. Returns True on success, False on failure."""
    print(f"Normalizing {raw_path} -> {out_path}...")
    cmd = [
        settings.ffmpeg_path,
        "-y",
        "-i",
        str(raw_path),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-s",
        "1280x720",
        str(out_path),
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        print(f"  ERROR: ffmpeg failed with code {result.returncode}")
        return False
    if not out_path.exists():
        print(f"  ERROR: output file not created: {out_path}")
        return False
    return True


def main():
    load_dotenv()
    hf_token = os.getenv("HF_TOKEN")
    settings = _load_settings()

    # First measure how much of the corpus is already collected.
    collected = {
        "en": {"short": 0, "medium": 0, "long": 0},
        "ru": {"short": 0, "medium": 0, "long": 0},
    }
    rows = []

    # Reuse the current manifest when it already exists.
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                collected[r["language"]][r["duration_bucket"]] += 1
                rows.append(r)

    print("Current collected quotas:", collected)

    # Exit early if every quota is already satisfied.
    if all(collected[lang][buck] >= QUOTAS[lang][buck] for lang in QUOTAS for buck in QUOTAS[lang]):
        print("All quotas met. Existing manifest:")
        print(len(rows), "rows.")
        return

    print("Loading HuggingFaceFV/finevideo stream...")
    dataset = load_dataset("HuggingFaceFV/finevideo", split="train", streaming=True, token=hf_token)

    manifest_headers = [
        "id",
        "path",
        "language",
        "duration_bucket",
        "duration_sec",
        "content_type",
        "resolution",
        "fps",
        "audio_condition",
        "source_license",
    ]

    with open(MANIFEST_PATH, "a" if rows else "w", newline="", encoding="utf-8") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=manifest_headers)
        if not rows:
            writer.writeheader()

        count = 0
        try:
            for item in dataset:
                meta = item["json"]
                if isinstance(meta, str):
                    meta = json.loads(meta)

                parent = meta.get("content_parent_category", "")
                if parent not in ["Education", "Science & Technology", "Howto & Style"]:
                    continue

                duration = meta.get("duration_seconds", 0)
                if duration < 60 or duration > 1200:
                    continue

                bucket = get_duration_bucket(duration)

                title = meta.get("youtube_title", "")
                desc = meta.get("youtube_description", "")
                text_for_lang = f"{title}. {desc}"

                try:
                    lang = detect(text_for_lang)
                except LangDetectException:
                    continue

                if lang not in ["en", "ru"]:
                    continue

                if collected[lang][bucket] >= QUOTAS[lang][bucket]:
                    continue

                vid_id = meta.get("original_video_filename", f"vid_{count}").replace(".mp4", "")
                print(
                    f"[{count}] Found match! Lang: {lang}, Bucket: {bucket}, Title: {title[:50]}..."
                )

                raw_vid_path = settings.temp_dir / f"{vid_id}_raw.mp4"
                with open(raw_vid_path, "wb") as f_vid:
                    f_vid.write(item["mp4"])

                final_vid_path = INPUT_DIR / f"{vid_id}.mp4"
                if not normalize_video(raw_vid_path, final_vid_path):
                    print(f"  Skipping {vid_id} due to normalization failure")
                    raw_vid_path.unlink(missing_ok=True)
                    continue
                raw_vid_path.unlink()

                c_type = guess_content_type(meta)

                row = {
                    "id": vid_id,
                    "path": f"./input/{vid_id}.mp4",
                    "language": lang,
                    "duration_bucket": bucket,
                    "duration_sec": duration,
                    "content_type": c_type,
                    "resolution": "1280x720",
                    "fps": 30,
                    "audio_condition": "clean",
                    "source_license": "CC-BY",
                }
                writer.writerow(row)
                f_csv.flush()

                collected[lang][bucket] += 1
                print(
                    f"Collected: {lang} {bucket} ({collected[lang][bucket]}/{QUOTAS[lang][bucket]})"
                )

                if all(
                    collected[language][bucket_name] >= QUOTAS[language][bucket_name]
                    for language in QUOTAS
                    for bucket_name in QUOTAS[language]
                ):
                    print("All quotas met! Exiting.")
                    break
                count += 1
        except KeyboardInterrupt:
            print("Interrupted by user.")


if __name__ == "__main__":
    settings = _load_settings()
    settings.temp_dir.mkdir(exist_ok=True)
    main()
