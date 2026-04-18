import csv
import subprocess
from pathlib import Path

import yt_dlp

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = PROJECT_ROOT / "evaluation"
INPUT_DIR = PROJECT_ROOT / "input"
MANIFEST_PATH = EVAL_DIR / "corpus_manifest.csv"


def main():
    with open(MANIFEST_PATH, "a", newline="", encoding="utf-8") as f_csv:
        writer = csv.writer(f_csv)

        print("Searching for: en_long_practical_demo (600-1200s)...")
        ydl_opts_search = {"extract_flat": True, "quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
            res = ydl.extract_info(
                "ytsearch20:science physics experiment demonstration long", download=False
            )
            for entry in res["entries"]:
                dur = entry.get("duration")
                if dur and 600 <= dur <= 1200:
                    vid_id = entry["id"]
                    print(f"Trying: {vid_id} ({dur}s)")
                    try:
                        raw_path = INPUT_DIR / f"{vid_id}_raw.mp4"
                        final_path = INPUT_DIR / f"{vid_id}.mp4"
                        ydl_opts_download = {
                            "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                            "outtmpl": str(raw_path),
                            "quiet": True,
                        }
                        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl_dl:
                            ydl_dl.download([f"https://www.youtube.com/watch?v={vid_id}"])

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
                                    "en",
                                    "long",
                                    dur,
                                    "practical_demo",
                                    "1280x720",
                                    30,
                                    "clean",
                                    "youtube",
                                ]
                            )
                            f_csv.flush()
                            print("Added en_long_practical_demo")
                            return
                    except Exception as e:
                        print(f"Failed {vid_id}: {e}")
                        continue


if __name__ == "__main__":
    main()
