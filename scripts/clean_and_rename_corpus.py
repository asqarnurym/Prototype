import csv
import subprocess
from pathlib import Path

import yt_dlp

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
EVAL_DIR = PROJECT_ROOT / "evaluation"
OLD_MANIFEST = EVAL_DIR / "corpus_manifest.csv"
NEW_MANIFEST = EVAL_DIR / "corpus_manifest_v2.csv"

# Rejected source videos that should be removed from the corpus.
BAD_IDS = ["EFYBO7xnmEg", "0ECqAg6sl-4", "86gn1y9P7nU", "rieb8cBb2z8", "xbtjjHYj8rA"]

# User-provided videos mapped into target corpus slots.
USER_VIDEOS = {
    "en_short_practical_demo": ("test.mp4", 119.7),
    "ru_long_slide-centric": ("История и философия науки 10.1.mp4", 832.1),
    "en_medium_screencast": (
        "Debugging with stack traces_Intro to CS - Python_Khan Academy.mp4",
        349.6,
    ),
    "en_short_screencast": (
        "Intro to Games and Visualizations _ Computer programming _ Khan Academy.mp4",
        186.1,
    ),
}

MATRIX = []
for lang in ["en", "ru"]:
    for dur in ["short", "medium", "long"]:
        for t in ["talking_head", "slide-centric", "screencast", "practical_demo"]:
            MATRIX.append(f"{lang}_{dur}_{t}")


def search_and_download(semantic_id):
    parts = semantic_id.split("_")
    lang = parts[0]
    dur_bucket = parts[1]
    v_type = "_".join(parts[2:])

    queries = {
        "talking_head": "educational vlog presentation",
        "slide-centric": "university lecture presentation slides",
        "screencast": "programming tutorial screen recording",
        "practical_demo": "science experiment demonstration",
    }

    if lang == "ru":
        queries = {
            "talking_head": "образовательное видео спикер",
            "slide-centric": "университет лекция презентация",
            "screencast": "урок программирование запись экрана",
            "practical_demo": "физика химия эксперимент опыт",
        }

    dur_ranges = {"short": (60, 299), "medium": (300, 599), "long": (600, 1200)}

    min_s, max_s = dur_ranges[dur_bucket]
    query = f"ytsearch20:{queries[v_type]}"

    ydl_opts_search = {"extract_flat": True, "quiet": True}
    print(f"  Searching YouTube for {semantic_id} ({min_s}-{max_s}s)...")
    with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
        res = ydl.extract_info(query, download=False)
        for entry in res["entries"]:
            dur = entry.get("duration")
            if dur and min_s <= dur <= max_s and entry["id"] not in BAD_IDS:
                # Found a candidate that matches the slot constraints.
                vid_id = entry["id"]
                print(f"  Found candidate {vid_id} ({dur}s)")
                raw_path = INPUT_DIR / f"{vid_id}_raw.mp4"
                final_path = INPUT_DIR / f"{semantic_id}.mp4"

                dl_opts = {
                    "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "outtmpl": str(raw_path),
                    "quiet": True,
                }
                try:
                    with yt_dlp.YoutubeDL(dl_opts) as dl:
                        dl.download([f"https://www.youtube.com/watch?v={vid_id}"])

                    dfiles = list(INPUT_DIR.glob(f"{vid_id}*.*"))
                    if dfiles:
                        # Normalize the download into the standard target format.
                        subprocess.run(
                            [
                                "ffmpeg",
                                "-y",
                                "-i",
                                str(dfiles[0]),
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
                        dfiles[0].unlink()
                        if final_path.exists():
                            return dur
                except Exception as e:
                    print(f"  [!] Failed {vid_id}: {e}")
                    pass
    return None


def main():
    # 1. Remove known-bad files.
    print("Cleaning up bad files...")
    for bad in BAD_IDS:
        for f in INPUT_DIR.glob(f"{bad}*"):
            f.unlink()
            print(f"  Deleted {f.name}")

    for f in INPUT_DIR.glob("*_raw.mp4"):
        f.unlink()

    # 2. Read the previous manifest and build an id -> semantic slot map,
    #    skipping videos that were explicitly rejected.
    downloaded_map = {}
    if OLD_MANIFEST.exists():
        with open(OLD_MANIFEST, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                vid = row["id"]
                if vid not in BAD_IDS:
                    sem_id = f"{row['language']}_{row['duration_bucket']}_{row['content_type']}"
                    downloaded_map[sem_id] = (vid, float(row["duration_sec"]))

    # 3. Prepare a rebuilt manifest.
    with open(NEW_MANIFEST, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
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
        )

        # 4. Fill the full 24-slot matrix.
        for sem_id in MATRIX:
            parts = sem_id.split("_")
            lang, dur, ctype = parts[0], parts[1], "_".join(parts[2:])

            target_path = INPUT_DIR / f"{sem_id}.mp4"
            actual_dur = 0

            if sem_id in USER_VIDEOS:
                # Prefer curated user-provided videos for selected slots.
                user_file, udur = USER_VIDEOS[sem_id]
                source_path = INPUT_DIR / user_file
                if source_path.exists():
                    # Normalize the user video into the semantic target filename.
                    print(f"Converting user video {user_file} -> {sem_id}.mp4")
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-y",
                            "-i",
                            str(source_path),
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
                            str(target_path),
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    actual_dur = udur
                else:
                    print(f"[!] Warning: User file {user_file} not found!")

            elif sem_id in downloaded_map:
                # Reuse a previously downloaded video if it is still available.
                old_id, odur = downloaded_map[sem_id]
                old_path = INPUT_DIR / f"{old_id}.mp4"
                if old_path.exists():
                    print(f"Renaming downloaded {old_id}.mp4 -> {sem_id}.mp4")
                    old_path.rename(target_path)
                    actual_dur = odur
                else:
                    # The file is missing, so this slot must be downloaded again.
                    print(f"File {old_id}.mp4 missing, will redownload {sem_id}")

            # If the slot is still empty, fetch a fresh candidate.
            if not target_path.exists():
                print(f"Missing {sem_id}, downloading fresh...")
                actual_dur = search_and_download(sem_id)
                if not actual_dur:
                    print(f"[!!!] FAILED TO GET {sem_id}")
                    continue

            # Persist the slot assignment in the rebuilt manifest.
            writer.writerow(
                [
                    sem_id,
                    f"./input/{sem_id}.mp4",
                    lang,
                    dur,
                    actual_dur,
                    ctype,
                    "1280x720",
                    30,
                    "clean",
                    "mixed",
                ]
            )
            f.flush()

    # Replace the old manifest with the rebuilt one.
    if OLD_MANIFEST.exists():
        OLD_MANIFEST.unlink()
    NEW_MANIFEST.rename(OLD_MANIFEST)
    print("\nClean up and renaming complete! Matrix mapped to semantic filenames.")


if __name__ == "__main__":
    main()
