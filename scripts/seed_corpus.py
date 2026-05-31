"""Seed the videos table from evaluation/corpus_manifest.csv.

Run once after fresh database creation (idempotent — uses INSERT OR IGNORE).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import ensure_video  # noqa: E402

MANIFEST_PATH = PROJECT_ROOT / "evaluation" / "corpus_manifest.csv"


def main() -> None:
    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found at {MANIFEST_PATH}")
        raise SystemExit(1)

    with MANIFEST_PATH.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    for row in rows:
        vid_id = row["id"]
        ensure_video(
            vid_id,
            source="corpus",
            filename=Path(row["path"]).name,
            file_path=str(PROJECT_ROOT / row["path"].lstrip("./")),
            language=row["language"],
            duration_bucket=row["duration_bucket"],
            content_type=row.get("content_type", ""),
            video_duration_sec=float(row.get("duration_sec", 0) or 0),
            checksum="",
        )

    print(f"Seeded {len(rows)} corpus videos into the database.")


if __name__ == "__main__":
    main()
