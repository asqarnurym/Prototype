import csv
import subprocess
from pathlib import Path

import yt_dlp

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = PROJECT_ROOT / "evaluation"
INPUT_DIR = PROJECT_ROOT / "input"
MANIFEST_PATH = EVAL_DIR / "corpus_manifest.csv"

MISSING = [
    {"lang": "en", "type": "talking_head", "query": "vlog education long"},
    {
        "lang": "en",
        "type": "practical_demo",
        "query": "science experiment long demonstration",
    },
    {"lang": "ru", "type": "talking_head", "query": "образование лекция"},
    {"lang": "ru", "type": "slide-centric", "query": "лекция презентация"},
    {"lang": "ru", "type": "screencast", "query": "программирование туториал"},
    {"lang": "ru", "type": "practical_demo", "query": "научный эксперимент"},
]


def main():
    with open(MANIFEST_PATH, "a", newline="", encoding="utf-8") as f_csv:
        writer = csv.writer(f_csv)

        ydl_opts_search = {"extract_flat": True, "quiet": True}

        for item in MISSING:
            key = f"{item['lang']}_long_{item['type']}"
            print(f"Searching for: {key} (600-1200s)...")

            found_entry = None
            with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
                res = ydl.extract_info(f"ytsearch20:{item['query']}", download=False)
                for entry in res["entries"]:
                    dur = entry.get("duration")
                    if dur and 600 <= dur <= 1200:
                        found_entry = entry
                        break

            if not found_entry:
                print(f"  [!] Still no match for {key}.")
                continue

            vid_id = found_entry["id"]
            dur = found_entry["duration"]
            print(f"  Found: {vid_id} ({dur}s)")

            raw_path = INPUT_DIR / f"{vid_id}_raw.mp4"
            final_path = INPUT_DIR / f"{vid_id}.mp4"

            try:
                if not final_path.exists():
                    ydl_opts_download = {
                        "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                        "outtmpl": str(raw_path),
                        "quiet": True,
                    }
                    with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                        ydl.download([f"https://www.youtube.com/watch?v={vid_id}"])

                    downloaded_files = list(INPUT_DIR.glob(f"{vid_id}*.*"))
                    if downloaded_files:
                        actual_raw = downloaded_files[0]
                        subprocess.run(
                            [
                                "ffmpeg",
                                "-y",
                                "-i",
                                str(actual_raw),
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
                                str(final_path),
                            ],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        actual_raw.unlink()

                if final_path.exists():
                    writer.writerow(
                        [
                            vid_id,
                            f"./input/{vid_id}.mp4",
                            item["lang"],
                            "long",
                            dur,
                            item["type"],
                            "1280x720",
                            30,
                            "clean",
                            "youtube",
                        ]
                    )
                    f_csv.flush()
                    print(f"  [+] Added {key}")
            except Exception as e:
                print(f"  [!] Failed to download {vid_id}: {e}")


if __name__ == "__main__":
    main()
