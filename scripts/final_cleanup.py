import argparse
import csv
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

INPUT_DIR = PROJECT_ROOT / "input"
MANIFEST_PATH = PROJECT_ROOT / "evaluation" / "corpus_manifest.csv"


def _load_settings():
    from core.config import settings

    return settings


MATRIX = []
for lang in ["en", "ru"]:
    for dur in ["short", "medium", "long"]:
        for t in ["talking_head", "slide-centric", "screencast", "practical_demo"]:
            MATRIX.append(f"{lang}_{dur}_{t}")


def get_duration(path):
    settings = _load_settings()
    cmd = [
        settings.ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return float(res.stdout.strip())


def main():
    parser = argparse.ArgumentParser(
        description="Clean up input/ to only contain 24-slot matrix files and regenerate manifest."
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt (use with caution)"
    )
    args = parser.parse_args()

    # 1. Find files to delete
    to_delete = [f for f in INPUT_DIR.glob("*.mp4") if f.stem not in MATRIX]

    if to_delete:
        print(f"Files to delete ({len(to_delete)}):")
        for f in to_delete:
            print(f"  - {f.name}")

        if args.dry_run:
            print("\n[DRY RUN] No files were deleted.")
        else:
            if not args.yes:
                confirm = input("\nProceed with deletion? [y/N]: ").strip().lower()
                if confirm != "y":
                    print("Aborted.")
                    return

            for f in to_delete:
                print(f"Deleting: {f.name}")
                f.unlink()
            print(f"Deleted {len(to_delete)} file(s).")
    else:
        print("No leftover files to delete.")

    if args.dry_run:
        print("\n[DRY RUN] Manifest would be regenerated.")
        return

    # 2. Regenerate manifest with exact durations
    with open(MANIFEST_PATH, "w", newline="", encoding="utf-8") as f:
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

        for sem_id in MATRIX:
            target_path = INPUT_DIR / f"{sem_id}.mp4"
            if not target_path.exists():
                print(f"[!] MISSING: {sem_id}")
                continue

            parts = sem_id.split("_")
            lang, dur_bucket, ctype = parts[0], parts[1], "_".join(parts[2:])
            actual_dur = get_duration(target_path)

            writer.writerow(
                [
                    sem_id,
                    f"./input/{sem_id}.mp4",
                    lang,
                    dur_bucket,
                    actual_dur,
                    ctype,
                    "1280x720",
                    30,
                    "clean",
                    "mixed",
                ]
            )
            print(f"Verified {sem_id}: {actual_dur}s")


if __name__ == "__main__":
    main()
