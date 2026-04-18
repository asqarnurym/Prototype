import csv
import subprocess
from contextlib import suppress
from pathlib import Path

import yt_dlp

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = PROJECT_ROOT / "evaluation"
INPUT_DIR = PROJECT_ROOT / "input"
EVAL_DIR.mkdir(exist_ok=True)
INPUT_DIR.mkdir(exist_ok=True)
MANIFEST_PATH = EVAL_DIR / "corpus_manifest.csv"

# Target matrix: 24 videos = 2 languages * 3 duration buckets * 4 content types.
MATRIX = [
    {"lang": "en", "type": "talking_head", "query": "educational explanation topic"},
    {
        "lang": "en",
        "type": "slide-centric",
        "query": "university lecture with slides presentation",
    },
    {
        "lang": "en",
        "type": "screencast",
        "query": "software programming tutorial screen coding",
    },
    {
        "lang": "en",
        "type": "practical_demo",
        "query": "science physics experiment demonstration",
    },
    {
        "lang": "ru",
        "type": "talking_head",
        "query": "образовательное объяснение лекция",
    },
    {
        "lang": "ru",
        "type": "slide-centric",
        "query": "университетская лекция с презентацией слайды",
    },
    {
        "lang": "ru",
        "type": "screencast",
        "query": "программирование туториал запись экрана",
    },
    {
        "lang": "ru",
        "type": "practical_demo",
        "query": "научный эксперимент демонстрация физика",
    },
]

BUCKETS = {
    "short": (60, 299),  # 1-5 minutes
    "medium": (300, 599),  # 5-10 minutes
    "long": (600, 1200),  # 10-20 minutes
}


def normalize_video(raw_path, out_path):
    print(f"  [FFMPEG] Normalizing {raw_path} -> {out_path}...")
    cmd = [
        "ffmpeg",
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
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    rows = []
    collected_keys = set()

    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
                collected_keys.add(f"{r['language']}_{r['duration_bucket']}_{r['content_type']}")

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

        ydl_opts_search = {
            "extract_flat": True,
            "quiet": True,
        }

        for bucket_name, (min_sec, max_sec) in BUCKETS.items():
            for item in MATRIX:
                key = f"{item['lang']}_{bucket_name}_{item['type']}"
                if key in collected_keys:
                    print(f"Skipping {key}, already in manifest.")
                    continue

                print(f"\nSearching for: {key} (Duration: {min_sec}-{max_sec}s)...")

                # Search 15 candidates to find one in the target duration range.
                search_query = (
                    f"ytsearch15:{item['query']} short"
                    if bucket_name == "short"
                    else f"ytsearch15:{item['query']}"
                )

                found_entry = None
                with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
                    try:
                        res = ydl.extract_info(search_query, download=False)
                        for entry in res["entries"]:
                            dur = entry.get("duration")
                            if dur and min_sec <= dur <= max_sec:
                                found_entry = entry
                                break
                    except Exception as e:
                        print(f"  Error searching: {e}")

                if not found_entry:
                    print(f"  [!] Could not find matching video for {key}. Try manual later.")
                    continue

                vid_id = found_entry["id"]
                dur = found_entry["duration"]
                title = found_entry.get("title", "")
                print(f"  Found: {vid_id} - {title[:50]} ({dur}s)")

                raw_path = INPUT_DIR / f"{vid_id}_raw.mp4"
                final_path = INPUT_DIR / f"{vid_id}.mp4"

                if not final_path.exists():
                    ydl_opts_download = {
                        "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                        "outtmpl": str(raw_path),
                        "quiet": True,
                    }
                    print("  Downloading video...")
                    with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                        try:
                            ydl.download([f"https://www.youtube.com/watch?v={vid_id}"])
                        except Exception as e:
                            print(f"  [!] Download failed: {e}")
                            continue

                    if raw_path.exists():
                        normalize_video(raw_path, final_path)
                        with suppress(Exception):
                            raw_path.unlink()
                    else:
                        downloaded_files = list(INPUT_DIR.glob(f"{vid_id}*.*"))
                        if downloaded_files:
                            actual_raw = downloaded_files[0]
                            normalize_video(actual_raw, final_path)
                            actual_raw.unlink()

                if final_path.exists():
                    row = {
                        "id": vid_id,
                        "path": f"./input/{vid_id}.mp4",
                        "language": item["lang"],
                        "duration_bucket": bucket_name,
                        "duration_sec": dur,
                        "content_type": item["type"],
                        "resolution": "1280x720",
                        "fps": 30,
                        "audio_condition": "clean",
                        "source_license": "youtube",
                    }
                    writer.writerow(row)
                    f_csv.flush()
                    collected_keys.add(key)
                    print(f"  [+] Added to manifest: {key}")
                else:
                    print(f"  [!] Normalization failed or file missing for {vid_id}")

    print("\nCorpus generation complete.")


if __name__ == "__main__":
    main()
